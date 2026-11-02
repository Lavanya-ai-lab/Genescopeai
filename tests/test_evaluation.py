"""Offline tests for independent evaluation and the real interrupt lifecycle."""

import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.evaluation.dataset import CORPUS, digest, load_cases, verify_frozen
from src.evaluation.evaluators import citation_integrity, evaluate, semantic_judgment, visible_output
from src.evaluation.runner import run_case
from src.evaluation.report import build_report, compare
from src.observability import graph_config, trace_client


@pytest.fixture
def corpus():
    return json.loads(CORPUS.read_text())


@pytest.fixture
def cases():
    return {c["id"]: c for c in load_cases()}


def test_frozen_dataset_has_40_honestly_labeled_cases(cases):
    assert len(cases) == 40
    for case in cases.values():
        review = case["human_review"]
        assert review["status"] in {"draft", "reviewed"}
        if review["status"] == "reviewed":
            assert review["reviewer"] and review["reviewed_at"] and review["notes"]
    assert len({c["category"] for c in cases.values()}) == 5
    verify_frozen(check_index=False)


def test_cannot_silently_change_frozen_inputs(cases):
    changed = list(deepcopy(cases).values())
    changed[0]["question"] += " changed"
    with pytest.raises(ValueError, match="inputs changed"):
        verify_frozen(changed, check_index=False)


def state_for(corpus):
    source = next(c for c in corpus if c["chunk_id"] == "pubmed_33340485_chunk_000")
    return {"question": "APOE risk?", "retrieved_evidence": [{"document_id": "pubmed_33340485", **source}],
            "research_summary": "APOE epsilon 4 increases risk [pubmed_33340485].",
            "validation_results": [{"check": "claim_evidence_validation", "passed": True,
                                    "claims": [{"evidence_status": "supported"}]}]}


def record_for(state):
    return {"state": state, "nodes": ["clarification_agent", "research_agent", "summarize_evidence",
                                      "human_review_agent"], "active_seconds": 1.25,
            "awaiting_review": False, "segments": []}


def test_citation_checks_use_frozen_and_retrieved_ids(corpus):
    state = state_for(corpus)
    assert citation_integrity(state, corpus)["status"] == "pass"
    state["research_summary"] += " False claim [pubmed_99999999]."
    result = citation_integrity(state, corpus)
    assert result["status"] == "fail"
    assert result["invalid_citations"] == ["pubmed_99999999"]


def test_ncbi_gene_ids_are_valid_citations(corpus):
    state = {"retrieved_evidence": [{"document_id": "ncbi_gene_348"}],
             "research_summary": "APOE maps to chromosome 19 [ncbi_gene_348]."}
    assert citation_integrity(state, corpus)["status"] == "pass"


def test_unjudged_entailment_is_not_a_pass(cases, corpus):
    result = evaluate(cases["H01"], record_for(state_for(corpus)), corpus)
    assert result["grounded_correctness"]["status"] == "ungraded"
    assert result["citation_validity"]["status"] == "ungraded"


def test_unexpected_output_at_scope_stop_cannot_pass_unassessed_entailment(cases, corpus):
    metrics = evaluate(cases["E08"], record_for(state_for(corpus)), corpus)
    assert metrics["workflow_completion"]["status"] == "fail"
    assert metrics["citation_validity"]["status"] == "ungraded"


def test_unknown_id_in_refusal_requires_adjudication_when_entailment_passes(cases, corpus):
    state = state_for(corpus)
    state["research_summary"] += " I will not cite pubmed_99999999 because it was not retrieved."
    def disagreement(*args):
        return {key: {"passed": key != "grounded_correctness", "reason": "Refusal mentions an unknown source.",
                      "failure_type": "unsupported_claim" if key == "grounded_correctness" else "none",
                      "evidence_chunk_ids": []}
                for key in ("grounded_correctness", "citation_entailment", "uncertainty_handling")}
    metrics = evaluate(cases["A04"], record_for(state), corpus, disagreement)
    assert metrics["citation_validity"]["status"] == "ungraded"
    assert metrics["grounded_correctness"]["status"] == "ungraded"
    assert metrics["grounded_correctness"]["original_judgment"]["status"] == "fail"


def test_independent_judge_overrides_app_verdict_and_never_receives_it(cases, corpus):
    state = state_for(corpus)
    client = Mock()
    result = {key: {"passed": False, "reason": "Unsupported by the cited passage.",
                    "failure_type": "unsupported_claim", "evidence_chunk_ids": []}
              for key in ("grounded_correctness", "citation_entailment", "uncertainty_handling")}
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(result)))])
    judge = lambda c, s, frozen: semantic_judgment(c, s, frozen, client, "independent-test")
    metrics = evaluate(cases["H01"], record_for(state), corpus, judge)
    assert metrics["grounded_correctness"]["status"] == "fail"
    assert metrics["citation_validity"]["status"] == "fail"
    prompt = client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "validation_results" not in prompt and "evidence_status" not in prompt
    assert "verification_status" not in prompt


