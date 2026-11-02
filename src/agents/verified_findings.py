
"""
GeneScope AI - Verified Findings Extractor.

Separates claims marked supported from claims
requiring further review.

These are model-assessed findings, not independently
verified scientific facts.
"""

from src.graph.state import ResearchState


def verified_findings_agent(state: ResearchState) -> dict:
    validation_results = state.get("validation_results", [])

    evidence_check = next(
        (
            check
            for check in validation_results
            if check.get("check") == "claim_evidence_validation"
        ),
        None,
    )

    if evidence_check is None:
        return {
            "findings": [],
            "agent_log": state.get("agent_log", []) + [
                "Verified Findings skipped: no evidence assessment."
            ],
        }

    findings = []

    for claim in evidence_check.get("claims", []):
        if claim.get("evidence_status") == "supported":
            findings.append({
                "claim_id": claim["claim_id"],
                "statement": claim["claim_text"],
                "citations": claim["citations"],
                "verification_status": "model_assessed_supported",
                **({"presentation_type": claim["presentation_type"]} if claim.get("presentation_type") else {}),
                **({"conclusion": claim["conclusion"]} if "conclusion" in claim else {}),
            })

    return {
        "findings": findings,
        "agent_log": state.get("agent_log", []) + [
            f"Verified Findings extracted {len(findings)} supported claims."
        ],
    }
