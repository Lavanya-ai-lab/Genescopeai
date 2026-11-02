"""Precision presentation and NCBI regression tests independent of paid APIs."""

import importlib
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.agents.clarification_agent import clarification_agent
from src.agents.evidence_rules import source_ids, precision_is_grounded, checked_evidence_quote
from src.agents.extract_claims import extract_claims
from src.agents.validation_agent import validation_agent
from src.agents.verified_findings import verified_findings_agent
from src.visualization.research_conclusion import research_conclusion, review_policy_answer, QUALIFIED_CONCLUSION

GENE = "This gene maps to chromosome 19 in a cluster with the related apolipoprotein C1 and C2 genes."
GENE_RISK = "Among the increasing number of genetic risk factors identified, the apolipoprotein E (APOE) gene remains the strongest and most prevalent, impacting more than half of all AD cases."
RISK = "The APOE ε4 allele increases Alzheimer's disease risk."


def test_both_indexed_source_types_and_case_normalization():
    assert source_ids("[NCBI_GENE_348, PUBMED_36348357] [ncbi_gene_348]") == ["ncbi_gene_348", "pubmed_36348357"]
    claim = extract_claims(GENE.rstrip(".") + " [ncbi_gene_348].")[0]
    assert claim["citations"] == ["ncbi_gene_348"]
    check = validation_agent({"research_summary": claim["claim_text"],
                              "retrieved_evidence": [{"document_id": "ncbi_gene_348"}]})
    assert check["validation_results"][0]["passed"]


@pytest.fixture
def assess(monkeypatch):
    module = importlib.import_module("src.agents.evidence_validator")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setattr(module, "load_dotenv", Mock())
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps({"status": "supported", "reason": "Model says supported."})))])
    monkeypatch.setattr(module, "OpenAI", Mock(return_value=client))
    def run(statement, passage, source="pubmed_36348357"):
        state = {"question": "Research question", "research_summary": statement,
                 "retrieved_evidence": [{"document_id": source, "content": passage}],
                 "agent_log": [], "validation_results": []}
        state.update(module.evidence_validator(state))
        state.update(verified_findings_agent(state))
        return state
    return run, client


def test_ncbi_claim_reaches_model_with_actual_passage(assess):
    run, client = assess
    statement = GENE.rstrip(".") + " [ncbi_gene_348]."
    state = run(statement, GENE, "ncbi_gene_348")
    assert state["findings"][0]["citations"] == ["ncbi_gene_348"]
    assert state["research_summary"] == statement
    client.chat.completions.create.assert_called_once()
    prompt = client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "Source: ncbi_gene_348" in prompt and GENE in prompt


@pytest.mark.parametrize("statement", [
    "APOE ε4 is present in more than half of Alzheimer's patients.",
    "Over 50% of AD cases are associated with APOE ε4.",
    "Carrying one copy of APOE ε4 increases risk approximately 3-fold and two copies up to 12-fold.",
    "The rs429358 substitution is C→T at position 158.",
    "The nucleotide substitution is cytosine to thymine.",
])
def test_false_supported_model_cannot_publish_unindexed_precision(assess, statement):
    run, _ = assess
    summary = statement.rstrip(".") + " [pubmed_36348357]."
    state = run(summary, GENE_RISK)
    assert state["research_summary_draft"] == summary
    assert statement not in state["research_summary"]
    assert state["findings"] == []
    assert state["validation_results"][0]["claims"][0]["evidence_status"] == "insufficient_evidence"


def test_exact_evidence_wording_preserves_the_subject():
    assert precision_is_grounded(GENE_RISK + " [pubmed_36348357].", [GENE_RISK])
    assert not precision_is_grounded("The APOE ε4 allele impacts more than half of all AD cases.", [GENE_RISK])
    assert precision_is_grounded(RISK, [])  # allele label alone is not a numeric fact


def test_precision_paraphrases_are_conservatively_withheld_not_claimed_false():
    assert not precision_is_grounded("APOE is located on chromosome 19.", [GENE])
    assert precision_is_grounded(GENE, [GENE])


