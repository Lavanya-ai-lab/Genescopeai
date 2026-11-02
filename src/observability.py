"""Opt-in LangSmith instrumentation; never change research decisions.

LangGraph supplies node/embedding traces. wrap_openai adds the existing raw
Nebius calls. A review resume is a new trace with the same thread metadata,
not a span held open while a researcher is away.
"""

import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from langsmith import tracing_context
from langsmith.wrappers import wrap_openai


def tracing_enabled():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    return bool(os.getenv("LANGSMITH_API_KEY")) and os.getenv(
        "LANGSMITH_TRACING", "false"
    ).lower() == "true"


def graph_config(thread_id, phase="research", **metadata):
    return {
        "configurable": {"thread_id": thread_id},
        "metadata": {**metadata, "thread_id": thread_id,
                     "session_id": thread_id, "phase": phase},
        "tags": ["genescope", phase],
    }


@contextmanager
def research_trace():
    # Disable explicitly when no key is available, even if a shell has enabled
    # tracing. The SDK handles upload failures without changing graph output.
    with tracing_context(enabled=tracing_enabled()):
        yield


def trace_client(client):
    return wrap_openai(client) if tracing_enabled() else client


def verify_review_transport(client=None):
    """Explicit hosted smoke test of real pause/resume, with no research calls.

Seeds a labeled review fixture after analysis. This is transport verification,
not a scientific evaluation or an additional golden case. No API secrets enter
the report; a link is returned only after the hosted run has been read back.
"""
    if not tracing_enabled():
        return {"status": "not_configured", "verified": [],
                "reason": "Set LANGSMITH_API_KEY and LANGSMITH_TRACING=true, then restart this command."}
    from uuid import uuid4
    import time
    from langsmith import Client
    from langsmith.run_trees import get_cached_client
    from langgraph.types import Command
    from src.graph.workflow import build_workflow
    client = client or Client()
    graph = build_workflow()
    thread = str(uuid4())
    seed = graph_config(thread, "observability_fixture", synthetic=True)
    graph.update_state(seed, {"question": "Transport test only; no scientific research performed.",
        "relationships": [{"gene": "APOE", "allele": "APOE ε4", "disease": "Alzheimer's disease",
                           "relationship_type": "increased_risk", "relationship_status": "transport_fixture_only"}],
        "agent_log": [], "errors": []}, as_node="analysis_agent")
    pause = graph_config(thread, "research", synthetic=True, purpose="review_transport_smoke")
    resume = graph_config(thread, "review_resume", synthetic=True, purpose="review_transport_smoke")
    pause["run_id"], resume["run_id"] = uuid4(), uuid4()
    with tracing_context(enabled=True, client=client):
        paused = graph.invoke(None, config=pause)
        if not paused.get("__interrupt__"):
            raise ValueError("Smoke test did not pause for human review.")
        completed = graph.invoke(Command(resume={"approved": False,
            "feedback": "Scripted transport test; no human scientific adjudication."}), config=resume)
    if completed.get("approved_relationships") or completed.get("review_status") != "rejected":
        raise ValueError("Smoke test review lifecycle failed.")
    client.flush(timeout=10)
    get_cached_client().flush(timeout=10)
    verified = []
    for config in (pause, resume):
        run = None
        for attempt in range(3):
            try:
                run = client.read_run(config["run_id"], load_child_runs=True)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2)
        metadata = (run.extra or {}).get("metadata", {})
        if metadata.get("thread_id") != thread or metadata.get("phase") != config["metadata"]["phase"] or run.error:
            raise ValueError("Hosted trace did not preserve the expected thread/phase or ended in error.")
        outputs = run.outputs or {}
        if config is pause and not outputs.get("__interrupt__"):
            # This LangGraph version omits the interrupt from root outputs;
            # the human-review child records GraphInterrupt instead. That is
            # an expected pause, not a failed root invocation.
            children = getattr(run, "child_runs", None) or []
            if not any(child.name == "human_review_agent" and "GraphInterrupt" in str(child.error)
                       for child in children):
                raise ValueError("Hosted trace does not expose the expected review pause.")
        if config is resume and outputs.get("review_status") != "rejected":
            raise ValueError("Hosted resume trace does not contain its recorded rejection.")
        verified.append({"run_id": str(run.id), "thread_id": thread,
                         "phase": metadata["phase"], "url": client.get_run_url(run=run)})
    return {"status": "verified", "verified": verified,
            "scope": "Synthetic review transport only; no Nebius calls or scientific evaluation."}


def verify_saved_case(record, client=None):
    """Read back actual recorded trace IDs; never infer delivery from a UUID."""
    if not tracing_enabled():
        return {"status": "not_configured", "verified": [], "reason": "LangSmith credentials/tracing are not configured."}
    from langsmith import Client
    client = client or Client()
    verified = []
    if len(record["trace_ids"]) != len(record["segments"]):
        raise ValueError("Trace segment accounting mismatch.")
    for id, segment in zip(record["trace_ids"], record["segments"]):
        run = client.read_run(id, load_child_runs=True)
        expected_thread = record["clarification_turn"]["thread_id"] if segment["phase"] == "clarify" else record["thread_id"]
        metadata = (run.extra or {}).get("metadata", {})
        if run.error or metadata.get("thread_id") != expected_thread or metadata.get("phase") != segment["phase"]:
            raise ValueError("Hosted case trace does not match the saved thread/phase.")
        verified.append({"run_id": str(run.id), "thread_id": expected_thread,
                         "phase": segment["phase"], "url": client.get_run_url(run=run)})
    if not verified:
        raise ValueError("No hosted runs were verified.")
    return {"status": "verified", "case_id": record["case_id"], "verified": verified,
            "scope": "Read-back verification of this saved case only."}


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Explicit LangSmith review transport verification")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--verify-review", action="store_true")
    group.add_argument("--verify-case", type=Path)
    args = parser.parse_args()
    try:
        result = verify_review_transport() if args.verify_review else verify_saved_case(json.loads(args.verify_case.read_text()))
    except Exception as exc:
        result = {"status": "failed", "verified": [], "reason": type(exc).__name__}
    target = Path(__file__).resolve().parents[1] / "evals/reports/langsmith_verification.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
