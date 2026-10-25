
from src.agents.evidence_validator import evidence_validator


def main():
    state = {
        "research_summary": (
            "The APOE epsilon 4 allele is present in more than "
            "half of all Alzheimer's disease patients "
            "[pubmed_36348357]."
        ),
        "retrieved_evidence": [
            {
                "document_id": "pubmed_36348357",
                "title": "APOE and Alzheimer's disease",
                "content": (
                    "The APOE gene contributes to Alzheimer's "
                    "disease risk and impacts more than half "
                    "of Alzheimer's disease cases. "
                    "The epsilon 4 allele is associated with "
                    "increased disease risk."
                ),
            }
        ],
        "validation_results": [],
        "agent_log": [],
        "errors": [],
    }

    result = evidence_validator(state)
    claim = result["validation_results"][0]["claims"][0]

    print("\nAPOE CLAIM PRECISION TEST")
    print("=" * 55)
    print("Claim:", claim["claim_text"])
    print("Status:", claim["evidence_status"])
    print("Reason:", claim["reason"])

    assert claim["evidence_status"] in {
        "partially_supported",
        "insufficient_evidence",
    }, "Validator incorrectly accepted an unsupported prevalence claim."

    print("\nSUCCESS: Validator flagged the unsupported inference!")


if __name__ == "__main__":
    main()
