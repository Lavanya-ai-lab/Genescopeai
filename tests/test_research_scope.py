"""Offline regressions: run with `python -m pytest tests/test_research_scope.py`.

Requires pytest and the app's runtime dependencies. Only Chroma/embedding and
LLM boundaries are mocked; routing, citation checks, extraction, and review run
through the real LangGraph. All evidence here is a synthetic test fixture.
"""

import importlib
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
import streamlit as st
from langgraph.types import Command
from streamlit.testing.v1 import AppTest

from src.agents.clarification_agent import clarification_agent
from src.graph import workflow


APOE_QUESTION = "How does APOE epsilon 4 affect Alzheimer's disease risk?"
BRCA_QUESTION = "Which BRCA1 mutation causes breast cancer?"
STATEMENT = "APOE epsilon 4 increases Alzheimer's disease risk."
SUMMARY = STATEMENT.rstrip(".") + " [pubmed_00000000]."
APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def initial_state(question):
    # Match the sparse state used by Streamlit. The default gene must not
    # override the actual research question during scope checking.
    return {"question": question, "gene": "APOE", "agent_log": [], "errors": []}


def config():
    return {"configurable": {"thread_id": str(uuid4())}}


def response(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.fixture
def offline(monkeypatch, tmp_path):
    research = importlib.import_module("src.agents.research_agent")
    summary = importlib.import_module("src.agents.summarize_evidence")
    validator = importlib.import_module("src.agents.evidence_validator")
    for module in (research, summary, validator):
        monkeypatch.setattr(module, "load_dotenv", Mock())
    for variable in ("API_KEY", "BASE_URL", "EMBEDDING_MODEL", "LLM_MODEL"):
        monkeypatch.setenv("NEBIUS_" + variable, "offline-test")
    monkeypatch.setattr(research, "CHROMA_DIR", tmp_path)
    embeddings = Mock()
    monkeypatch.setattr(research, "OpenAIEmbeddings", embeddings)
    document = SimpleNamespace(
        page_content=STATEMENT,
        metadata={"document_id": "pubmed_00000000", "title": "Synthetic test evidence"},
    )
    store = Mock()
    store.similarity_search_with_score.return_value = [(document, 0.1)]
    chroma = Mock(return_value=store)
    monkeypatch.setattr(research, "Chroma", chroma)
    summary_client = Mock()
    summary_client.chat.completions.create.return_value = response(SUMMARY)
    monkeypatch.setattr(summary, "OpenAI", Mock(return_value=summary_client))
    validation_client = Mock()
    validation_client.chat.completions.create.return_value = response(
        '{"status": "supported", "reason": "Synthetic fixture supports the claim."}'
    )
    monkeypatch.setattr(validator, "OpenAI", Mock(return_value=validation_client))
    retrieval_calls = Mock()

    def tracked_research(state):
        retrieval_calls(state)
        return research.research_agent(state)

    monkeypatch.setattr(workflow, "research_agent", tracked_research)
    st.cache_resource.clear()
    yield SimpleNamespace(
        graph=workflow.build_workflow(), store=store, chroma=chroma,
        embeddings=embeddings, retrieval_calls=retrieval_calls,
        summary=summary_client.chat.completions.create,
        validation=validation_client.chat.completions.create,
        research=research.research_agent,
    )
    st.cache_resource.clear()


@pytest.mark.parametrize("question", [
    "What should I investigate next?",
    "What should I research next?",
    "What should we explore?",
    "What should I do next?",
    "What is the next step?",
    "Tell me what to investigate.",
    "  WHAT  should\nI investigate NEXT?!  ",
    "Please tell us what to study next.",
    "What should we investigate next?",
    "What should I research?",
    "What next?",
    "", " ?! ",
])
def test_vague_questions_stop_before_retrieval(offline, question):
    result = offline.graph.invoke(initial_state(question), config=config())
    assert result["needs_clarification"] is True
    assert result["clarification_question"]
    assert result["out_of_scope"] is False
    assert not result.get("retrieved_evidence")
    assert not result.get("research_summary")
    assert not result.get("relationships")
    assert "__interrupt__" not in result
    offline.retrieval_calls.assert_not_called()
    offline.chroma.assert_not_called()
    offline.summary.assert_not_called()
    offline.validation.assert_not_called()


@pytest.mark.parametrize("question, topic", [
    (BRCA_QUESTION, "BRCA1"),
    ("Which brca1 mutation causes breast cancer?", "BRCA1"),
    ("How does CFTR affect cystic fibrosis?", "CFTR"),
    ("What genetic factors affect breast cancer?", "breast cancer"),
])
def test_out_of_scope_stops_before_retrieval(offline, question, topic):
    result = offline.graph.invoke(initial_state(question), config=config())
    assert result["needs_clarification"] is False
    assert result["clarification_question"] == ""
    assert result["out_of_scope"] is True
    assert result["scope_message"] == (
        "GeneScope AI currently contains research on APOE and Alzheimer's disease. "
        f"I don't have sufficient indexed evidence to answer this {topic} question reliably."
    )
    for field in ("retrieved_evidence", "research_summary", "findings", "relationships",
                  "approved_relationships", "validation_results"):
        assert not result.get(field)
    assert "__interrupt__" not in result
    offline.retrieval_calls.assert_not_called()
    offline.chroma.assert_not_called()
    offline.summary.assert_not_called()
    offline.validation.assert_not_called()


@pytest.mark.parametrize("question", [
    APOE_QUESTION,
    "How does epsilon 4 influence Alzheimer's disease risk?",
    "How does epsilon 2 affect Alzheimer's disease risk?",
    "How does ε4 influence Alzheimer’s disease risk?",
    "How does apolipoprotein E influence dementia?",
    "How does ApoE4 affect late-onset AD?",
    "What should I investigate about APOE?",
    "Tell me what to investigate about amyloid clearance.",
    "What mechanisms underlie lipid transport in the brain?",
])
def test_specific_questions_proceed_to_research(offline, question):
    result = offline.graph.invoke(initial_state(question), config=config())
    assert result["needs_clarification"] is False
    assert result["out_of_scope"] is False
    offline.retrieval_calls.assert_called_once()
    offline.store.similarity_search_with_score.assert_called_once_with(question, k=3)
    assert result["retrieved_evidence"]
    assert result["findings"][0]["verification_status"] == "model_assessed_supported"
    assert result["relationships"][0]["relationship_status"] == "rule_extracted_candidate"
    assert not result.get("approved_relationships")
    assert "__interrupt__" in result
    assert not result["errors"]


def test_no_evidence_stops_without_fabricated_conclusions(offline):
    offline.store.similarity_search_with_score.return_value = []
    result = offline.graph.invoke(initial_state(APOE_QUESTION), config=config())
    offline.retrieval_calls.assert_called_once()
    assert result["retrieved_evidence"] == []
    assert result["out_of_scope"] is False
    assert not result["errors"]
    for field in ("research_summary", "findings", "relationships", "approved_relationships"):
        assert not result.get(field)
    assert "__interrupt__" not in result
    offline.summary.assert_not_called()
    offline.validation.assert_not_called()


def test_unsubstantiated_claim_does_not_become_a_finding(offline):
    offline.validation.return_value = response(
        '{"status": "insufficient_evidence", "reason": "Fixture does not support this claim."}'
    )
    result = offline.graph.invoke(initial_state(APOE_QUESTION), config=config())
    assert result["retrieved_evidence"]
    assert result["findings"] == []
    assert result["relationships"] == []
    assert result["approved_relationships"] == []
    assert result["review_status"] == "not_required"
    assert "__interrupt__" not in result


@pytest.mark.parametrize("approved", [True, False])
def test_human_approval_and_rejection_remain_functional(offline, approved):
    thread = config()
    paused = offline.graph.invoke(initial_state(APOE_QUESTION), config=thread)
    assert "__interrupt__" in paused
    candidates = paused["relationships"]
    assert not paused.get("approved_relationships")
    resumed = offline.graph.invoke(
        Command(resume={"approved": approved, "feedback": "Test reviewer decision."}),
        config=thread,
    )
    assert "__interrupt__" not in resumed
    assert resumed["review_status"] == ("approved" if approved else "rejected")
    assert resumed["review_feedback"] == "Test reviewer decision."
    assert resumed["approved_relationships"] == (candidates if approved else [])
    assert resumed["relationships"] == candidates
    for field in ("retrieved_evidence", "research_summary", "findings", "validation_results"):
        assert resumed[field] == paused[field]
    assert all(item["relationship_status"] == "rule_extracted_candidate" for item in candidates)
    offline.retrieval_calls.assert_called_once()


@pytest.mark.parametrize("field", ["needs_clarification", "out_of_scope"])
def test_retrieval_defensive_guard(offline, field):
    offline.research({**initial_state(APOE_QUESTION), field: True})
    offline.embeddings.assert_not_called()
    offline.chroma.assert_not_called()


def test_gate_clears_previous_scope_flags():
    result = clarification_agent({
        **initial_state(APOE_QUESTION), "needs_clarification": True,
        "clarification_question": "Old prompt", "out_of_scope": True,
        "scope_message": "Old scope message",
    })
    assert not result["needs_clarification"]
    assert not result["out_of_scope"]
    assert result["clarification_question"] == result["scope_message"] == ""


@pytest.mark.parametrize("question, expected", [
    ("What should I investigate next?", "Please clarify your research objective before continuing."),
    (BRCA_QUESTION, "This topic is outside the current indexed research collection."),
    (APOE_QUESTION, "The available evidence is insufficient to establish a candidate relationship."),
])
def test_streamlit_run_shows_actual_stop_reason(offline, question, expected):
    offline.store.similarity_search_with_score.return_value = []
    app = AppTest.from_file(str(APP_PATH)).run()
    assert not app.exception
    app.text_input(key="question_input").set_value(question)
    app.button[0].click().run()
    assert not app.exception
    messages = [element.value for kind in ("info", "warning", "caption") for element in getattr(app, kind)]
    assert expected in messages
    assert "No candidate relationships were extracted for this question." not in messages
    assert "No candidate relationships required human review." not in messages
    result = app.session_state["research_result"]
    if question != APOE_QUESTION:
        offline.retrieval_calls.assert_not_called()
        assert "Research Conclusion" not in [heading.value for heading in app.subheader]
        assert app.session_state["completed_nodes"] == ["clarification_agent"]
        assert not any("Human review was skipped" in message for message in messages)
    else:
        offline.retrieval_calls.assert_called_once()
        assert app.session_state["completed_nodes"] == ["clarification_agent", "research_agent"]
    if question == BRCA_QUESTION:
        assert result["scope_message"] in messages
        assert messages.count(result["scope_message"]) == 1
        assert messages.count(expected) == 1
        assert [item.value for item in app.tabs[0].info] == [
            "No relationships available for this question."
        ]
        assert [item.value for item in app.tabs[1].info] == [
            "No research summary available because this topic is outside the indexed collection."
        ]
        assert [item.value for item in app.tabs[2].info] == [
            "No indexed scientific evidence available for this question."
        ]
        assert [metric.value for metric in app.metric] == ["0", "0", "0"]
        offline.summary.assert_not_called()
        offline.validation.assert_not_called()


@pytest.mark.parametrize("supported", [True, False])
def test_streamlit_distinguishes_insufficient_support_and_extraction_criteria(offline, supported):
    offline.summary.return_value = response("APOE is a gene [pubmed_00000000].")
    if not supported:
        offline.validation.return_value = response(
            '{"status": "insufficient_evidence", "reason": "Insufficient fixture support."}'
        )
    result = offline.graph.invoke(initial_state(APOE_QUESTION), config=config())
    app = AppTest.from_file(str(APP_PATH))
    app.session_state["research_result"] = result
    app.run()
    assert not app.exception
    expected = (
        "No candidate relationship met the extraction criteria." if supported else
        "The available evidence is insufficient to establish a candidate relationship."
    )
    assert expected in [item.value for item in app.info]
    assert result["review_status"] == "not_required"


@pytest.mark.parametrize("approved", [True, False])
def test_streamlit_review_buttons_resume_real_workflow(offline, approved, monkeypatch):
    maps = importlib.import_module("src.visualization.relationship_map")
    map_display = Mock(wraps=maps.show_relationship_map)
    monkeypatch.setattr(maps, "show_relationship_map", map_display)
    app = AppTest.from_file(str(APP_PATH)).run()
    app.text_input(key="question_input").set_value(APOE_QUESTION)
    app.button[0].click().run()
    assert not app.exception
    assert "__interrupt__" in app.session_state["research_result"]
    paused = deepcopy(app.session_state["research_result"])
    app.text_area(key="review_feedback").set_value("UI review test")
    label = "Approve Relationships" if approved else "Reject Relationships"
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception
    result = app.session_state["research_result"]
    assert result["review_status"] == ("approved" if approved else "rejected")
    assert result["review_feedback"] == "UI review test"
    assert bool(result["approved_relationships"]) is approved
    assert "human_review_agent" in app.session_state["completed_nodes"]
    assert "#### Human review decision" in [item.value for item in app.tabs[0].markdown]
    assert "**Approved relationships**" in [item.value for item in app.tabs[0].markdown]
    assert map_display.call_args.kwargs["review_status"] == result["review_status"]
    assert map_display.call_args.args[0] == paused["relationships"]
    for field in ("retrieved_evidence", "research_summary", "findings", "relationships", "validation_results"):
        assert result[field] == paused[field]
    if approved:
        assert any("does not independently establish scientific validity" in item.value for item in app.caption)
        assert result["approved_relationships"] == paused["relationships"]
    else:
        assert "Rejected by researcher" in [item.value for item in app.warning]
        assert "UI review test" in [item.value for item in app.text]
        assert result["approved_relationships"] == []


RISK_OPTION = "Genetic risk associated with APOE variants"
RISK_QUESTION = "What does the indexed research say about APOE variants and Alzheimer's disease risk?"
CUSTOM_OPTION = "Other — specify my research question"
NOT_STARTED = "Research has not started. Please clarify your question to continue."


def click_button(app, label):
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception


def request_clarification(app):
    app.text_input(key="question_input").set_value("What should I investigate next?")
    click_button(app, "Run research")
    return app


def test_clarification_requires_selection_without_duplicate_prompt(offline):
    app = request_clarification(AppTest.from_file(str(APP_PATH)).run())
    result = app.session_state["research_result"]
    assert result["needs_clarification"]
    assert app.radio[0].value is None
    assert app.radio[0].options == [
        RISK_OPTION,
        "Biological mechanisms involving APOE",
        "Therapeutic approaches related to APOE and Alzheimer's disease",
        CUSTOM_OPTION,
    ]
    assert app.button(key="continue_research").disabled
    assert [metric.value for metric in app.metric] == ["0", "0", "0"]
    assert result["clarification_question"] not in [item.value for item in app.info]
    assert app.radio[0].label == "Which aspect of APOE research would you like to investigate?"
    assert sum(item.value == "#### Help us refine your research question" for item in app.markdown) == 1
    assert "Please clarify your research objective before continuing." in [item.value for item in app.warning]
    for tab in app.tabs:
        assert NOT_STARTED in [item.value for item in tab.info]
        assert result["clarification_question"] not in [item.value for item in tab.info]
    # An ordinary rerun cannot implicitly choose an option or begin retrieval.
    app.run()
    assert app.radio[0].value is None
    offline.retrieval_calls.assert_not_called()
    offline.summary.assert_not_called()
    offline.validation.assert_not_called()


@pytest.mark.parametrize("approved", [True, False])
def test_complete_clarification_to_research_and_review(offline, approved):
    app = request_clarification(AppTest.from_file(str(APP_PATH)).run())
    stopped_thread = app.session_state["thread_id"]
    offline.retrieval_calls.assert_not_called()
    app.radio[0].set_value(RISK_OPTION).run()
    assert not app.exception
    assert not app.button(key="continue_research").disabled
    assert app.session_state["research_result"]["needs_clarification"]
    offline.retrieval_calls.assert_not_called()
    click_button(app, "Continue Research")
    result = app.session_state["research_result"]
    assert app.session_state["thread_id"] != stopped_thread
    assert result["question"] == RISK_QUESTION
    assert app.text_input(key="question_input").value == RISK_QUESTION
    assert not result["needs_clarification"]
    assert not result["out_of_scope"]
    offline.store.similarity_search_with_score.assert_called_once_with(RISK_QUESTION, k=3)
    assert result["retrieved_evidence"]
    assert result["research_summary"] == SUMMARY
    assert result["findings"][0]["verification_status"] == "model_assessed_supported"
    assert result["relationships"][0]["relationship_status"] == "rule_extracted_candidate"
    assert not result.get("approved_relationships")
    assert "__interrupt__" in result
    assert [metric.value for metric in app.metric] == ["1", "1", "1"]
    assert "analysis_agent" in app.session_state["completed_nodes"]
    assert "human_review_agent" not in app.session_state["completed_nodes"]
    assert not any(button.label == "Continue Research" for button in app.button)
    app.text_area(key="review_feedback").set_value("Reviewed after clarification")
    click_button(app, "Approve Relationships" if approved else "Reject Relationships")
    reviewed = app.session_state["research_result"]
    assert reviewed["review_status"] == ("approved" if approved else "rejected")
    assert bool(reviewed["approved_relationships"]) is approved
    assert reviewed["review_feedback"] == "Reviewed after clarification"
    assert reviewed["relationships"] == result["relationships"]
    offline.retrieval_calls.assert_called_once()


@pytest.mark.parametrize("option, expected", [
    ("Biological mechanisms involving APOE",
     "What biological mechanisms link APOE variants to Alzheimer's disease?"),
    ("Therapeutic approaches related to APOE and Alzheimer's disease",
     "What therapeutic approaches targeting APOE have been studied in Alzheimer's disease?"),
])
def test_other_preset_objectives_use_specific_questions(offline, option, expected):
    app = request_clarification(AppTest.from_file(str(APP_PATH)).run())
    app.radio[0].set_value(option).run()
    offline.retrieval_calls.assert_not_called()
    click_button(app, "Continue Research")
    assert app.session_state["research_result"]["question"] == expected
    offline.store.similarity_search_with_score.assert_called_once_with(expected, k=3)


@pytest.mark.parametrize("question", [
    "How does epsilon 2 affect Alzheimer's disease risk?",
    BRCA_QUESTION,
    "What should I research next?",
])
def test_custom_clarification_question_reenters_existing_gate(offline, question):
    app = request_clarification(AppTest.from_file(str(APP_PATH)).run())
    first_thread = app.session_state["thread_id"]
    app.radio[0].set_value(CUSTOM_OPTION).run()
    app.text_input[1].set_value("  " + question + "  ").run()
    offline.retrieval_calls.assert_not_called()
    click_button(app, "Continue Research")
    result = app.session_state["research_result"]
    assert result["question"] == question
    assert app.text_input(key="question_input").value == question
    assert app.session_state["thread_id"] != first_thread
    if question == BRCA_QUESTION:
        assert result["out_of_scope"]
        offline.retrieval_calls.assert_not_called()
    elif question == "What should I research next?":
        assert result["needs_clarification"]
        assert app.radio[0].value is None
        assert app.button(key="continue_research").disabled
        offline.retrieval_calls.assert_not_called()
    else:
        assert not result["needs_clarification"]
        offline.store.similarity_search_with_score.assert_called_once_with(question, k=3)


@pytest.mark.parametrize("empty", ["", "   "])
def test_empty_custom_question_cannot_be_submitted(offline, empty):
    app = request_clarification(AppTest.from_file(str(APP_PATH)).run())
    thread = app.session_state["thread_id"]
    app.radio[0].set_value(CUSTOM_OPTION).run()
    app.text_input[1].set_value(empty).run()
    assert app.button(key="continue_research").disabled
    assert app.session_state["thread_id"] == thread
    assert app.session_state["research_result"]["needs_clarification"]
    offline.retrieval_calls.assert_not_called()
    offline.summary.assert_not_called()


def test_switching_from_preset_to_empty_custom_disables_continue(offline):
    app = request_clarification(AppTest.from_file(str(APP_PATH)).run())
    app.radio[0].set_value(RISK_OPTION).run()
    assert not app.button(key="continue_research").disabled
    app.radio[0].set_value(CUSTOM_OPTION).run()
    assert not app.exception
    assert app.text_input[1].value == ""
    assert app.button(key="continue_research").disabled
    offline.retrieval_calls.assert_not_called()


@pytest.mark.parametrize("empty", ["", "   "])
def test_clearing_custom_question_disables_continue(offline, empty):
    app = request_clarification(AppTest.from_file(str(APP_PATH)).run())
    app.radio[0].set_value(CUSTOM_OPTION).run()
    app.text_input[1].set_value(APOE_QUESTION).run()
    assert not app.button(key="continue_research").disabled
    app.text_input[1].set_value(empty).run()
    assert not app.exception
    assert app.button(key="continue_research").disabled
    assert app.session_state["research_result"]["needs_clarification"]
    offline.retrieval_calls.assert_not_called()


def test_clarification_starts_clean_after_previous_approved_research(offline):
    app = AppTest.from_file(str(APP_PATH)).run()
    app.text_input(key="question_input").set_value(APOE_QUESTION)
    click_button(app, "Run research")
    click_button(app, "Approve Relationships")
    assert app.session_state["research_result"]["approved_relationships"]
    approved_thread = app.session_state["thread_id"]
    request_clarification(app)
    stopped = app.session_state["research_result"]
    assert app.session_state["thread_id"] != approved_thread
    for field in ("retrieved_evidence", "findings", "relationships", "approved_relationships",
                  "research_summary", "review_status", "validation_results"):
        assert not stopped.get(field)
    assert [metric.value for metric in app.metric] == ["0", "0", "0"]
    app.radio[0].set_value(RISK_OPTION).run()
    # The clarified run must not retain the previous evidence or approval,
    # even if retrieval returns nothing this time.
    offline.store.similarity_search_with_score.return_value = []
    click_button(app, "Continue Research")
    result = app.session_state["research_result"]
    for field in ("retrieved_evidence", "findings", "relationships", "approved_relationships",
                  "research_summary", "review_status", "validation_results"):
        assert not result.get(field)
    assert not result["needs_clarification"]
    assert app.session_state["completed_nodes"] == ["clarification_agent", "research_agent"]
    assert offline.retrieval_calls.call_count == 2
    assert offline.summary.call_count == 1


def test_clarified_run_requires_evidence_support_for_candidates(offline):
    app = request_clarification(AppTest.from_file(str(APP_PATH)).run())
    app.radio[0].set_value(RISK_OPTION).run()
    offline.validation.return_value = response(
        '{"status": "insufficient_evidence", "reason": "Fixture lacks supporting evidence."}'
    )
    click_button(app, "Continue Research")
    result = app.session_state["research_result"]
    assert result["retrieved_evidence"]
    assert result["research_summary"]
    assert result["findings"] == []
    assert result["relationships"] == []
    assert result["approved_relationships"] == []
    assert "__interrupt__" not in result
    assert "The available evidence is insufficient to establish a candidate relationship." in [
        item.value for item in app.info
    ]


@pytest.mark.parametrize("question, statements, short_answer, kind, question_type, has_links", [
    (
        "Does APOE epsilon 4 guarantee Alzheimer's disease?",
        [
            "APOE epsilon 4 increases Alzheimer's disease risk",
            "APOE epsilon 4 does not guarantee that someone will develop Alzheimer's disease",
        ],
        "APOE ε4 is associated with increased Alzheimer's disease risk, but carrying "
        "this variant does not guarantee that a person will develop the disease.",
        "no", "yes_no", True,
    ),
    (
        "How does APOE epsilon 2 affect Alzheimer's disease risk?",
        ["APOE epsilon 2 is associated with reduced Alzheimer's disease risk"],
        "APOE ε2 is associated with reduced Alzheimer's disease risk in the indexed findings, "
        "but this association does not establish certainty for an individual.",
        "explanatory", "open", True,
    ),
    (
        "What biological mechanisms involve APOE?",
        ["APOE participates in lipid transport and amyloid clearance"],
        "The indexed findings implicate APOE in lipid transport and amyloid clearance, "
        "but do not establish a single causal mechanism for Alzheimer's disease.",
        "explanatory", "open", False,
    ),
])
def test_summary_conclusion_uses_validated_findings_above_unchanged_summary(
    offline, question, statements, short_answer, kind, question_type, has_links
):
    summary = " ".join(statement + " [pubmed_00000000]." for statement in statements)
    offline.summary.return_value = response(summary)
    offline.validation.return_value = response(json.dumps({
        "status": "supported", "reason": "Synthetic fixture assessment.",
        "conclusion": {"question_type": question_type, "answer": kind,
                       "text": short_answer, "supported": True},
    }))
    # Supply matching synthetic evidence at the mocked retrieval boundary.
    offline.store.similarity_search_with_score.return_value[0][0].page_content = summary
    app = AppTest.from_file(str(APP_PATH)).run()
    assert "Research Conclusion" not in [heading.value for heading in app.subheader]
    app.text_input(key="question_input").set_value(question)
    click_button(app, "Run research")
    summary_tab = app.tabs[1]
    assert [heading.value for heading in summary_tab.subheader] == [
        "Research Conclusion", "Research Summary"
    ]
    # The direct answer is a separate assessed field, not a summary excerpt.
    texts = [item.value for item in summary_tab.markdown]
    answer = ("No. " if kind == "no" else "") + short_answer
    assert answer in texts
    assert len(answer.split()) <= 45
    assert "pubmed_00000000" in summary
    assert summary in texts
    assert summary in texts[texts.index(answer) + 1:]
    assert "#### Model-assessed findings" in texts
    assert app.session_state["research_result"]["research_summary"] == summary
    assert bool(app.session_state["research_result"]["relationships"]) is has_links
    offline.summary.assert_called_once()
    assert offline.validation.call_count == len(statements)
    if not has_links:
        assert "__interrupt__" not in app.session_state["research_result"]
        return
    assert "__interrupt__" in app.session_state["research_result"]
    # A human decision changes approval state, not the scientific conclusion.
    click_button(app, "Approve Relationships")
    assert app.session_state["research_result"]["review_status"] == "approved"
    assert answer in [item.value for item in app.tabs[1].markdown]
    offline.summary.assert_called_once()
    assert offline.validation.call_count == len(statements)


@pytest.mark.parametrize("has_evidence", [True, False])
def test_summary_conclusion_reports_insufficient_evidence(offline, has_evidence):
    if has_evidence:
        offline.validation.return_value = response(
            '{"status": "insufficient_evidence", "reason": "Synthetic claim lacks support."}'
        )
    else:
        offline.store.similarity_search_with_score.return_value = []
    app = AppTest.from_file(str(APP_PATH)).run()
    app.text_input(key="question_input").set_value(APOE_QUESTION)
    click_button(app, "Run research")
    assert "Research Conclusion" in [heading.value for heading in app.tabs[1].subheader]
    assert "Insufficient evidence to reach a reliable conclusion" in [
        item.value for item in app.tabs[1].markdown
    ]
    assert not app.session_state["research_result"].get("findings")
    assert not app.session_state["research_result"].get("relationships")


@pytest.mark.parametrize("status", ["supported", "partially_supported", "unsupported", "insufficient_evidence"])
def test_direct_answer_uses_existing_assessment_call_and_supported_claim_only(offline, status):
    offline.validation.return_value = response(json.dumps({
        "status": status, "reason": "Synthetic fixture.",
        "conclusion": {"question_type": "open", "answer": "explanatory",
                       "text": "The indexed evidence indicates a risk association with limitations.",
                       "supported": True},
    }))
    result = offline.graph.invoke(initial_state(APOE_QUESTION), config=config())
    offline.summary.assert_called_once()
    offline.validation.assert_called_once()
    messages = offline.validation.call_args.kwargs["messages"]
    assert APOE_QUESTION in messages[1]["content"]
    assert result["research_summary"] == SUMMARY
    claim = next(check for check in result["validation_results"]
                 if check["check"] == "claim_evidence_validation")["claims"][0]
    assert ("conclusion" in claim) is (status == "supported")
    if status == "supported":
        assert result["findings"][0]["conclusion"] == claim["conclusion"]
        assert claim["conclusion"]["question"] == APOE_QUESTION
        assert "__interrupt__" in result
    else:
        assert not result["findings"]
        assert not result["relationships"]


@pytest.mark.parametrize("conclusion", [None, "plain text", ["an invalid answer"]])
def test_optional_answer_format_never_breaks_existing_findings_or_review(offline, conclusion):
    offline.validation.return_value = response(json.dumps({
        "status": "supported", "reason": "Synthetic fixture.", "conclusion": conclusion,
    }))
    thread = config()
    result = offline.graph.invoke(initial_state(APOE_QUESTION), config=thread)
    assert result["findings"]
    assert "conclusion" not in result["findings"][0]
    assert "__interrupt__" in result
    rejected = offline.graph.invoke(Command(resume={"approved": False}), config=thread)
    assert rejected["review_status"] == "rejected"
    assert rejected["approved_relationships"] == []
    offline.validation.assert_called_once()


@pytest.mark.parametrize("approved", [True, False])
def test_out_of_scope_question_after_review_shows_only_empty_results(offline, approved):
    app = AppTest.from_file(str(APP_PATH)).run()
    app.text_input(key="question_input").set_value(APOE_QUESTION)
    click_button(app, "Run research")
    click_button(app, "Approve Relationships" if approved else "Reject Relationships")
    reviewed = app.session_state["research_result"]
    assert reviewed["review_status"] == ("approved" if approved else "rejected")
    previous_thread = app.session_state["thread_id"]
    app.text_input(key="question_input").set_value(BRCA_QUESTION)
    click_button(app, "Run research")
    result = app.session_state["research_result"]
    assert result["out_of_scope"]
    assert app.session_state["thread_id"] != previous_thread
    assert [metric.value for metric in app.metric] == ["0", "0", "0"]
    expected = [
        "No relationships available for this question.",
        "No research summary available because this topic is outside the indexed collection.",
        "No indexed scientific evidence available for this question.",
    ]
    for tab, message in zip(app.tabs[:3], expected):
        assert [item.value for item in tab.info] == [message]
        assert reviewed["research_summary"] not in [item.value for item in tab.markdown]
    for field in ("retrieved_evidence", "research_summary", "findings", "relationships",
                  "approved_relationships", "validation_results"):
        assert not result.get(field)
    assert "__interrupt__" not in result
    offline.retrieval_calls.assert_called_once()
    offline.summary.assert_called_once()
    offline.validation.assert_called_once()


@pytest.mark.parametrize("feedback", [
    "", "   ",
    "The candidate needs further replication.\nPlease check the population studied.",
])
def test_rejection_preserves_candidates_and_only_displays_actual_reason(offline, feedback):
    app = AppTest.from_file(str(APP_PATH)).run()
    app.text_input(key="question_input").set_value(APOE_QUESTION)
    click_button(app, "Run research")
    paused = deepcopy(app.session_state["research_result"])
    app.text_area(key="review_feedback").set_value(feedback)
    click_button(app, "Reject Relationships")
    result = app.session_state["research_result"]
    assert result["review_status"] == "rejected"
    assert result["review_feedback"] == feedback
    assert result["approved_relationships"] == []
    for field in ("relationships", "retrieved_evidence", "research_summary", "findings", "validation_results"):
        assert result[field] == paused[field]
    assert "Rejected by researcher" in [item.value for item in app.warning]
    assert "#### Candidate genetic relationships" in [item.value for item in app.tabs[0].markdown]
    assert len(app.tabs[0].expander) == len(paused["relationships"])
    displayed_text = [item.value for item in app.text]
    if feedback.strip():
        assert feedback in displayed_text
        assert "**Rejection reason**" in [item.value for item in app.markdown]
    else:
        assert "**Rejection reason**" not in [item.value for item in app.markdown]
        assert displayed_text == []
    offline.retrieval_calls.assert_called_once()
    offline.summary.assert_called_once()
    offline.validation.assert_called_once()