def test_malformed_judge_is_ungraded_not_pass(cases, corpus):
    def unavailable(*args):
        raise ValueError("bad JSON")
    metrics = evaluate(cases["H01"], record_for(state_for(corpus)), corpus, unavailable)
    assert all(metrics[k]["status"] == "ungraded" for k in (
        "grounded_correctness", "citation_validity", "uncertainty_handling"))


@pytest.fixture
def offline_graph(monkeypatch):
    from src.graph import workflow
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    retrieval = Mock(return_value={"retrieved_evidence": [{"document_id": "pubmed_33340485",
        "content": "APOE epsilon 4 increases Alzheimer's risk."}]})
    summary = Mock(return_value={"research_summary": "APOE epsilon 4 increases Alzheimer's risk [pubmed_33340485]."})
    finding = {"claim_id": "c1", "statement": "APOE epsilon 4 increases Alzheimer's disease risk.",
               "citations": ["pubmed_33340485"], "verification_status": "model_assessed_supported"}
    monkeypatch.setattr(workflow, "research_agent", retrieval)
    monkeypatch.setattr(workflow, "summarize_evidence", summary)
    monkeypatch.setattr(workflow, "evidence_validator", lambda state: {})
    monkeypatch.setattr(workflow, "verified_findings_agent", lambda state: {"findings": [finding]})
    return workflow, retrieval, summary


@pytest.mark.parametrize("id", ["W01", "W02", "W03", "W04", "W05"])
def test_real_graph_pause_resume_and_clean_thread(cases, corpus, offline_graph, id):
    workflow, retrieval, _ = offline_graph
    record = run_case(cases[id], "offline", workflow)
    assert record["paused_before_resume"]
    assert retrieval.call_count == 1
    assert not record.get("exception")
    assert record["node_timings"]
    metric = evaluate(cases[id], record, corpus)["workflow_completion"]
    assert metric["status"] == "pass", metric
    state = record["state"]
    assert state["relationships"]
    if id == "W01":
        assert record["awaiting_review"] and not state.get("approved_relationships")
    elif id in {"W03", "W04"}:
        assert state["review_status"] == "rejected"
        assert not state["approved_relationships"]
        assert state["review_feedback"] == cases[id]["review_decision"]["feedback"]
    elif id == "W02":
        assert state["approved_relationships"] == state["relationships"]
    if id == "W05":
        assert record["thread_id"] != record["clarification_turn"]["thread_id"]


@pytest.mark.parametrize("id", ["E06", "E07", "A01", "A02", "W06", "W07"])
def test_stop_cases_do_not_call_generation(cases, corpus, offline_graph, id):
    workflow, retrieval, summary = offline_graph
    record = run_case(cases[id], "offline", workflow)
    summary.assert_not_called()
    retrieval.assert_not_called()
    assert evaluate(cases[id], record, corpus)["workflow_completion"]["status"] == "pass"


def test_thread_metadata_survives_resume():
    first = graph_config("same", "research", case_id="W03")
    resume = graph_config("same", "review_resume", case_id="W03")
    assert first["configurable"] == resume["configurable"]
    assert first["metadata"]["thread_id"] == resume["metadata"]["thread_id"]


