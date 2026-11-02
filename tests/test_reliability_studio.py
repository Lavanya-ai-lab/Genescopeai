"""Saved-results UI and transport read-back tests; no paid services."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from src.visualization.reliability_studio import load_results, BUNDLE
from src.observability import verify_saved_case

ROOT = Path(__file__).resolve().parents[1]


def test_published_results_preserve_unsafe_original_output_and_provisional_labels():
    data = load_results(str(BUNDLE), BUNDLE.stat().st_mtime_ns)
    case = next(c for c in data["cases"] if c["id"] == "K01")
    assert case["runs"]["baseline"]["presentation"]["conclusion"].startswith("Yes.")
    assert "more than half" in case["runs"]["baseline"]["presentation"]["conclusion"]
    for case in data["cases"]:
        review = case["human_review"]
        assert review["status"] in {"draft", "reviewed"}
        if review["status"] == "reviewed":
            assert review["reviewer"] and review["reviewed_at"] and review["notes"]


def test_invalid_saved_denominators_are_rejected(tmp_path):
    data = json.loads(BUNDLE.read_text())
    data["baseline"]["metrics"]["grounded_correctness"]["pass"] += 1
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="denominators"):
        load_results(str(path), 0)


def test_publisher_rejects_mismatched_intermediate_configuration(monkeypatch, tmp_path):
    import src.evaluation.report as reports
    from copy import deepcopy
    saved = json.loads(BUNDLE.read_text())["baseline"]
    wrong = deepcopy(saved)
    wrong["metadata"]["dataset_sha256"] = "different"
    monkeypatch.setattr(reports, "build_report", lambda path: wrong if str(path) == "wrong-run" else saved)
    with pytest.raises(ValueError, match="dataset_sha256"):
        reports.publish_studio(tmp_path, None, tmp_path / "out.json", additional_runs={"old": "wrong-run"})


def test_final_bundle_keeps_every_run_and_case_transition():
    data = load_results(str(BUNDLE), BUNDLE.stat().st_mtime_ns)
    assert len(data["comparison"]["paired_cases"]) == 40
    assert all(set(c["runs"]) == {"baseline", "intermediate", "iteration_2", "improved"} for c in data["cases"])
    paired = {p["id"]: p for p in data["comparison"]["paired_cases"]}
    for c in data["cases"]:
        for key, transition in paired[c["id"]]["metrics"].items():
            assert transition["before"] == c["runs"]["baseline"]["metrics"][key]["status"]
            assert transition["after"] == c["runs"]["improved"]["metrics"][key]["status"]
    import csv
    rows = list(csv.DictReader((ROOT / "evals/reports/case_comparison.csv").open()))
    assert {r["case_id"] for r in rows} == {c["id"] for c in data["cases"]}


def test_recorded_precision_and_approval_regressions_do_not_reappear_in_final_answers():
    data = load_results(str(BUNDLE), BUNDLE.stat().st_mtime_ns)
    cases = {c["id"]: c for c in data["cases"]}
    k01 = cases["K01"]["runs"]["improved"]["presentation"]
    assert not k01["conclusion"].startswith("Yes.")
    k08 = cases["K08"]["runs"]["improved"]["presentation"]
    assert "C→T" not in k08["summary"] and "Arg158" not in k08["summary"]
    a05 = cases["A05"]["runs"]["improved"]["presentation"]
    assert "3-fold" not in a05["summary"] and "12-fold" not in a05["summary"]
    a07 = cases["A07"]["runs"]["improved"]["presentation"]
    assert a07["conclusion"].startswith("No.") and "does not independently verify" in a07["conclusion"]


def test_page_load_and_example_never_start_research_or_evaluation(monkeypatch):
    from src.graph import workflow
    import src.evaluation.runner as runner
    research, paid_run = Mock(side_effect=AssertionError("Unexpected research")), Mock(side_effect=AssertionError("Unexpected evaluation"))
    monkeypatch.setattr(workflow, "research_agent", research)
    monkeypatch.setattr(runner, "run_case", paid_run)
    import streamlit as st
    st.cache_resource.clear()
    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=15)
    assert not app.exception
    assert "Evaluation Overview" not in [t.label for t in app.tabs]  # lazy hidden view
    app.session_state["workspace_tabs"] = "Reliability Studio"
    app.run(timeout=15)
    assert not app.exception
    for name in ["Evaluation Overview", "Failure Investigation", "Before/After"]:
        assert name in [t.label for t in app.tabs]
    app.button(key="use_example_question").click().run(timeout=15)
    assert not app.exception
    assert app.text_input(key="question_input").value == "Does APOE epsilon 4 guarantee Alzheimer's disease?"
    assert app.session_state["research_result"] is None
    app.selectbox(key="reliability_case").select("K06").run(timeout=15)
    assert not app.exception
    research.assert_not_called()
    paid_run.assert_not_called()
    st.cache_resource.clear()


def test_hosted_case_requires_read_back_with_matching_metadata(monkeypatch):
    import src.observability as tracing
    monkeypatch.setattr(tracing, "tracing_enabled", lambda: True)
    client = Mock()
    record = {"case_id": "W03", "thread_id": "thread", "trace_ids": ["first", "second"],
              "segments": [{"phase": "research"}, {"phase": "review_resume"}]}
    client.read_run.side_effect = [SimpleNamespace(id=id, error=None, extra={"metadata": {
        "thread_id": "thread", "phase": phase}}) for id, phase in [("first", "research"), ("second", "review_resume")]]
    client.get_run_url.side_effect = lambda run: "https://smith.langchain.com/r/" + run.id
    result = verify_saved_case(record, client)
    assert result["status"] == "verified" and len(result["verified"]) == 2
    client.read_run.side_effect = None
    client.read_run.return_value = SimpleNamespace(id="first", error=None, extra={"metadata": {"thread_id": "wrong"}})
    with pytest.raises(ValueError, match="thread/phase"):
        verify_saved_case(record, client)


def test_missing_credentials_never_claim_delivery(monkeypatch):
    import src.observability as tracing
    monkeypatch.setattr(tracing, "tracing_enabled", lambda: False)
    client = Mock()
    assert verify_saved_case({}, client)["status"] == "not_configured"
    client.read_run.assert_not_called()


def test_real_review_transport_smoke_checks_hosted_readback_without_research(monkeypatch):
    from unittest.mock import patch
    from langsmith import Client
    from src.graph import workflow
    import src.observability as tracing
    monkeypatch.setattr(tracing, "tracing_enabled", lambda: True)
    retrieval = Mock(side_effect=AssertionError("Transport verification must not retrieve evidence"))
    monkeypatch.setattr(workflow, "research_agent", retrieval)
    client = Client(api_key="local-test-only", api_url="https://api.smith.langchain.com",
                    auto_batch_tracing=False, info={"version": "0.14.12"})
    starts, ends = {}, {}
    def started(**kwargs):
        starts[str(kwargs["id"])] = kwargs
    def ended(run_id=None, **kwargs):
        ends[str(run_id)] = kwargs
    def read(id, **kwargs):
        id = str(id)
        children = [SimpleNamespace(name=start["name"], error=ends.get(child_id, {}).get("error"))
                    for child_id, start in starts.items() if str(start.get("parent_run_id")) == id]
        return SimpleNamespace(id=id, error=ends[id].get("error"), outputs=ends[id].get("outputs"),
                               extra=starts[id]["extra"], child_runs=children)
    with (patch("langchain_core.tracers.langchain.get_client", return_value=client),
          patch("langsmith.run_trees.get_cached_client", return_value=client),
          patch.object(Client, "create_run", side_effect=started),
          patch.object(Client, "update_run", side_effect=ended),
          patch.object(Client, "read_run", side_effect=read),
          patch.object(Client, "get_run_url", return_value="https://smith.langchain.com/test-only")):
        result = tracing.verify_review_transport(client)
    assert result["status"] == "verified"
    assert {r["phase"] for r in result["verified"]} == {"research", "review_resume"}
    assert len({r["thread_id"] for r in result["verified"]}) == 1
    retrieval.assert_not_called()
