"""Present concise answers assessed in the existing evidence-review call.

No scientific inference or keyword-based rewriting happens in the UI. Old
results without a structured answer receive a qualified fallback.
"""

import re
from src.agents.evidence_rules import source_ids, precision_is_grounded, requires_exact_precision


INSUFFICIENT_CONCLUSION = "Insufficient evidence to reach a reliable conclusion"
QUALIFIED_CONCLUSION = (
    "The evidence is inconclusive for a direct answer from the assessed findings. "
    "Please review the detailed summary and its limitations."
)
MAX_CONCLUSION_WORDS = 45
ANSWER_PREFIXES = {
    "yes": "Yes. ",
    "no": "No. ",
    "inconclusive": "The evidence is inconclusive. ",
    "explanatory": "",
}
LEADING_ANSWER = re.compile(
    r"^(yes|no|the evidence is inconclusive)\s*[,.:;!?]\s*", re.IGNORECASE
)
REVIEW_ACTION = re.compile(
    r"\b(?:i|we|you|humans?|researchers?|reviewers?)\s+(?:have\s+)?approv(?:e|ed)\b"
    r"|\b(?:my|our|human|researcher|reviewer)\s+approval\b", re.I
)
PROOF_REQUEST = re.compile(r"\b(?:prove|proves|proof|verify|verified|verification|scientifically|true)\b", re.I)


def review_policy_answer(question):
    """An application invariant, not a keyword-based biological conclusion.

The model cannot redefine what this application's approval action means.
Keep this administrative answer separately labeled in the UI.
"""
    if REVIEW_ACTION.search(question or "") and PROOF_REQUEST.search(question or ""):
        return "No. Researcher approval records a review decision; it does not independently verify a scientific relationship."
    return None


def _short_answer(conclusion, question):
    """Check formatting and provenance; never truncate scientific statements."""
    if not isinstance(conclusion, dict):
        return None
    kind = conclusion.get("answer")
    question_type = conclusion.get("question_type")
    text = conclusion.get("text")
    if (
        conclusion.get("supported") is not True
        or conclusion.get("question") != question
        or not isinstance(question_type, str)
        or not isinstance(kind, str)
        or question_type not in {"yes_no", "open"}
        or kind not in ANSWER_PREFIXES
        or (question_type == "yes_no" and kind == "explanatory")
        or (question_type == "open" and kind in {"yes", "no"})
        or not isinstance(text, str)
        or not text.strip()
        or bool(source_ids(text))
    ):
        return None
    body = " ".join(text.split())
    if kind != "explanatory":
        expected_prefix = ANSWER_PREFIXES[kind].strip().rstrip(".").casefold()
        # Normalize only explicit answer labels, preserving negation in prose
        # such as "No increased risk was observed" and all scientific wording.
        while (leading := LEADING_ANSWER.match(body)) is not None:
            if leading[1].casefold() != expected_prefix:
                return None
            body = body[leading.end():]
        if not body:
            return None
    answer = ANSWER_PREFIXES[kind] + body
    if len(answer.split()) > MAX_CONCLUSION_WORDS or len(re.split(r"(?<=[.!?])\s+", answer)) > 2:
        return None
    return answer


def research_conclusion(result):
    """Use a supported direct answer, or explain why one is unavailable."""
    if result.get("needs_clarification") or result.get("out_of_scope"):
        return None
    policy = review_policy_answer(result.get("question", ""))
    if policy:
        return policy
    if result.get("errors") or not result.get("research_summary"):
        return INSUFFICIENT_CONCLUSION

    sources = {item.get("document_id") for item in result.get("retrieved_evidence", [])}
    supported_claims = {
        (claim.get("claim_id"), claim.get("claim_text")): claim
        for check in result.get("validation_results", [])
        if check.get("check") == "claim_evidence_validation"
        for claim in check.get("claims", [])
        if claim.get("evidence_status") == "supported"
    }
    summary = " ".join(result["research_summary"].split())
    has_supported_findings = False
    answers = []
    for finding in result.get("findings", []):
        statement = finding.get("statement", "").strip()
        claim = supported_claims.get((finding.get("claim_id"), statement))
        citations = finding.get("citations") or []
        if (
            finding.get("verification_status") != "model_assessed_supported"
            or not claim
            or not citations
            or set(citations) != set(claim.get("citations", []))
            or not set(citations).issubset(sources)
            or not set(source_ids(statement)).issubset(citations)
            or " ".join(statement.split()) not in summary
        ):
            continue
        has_supported_findings = True
        conclusion = finding.get("conclusion")
        if conclusion != claim.get("conclusion"):
            continue
        answer = _short_answer(conclusion, result.get("question", ""))
        if answer:
            passages = [e.get("content", "") for e in result.get("retrieved_evidence", [])
                        if e.get("document_id") in citations]
            # A model-supported label alone is not sufficient for a precise
            # answer. Yes/no adds an inference to a source quote; qualify it.
            body = conclusion.get("text", "")
            if requires_exact_precision(body) and (
                conclusion.get("answer") in {"yes", "no"} or not precision_is_grounded(body, passages)
            ):
                continue
            answers.append((conclusion["answer"], answer))

    if not has_supported_findings:
        return INSUFFICIENT_CONCLUSION
    kinds = {kind for kind, _ in answers}
    if not answers or len(kinds) > 1:
        return QUALIFIED_CONCLUSION
    # Each answer must already answer the whole question. Do not concatenate
    # separate claims into a new scientific conclusion.
    return min((answer for _, answer in answers), key=lambda answer: len(answer.split()))