def test_tracing_disabled_leaves_sdk_untouched(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    client = object()
    assert trace_client(client) is client


def test_real_langsmith_sdk_links_interrupt_resume_without_upload(cases, offline_graph, monkeypatch):
    from langsmith import Client, tracing_context
    from unittest.mock import patch
    import src.observability as tracing
    workflow, retrieval, _ = offline_graph
    monkeypatch.setattr(tracing, "tracing_enabled", lambda: True)
    # The real SDK constructs spans, but class-level mocks prevent all uploads.
    client = Client(api_key="local-test-only", api_url="https://api.smith.langchain.com",
                    auto_batch_tracing=False, info={"version": "0.14.12"})
    with (patch("langchain_core.tracers.langchain.get_client", return_value=client),
          patch.object(Client, "create_run") as created, patch.object(Client, "update_run") as updated):
        with tracing_context(enabled=True, client=client):
            record = run_case(cases["W03"], "offline-tracing", workflow)
        client.flush(timeout=2)
    assert record["state"]["review_status"] == "rejected"
    assert retrieval.call_count == 1
    roots = [call.kwargs for call in created.call_args_list if call.kwargs.get("name") == "LangGraph"]
    assert len(roots) == 2  # pause and resume are two traces, one review thread
    assert all(r["extra"]["metadata"]["thread_id"] == record["thread_id"] for r in roots)
    assert {r["extra"]["metadata"]["phase"] for r in roots} == {"research", "review_resume"}
    root_ids = {str(r["id"]) for r in roots}
    assert root_ids == set(record["trace_ids"])
    endings = [call.kwargs for call in updated.call_args_list if str(call.args[0] if call.args else call.kwargs.get("run_id")) in root_ids]
    assert all(not ending.get("error") for ending in endings)


def test_raw_nebius_sdk_call_is_traced_without_network(monkeypatch):
    import httpx
    from openai import OpenAI
    from langsmith import Client, tracing_context
    from unittest.mock import patch
    import src.observability as tracing
    monkeypatch.setattr(tracing, "tracing_enabled", lambda: True)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={
        "id": "local-response", "object": "chat.completion", "created": 1,
        "model": "offline-model", "choices": [{"index": 0, "message": {
            "role": "assistant", "content": "Test output"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 2, "completion_tokens": 2, "total_tokens": 4}}))
    client = Client(api_key="local-test-only", api_url="https://api.smith.langchain.com",
                    auto_batch_tracing=False, info={"version": "0.14.12"})
    with httpx.Client(transport=transport) as http_client:
        sdk = trace_client(OpenAI(api_key="local-test-only", base_url="https://offline.example/v1",
                                  http_client=http_client))
        with patch.object(Client, "create_run") as created, patch.object(Client, "update_run"):
            with tracing_context(enabled=True, client=client):
                response = sdk.chat.completions.create(model="offline-model",
                    messages=[{"role": "user", "content": "Test input"}])
            client.flush(timeout=2)
    assert response.choices[0].message.content == "Test output"
    assert any(call.kwargs.get("run_type") == "llm" for call in created.call_args_list)


def test_trace_upload_failure_does_not_change_research_result(cases, offline_graph, monkeypatch):
    from langsmith import Client, tracing_context
    from unittest.mock import patch
    import src.observability as tracing
    workflow, _, _ = offline_graph
    monkeypatch.setattr(tracing, "tracing_enabled", lambda: True)
    client = Client(api_key="local-test-only", api_url="https://api.smith.langchain.com",
                    auto_batch_tracing=False, info={"version": "0.14.12"})
    with (patch("langchain_core.tracers.langchain.get_client", return_value=client),
          patch.object(Client, "create_run", side_effect=ConnectionError("offline tracing fixture")),
          patch.object(Client, "update_run", side_effect=ConnectionError("offline tracing fixture"))):
        with tracing_context(enabled=True, client=client):
            record = run_case(cases["W02"], "offline-trace-failure", workflow)
        client.flush(timeout=2)
    assert not record.get("exception")
    assert record["state"]["review_status"] == "approved"
    assert record["state"]["approved_relationships"] == record["state"]["relationships"]


def test_report_denominators_and_comparison(tmp_path, cases):
    metadata = {"dataset_sha256": "fixed", "label": "provisional_not_human_reviewed"}
    (tmp_path / "experiment.json").write_text(json.dumps(metadata))
    for id in cases:
        record = {"case_id": id, "active_seconds": 2, "awaiting_review": True, "trace_ids": [],
                  "metrics": {k: {"status": "ungraded", "reason": "No judge"} for k in (
                      "grounded_correctness", "citation_validity", "uncertainty_handling", "workflow_completion")}}
        (tmp_path / f"{id}.json").write_text(json.dumps(record))
    report = build_report(tmp_path)
    assert report["completed"] == 40
    assert report["metrics"]["grounded_correctness"]["pass_fraction"] is None
    assert report["top_failures"] == []
    assert len(compare(report, deepcopy(report))["paired_cases"]) == 40
    changed = deepcopy(report)
    changed["metadata"]["dataset_sha256"] = "different"
    with pytest.raises(ValueError, match="not comparable"):
        compare(report, changed)


def test_cached_regrade_keeps_originals_and_never_calls_a_model(tmp_path, cases):
    from src.evaluation.dataset import MANIFEST
    from src.evaluation.report import regrade_cached
    source = tmp_path / "original"
    source.mkdir()
    manifest = json.loads(MANIFEST.read_text())
    (source / "experiment.json").write_text(json.dumps({"dataset_sha256": manifest["cases_sha256"]}))
    for id, case in cases.items():
        record = {"case_id": id, "state": {}, "nodes": [], "active_seconds": 0,
                  "awaiting_review": False, "trace_ids": [], "human_review": case["human_review"],
                  "metrics": {key: {"status": "ungraded", "reason": "No judge"} for key in (
                      "grounded_correctness", "citation_validity", "uncertainty_handling", "workflow_completion")}}
        (source / f"{id}.json").write_text(json.dumps(record))
    before = (source / "H01.json").read_bytes()
    report = regrade_cached(source, tmp_path / "corrected")
    assert report["completed"] == 40
    assert (source / "H01.json").read_bytes() == before
    assert json.loads((tmp_path / "corrected/H01.json").read_text())["original_metrics"]