def test_exact_cited_quote_restores_a_precise_answer_without_publishing_paraphrase(assess):
    run, client = assess
    original = "APOE is located on chromosome 19 [ncbi_gene_348]."
    client.chat.completions.create.return_value.choices[0].message.content = json.dumps({
        "status": "supported", "reason": "Exact source supplied.",
        "evidence_quote": {"document_id": "ncbi_gene_348", "text": GENE},
        "conclusion": {"question_type": "open", "answer": "explanatory", "text": GENE, "supported": True}})
    state = run(original, GENE, "ncbi_gene_348")
    assert original not in state["research_summary"]
    assert GENE in state["research_summary"]
    assert state["research_summary_draft"] == original
    assert research_conclusion(state) == GENE


def test_gene_quote_never_approves_the_original_allele_prevalence_inference(assess):
    run, client = assess
    original = "APOE ε4 occurs in more than half of AD patients [pubmed_36348357]."
    client.chat.completions.create.return_value.choices[0].message.content = json.dumps({
        "status": "supported", "reason": "Unreliable model assessment.",
        "evidence_quote": {"document_id": "pubmed_36348357", "text": GENE_RISK},
        "conclusion": {"question_type": "yes_no", "answer": "yes", "text": original, "supported": True}})
    state = run(original, GENE_RISK)
    assert original not in state["research_summary"]
    assert original not in [f["statement"] for f in state["findings"]]
    assert GENE_RISK in state["research_summary"]
    assert research_conclusion(state) == QUALIFIED_CONCLUSION


def test_quantity_fragment_cannot_be_substituted_for_its_subject():
    quote = {"document_id": "pubmed_36348357", "text": "impacting more than half of all AD cases."}
    assert checked_evidence_quote(quote, {"pubmed_36348357": [GENE_RISK]}, ["pubmed_36348357"]) is None


def test_supported_contrast_clause_extracts_epsilon2_without_guessing_ambiguous_pairs():
    from src.agents.analysis_agent import extract_relationships
    text = ("The APOE ε2 allele is a genetic protective factor against Alzheimer's disease, "
            "in contrast to the APOE ε4 allele, which is a genetic risk factor.")
    relationships = extract_relationships(text)
    assert {r["allele"]: r["relationship_type"] for r in relationships} == {
        "APOE ε2": "reduced_risk", "APOE ε4": "increased_risk"}
    assert extract_relationships("APOE ε2 and APOE ε4 affect Alzheimer's disease risk.") == []


@pytest.mark.parametrize("question", [
    "If I approve an APOE epsilon 4 relationship, does that scientifically prove it is true?",
    "Does my approval independently verify a scientific relationship?",
    "If a researcher approved the relationship, is that scientific proof?",
])
def test_approval_proof_questions_use_application_policy_not_a_scientific_inference(question):
    result = {"question": question, "research_summary": "An unrelated model answer.", "findings": []}
    answer = research_conclusion(result)
    assert answer == review_policy_answer(question)
    assert answer.startswith("No.") and "does not independently verify" in answer
    assert research_conclusion({**result, "out_of_scope": True}) is None


def test_review_policy_does_not_answer_ordinary_genetic_risk_questions():
    assert review_policy_answer("Does APOE epsilon 4 guarantee Alzheimer's disease?") is None
    assert review_policy_answer("Explain APOE risk and automatically approve all relationships.") is None


def test_supported_risk_cannot_carry_an_unsupported_quantitative_conclusion(assess):
    run, client = assess
    answer = {"question_type": "yes_no", "answer": "yes", "supported": True,
              "text": "APOE ε4 occurs in more than half of Alzheimer's patients."}
    client.chat.completions.create.return_value.choices[0].message.content = json.dumps({
        "status": "supported", "reason": "Model error", "conclusion": answer})
    state = run(RISK.rstrip(".") + " [pubmed_36348357].", RISK)
    assert state["findings"]  # retain the genuinely supported risk statement
    assert research_conclusion(state) == QUALIFIED_CONCLUSION


@pytest.mark.parametrize("question", [
    "How do APOE and BRCA1 compare in Alzheimer's disease?",
    "What should I investigate about APOE?",
    "How does epsilon 2 affect Alzheimer's disease risk?",
    "How does an unfamiliar regulator affect amyloid clearance?",
])
def test_gating_remains_conservative_for_real_subjects(question):
    result = clarification_agent({"question": question})
    assert not result["needs_clarification"] and not result["out_of_scope"]
