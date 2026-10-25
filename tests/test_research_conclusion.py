"""Conclusion presentation checks with synthetic structured assessments."""

from copy import deepcopy

import pytest

from src.visualization.research_conclusion import (
    INSUFFICIENT_CONCLUSION,
    QUALIFIED_CONCLUSION,
    research_conclusion,
)


QUESTION = "Does APOE epsilon 4 guarantee Alzheimer's disease?"
STATEMENT = "APOE epsilon 4 increases risk but does not guarantee Alzheimer's disease."
DIRECT_ANSWER = (
    "APOE ε4 is associated with increased Alzheimer's disease risk, but carrying "
    "this variant does not guarantee that a person will develop the disease."
)
SOURCE = "pubmed_00000000"


def assessed_result(question=QUESTION, text=DIRECT_ANSWER, answer="no", question_type="yes_no"):
    conclusion = {
        "question": question, "text": text, "answer": answer,
        "question_type": question_type, "supported": True,
    }
    claim = {"claim_id": "claim_1", "claim_text": STATEMENT,
             "citations": [SOURCE], "evidence_status": "supported",
             "conclusion": conclusion}
    return {
        "question": question,
        "research_summary": STATEMENT,
        "retrieved_evidence": [{"document_id": SOURCE, "content": "Synthetic evidence"}],
        "findings": [{"claim_id": "claim_1", "statement": STATEMENT,
                      "citations": [SOURCE], "verification_status": "model_assessed_supported",
                      "conclusion": deepcopy(conclusion)}],
        "validation_results": [{"check": "claim_evidence_validation", "claims": [claim]}],
    }


def update_conclusion(result, **fields):
    for entry in (result["findings"][0], result["validation_results"][0]["claims"][0]):
        entry["conclusion"].update(fields)


def test_guarantee_answer_is_direct_short_and_not_a_summary_excerpt():
    result = assessed_result()
    before = deepcopy(result)
    assert research_conclusion(result) == "No. " + DIRECT_ANSWER
    assert len(research_conclusion(result).split()) <= 45
    assert result == before


def test_reported_duplicate_no_is_removed_without_changing_scientific_wording():
    body = (
        "APOE epsilon 4 does not guarantee Alzheimer's disease, "
        "as some carriers remain disease-free."
    )
    result = assessed_result(text="No, " + body)
    before = deepcopy(result)
    assert research_conclusion(result) == "No. " + body
    assert result == before


@pytest.mark.parametrize("kind, label", [
    ("yes", "Yes"), ("no", "No"), ("inconclusive", "The evidence is inconclusive"),
])
@pytest.mark.parametrize("separator", [", ", ". ", ": "])
def test_existing_answer_prefix_is_displayed_once(kind, label, separator):
    body = "The interpretation is limited to the supplied experimental conditions."
    result = assessed_result(answer=kind, text=label + separator + body)
    assert research_conclusion(result) == label + ". " + body


def test_repeated_mixed_case_answer_labels_are_normalized():
    result = assessed_result(text=" no. NO,\n" + DIRECT_ANSWER)
    assert research_conclusion(result) == "No. " + DIRECT_ANSWER


def test_negation_in_the_answer_body_is_preserved():
    body = "No increased risk was observed in the studied population."
    result = assessed_result(text=body)
    assert research_conclusion(result) == "No. " + body


@pytest.mark.parametrize("text", ["No,", "No. No,", "Yes, an affirmative answer."])
def test_empty_or_conflicting_prefixed_answer_gets_qualified_fallback(text):
    assert research_conclusion(assessed_result(text=text)) == QUALIFIED_CONCLUSION


@pytest.mark.parametrize("kind, prefix", [
    ("yes", "Yes. "), ("no", "No. "),
    ("inconclusive", "The evidence is inconclusive. "),
])
def test_yes_no_prefix_comes_from_assessment_not_question_keywords(kind, prefix):
    result = assessed_result(question="Is the proposed interpretation supported?", answer=kind,
                             text="The interpretation is limited to the supplied experimental conditions.")
    assert research_conclusion(result).startswith(prefix)


@pytest.mark.parametrize("question, text", [
    (
        "How does APOE epsilon 2 affect Alzheimer's disease risk?",
        "APOE ε2 is associated with reduced Alzheimer's disease risk in the indexed findings, "
        "but this association does not establish certainty for an individual.",
    ),
    (
        "What biological mechanisms involve APOE?",
        "The indexed findings implicate APOE in lipid transport and amyloid clearance, "
        "but do not establish a single causal mechanism for Alzheimer's disease.",
    ),
])
def test_open_questions_use_structured_qualified_answer(question, text):
    result = assessed_result(question=question, text=text, answer="explanatory", question_type="open")
    assert research_conclusion(result) == text
    assert len(text.split()) <= 45


