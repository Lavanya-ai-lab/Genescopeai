
"""
Test GeneScope AI's Evidence Validator.

Uses controlled scientific evidence to test:
1. Supported claims
2. Contradicted claims
3. Missing citations
"""

from src.agents.evidence_validator import evidence_validator


def make_state(summary: str) -> dict:
    return {
        "question": "How does APOE epsilon 4 affect Alzheimer's risk?",
        "gene": "APOE",
        "research_summary": summary,
        "retrieved_evidence": [
            {
                "document_id": "pubmed_33340485",
                "title": "APOE and Alzheimer's disease",
                "content": (
                    "APOE epsilon 4 is associated with increased "
                    "risk of late-onset Alzheimer's disease. "
                    "However, carrying APOE epsilon 4 does not "
                    "guarantee that a person will develop the disease."
                ),
            }
        ],
        "validation_results": [],
        "agent_log": [],
        "errors": [],
    }


def main():
    summary = (
        "APOE epsilon 4 increases the risk of Alzheimer's disease "
        "[pubmed_33340485]. "
        "Every person carrying APOE epsilon 4 will develop "
        "Alzheimer's disease [pubmed_33340485]. "
        "APOE epsilon 4 has been proven to cure Alzheimer's disease."
    )

    result = evidence_validator(make_state(summary))

    validation = result["validation_results"][0]
    claims = validation["claims"]

    print("\nGENESCOPE AI - EVIDENCE VALIDATION")
    print("=" * 60)

    for claim in claims:
        print(f"\n{claim['claim_id']}")
        print("Claim:", claim["claim_text"])
        print("Status:", claim["evidence_status"])
        print("Reason:", claim["reason"])

    assert len(claims) == 3

    assert claims[0]["evidence_status"] == "supported", (
        "The directly supported claim was not recognized."
    )

    assert claims[1]["evidence_status"] == "unsupported", (
        "The contradicted claim was not rejected."
    )

    assert claims[2]["evidence_status"] == "insufficient_evidence", (
        "The uncited claim was not flagged."
    )

    assert validation["passed"] is False

    print("\nSUCCESS: All three evidence-validation tests passed!")


if __name__ == "__main__":
    main()