@pytest.mark.parametrize("field", ["needs_clarification", "out_of_scope"])
def test_stopped_questions_have_no_conclusion_even_with_stale_findings(field):
    result = assessed_result()
    result[field] = True
    assert research_conclusion(result) is None


@pytest.mark.parametrize("field", ["retrieved_evidence", "findings", "validation_results", "research_summary"])
def test_missing_support_returns_insufficient_evidence(field):
    result = assessed_result()
    result[field] = [] if field != "research_summary" else ""
    assert research_conclusion(result) == INSUFFICIENT_CONCLUSION


@pytest.mark.parametrize("status", ["partially_supported", "unsupported", "insufficient_evidence"])
def test_unsupported_claim_cannot_provide_conclusion(status):
    result = assessed_result()
    result["validation_results"][0]["claims"][0]["evidence_status"] = status
    assert research_conclusion(result) == INSUFFICIENT_CONCLUSION


@pytest.mark.parametrize("fields", [
    {"supported": False}, {"supported": "true"}, {"question": "An older question"},
    {"answer": "explanatory"}, {"answer": ["no"]}, {"answer": "unknown"},
    {"question_type": []}, {"text": ""}, {"text": None},
    {"text": "Unsupported source [pubmed_99999999]."},
    {"text": "First sentence. Second sentence. Third sentence."},
])
def test_unsuitable_direct_answer_receives_qualified_fallback(fields):
    result = assessed_result()
    update_conclusion(result, **fields)
    assert research_conclusion(result) == QUALIFIED_CONCLUSION


def test_long_answer_is_declined_without_truncating_qualification():
    result = assessed_result(text=(
        "APOE epsilon 4 is associated with increased Alzheimer's disease risk across the "
        "populations described in the supplied research, and the association depends on "
        "study design, age, genetic background, environmental conditions, and other "
        "factors that require careful interpretation, but carrying this variant does "
        "not guarantee that an individual will develop the disease."
    ))
    assert research_conclusion(result) == QUALIFIED_CONCLUSION


@pytest.mark.parametrize("words, expected", [(44, True), (45, False)])
def test_word_limit_includes_yes_no_prefix(words, expected):
    result = assessed_result(text=" ".join(["word"] * words) + ".")
    answer = research_conclusion(result)
    assert (answer != QUALIFIED_CONCLUSION) is expected
    assert len(answer.split()) <= 45


def test_legacy_findings_without_direct_answer_are_not_rewritten_using_keywords():
    result = assessed_result()
    for entry in (result["findings"][0], result["validation_results"][0]["claims"][0]):
        entry.pop("conclusion")
    assert research_conclusion(result) == QUALIFIED_CONCLUSION


def test_modified_or_unassessed_answer_is_not_displayed():
    result = assessed_result()
    result["findings"][0]["conclusion"]["text"] = "An unassessed replacement answer."
    assert research_conclusion(result) == QUALIFIED_CONCLUSION


@pytest.mark.parametrize("field", ["citations", "statement"])
def test_stale_or_uncited_findings_cannot_support_conclusion(field):
    result = assessed_result()
    result["findings"][0][field] = ["pubmed_99999999"] if field == "citations" else "Old statement."
    assert research_conclusion(result) == INSUFFICIENT_CONCLUSION


def test_stale_findings_outside_summary_are_not_reused():
    result = assessed_result()
    result["research_summary"] = "A different summary."
    assert research_conclusion(result) == INSUFFICIENT_CONCLUSION


def test_human_approved_candidates_are_not_a_source_for_conclusions():
    result = assessed_result()
    result.update({"findings": [], "review_status": "approved",
                   "approved_relationships": [{"statement": STATEMENT}]})
    assert research_conclusion(result) == INSUFFICIENT_CONCLUSION


def test_error_state_does_not_receive_confident_answer():
    result = assessed_result()
    result["errors"] = ["Validation failed"]
    assert research_conclusion(result) == INSUFFICIENT_CONCLUSION


def test_conflicting_assessed_polarities_are_not_resolved_by_picking_shorter_text():
    result = assessed_result()
    finding = deepcopy(result["findings"][0])
    claim = deepcopy(result["validation_results"][0]["claims"][0])
    finding["claim_id"] = claim["claim_id"] = "claim_2"
    finding["conclusion"]["answer"] = claim["conclusion"]["answer"] = "yes"
    result["findings"].append(finding)
    result["validation_results"][0]["claims"].append(claim)
    assert research_conclusion(result) == QUALIFIED_CONCLUSION
