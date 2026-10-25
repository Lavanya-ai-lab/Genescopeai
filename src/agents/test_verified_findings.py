
"""
Test GeneScope AI's Verified Findings Agent.

Ensure only claims classified as supported
are included in the findings list.
"""

from src.agents.verified_findings import verified_findings_agent


def main():
    state = {
        "validation_results": [
            {
                "check": "claim_evidence_validation",
                "passed": False,
                "claims": [
                    {
                        "claim_id": "claim_1",
                        "claim_text": (
                            "APOE epsilon 4 increases "
                            "Alzheimer's disease risk."
                        ),
                        "citations": ["pubmed_33340485"],
                        "evidence_status": "supported",
                        "reason": "Directly supported by the passage.",
                    },
                    {
                        "claim_id": "claim_2",
                        "claim_text": (
                            "APOE epsilon 4 occurs in more than "
                            "half of Alzheimer's patients."
                        ),
                        "citations": ["pubmed_36348357"],
                        "evidence_status": "partially_supported",
                        "reason": "Allele prevalence was not established.",
                    },
                    {
                        "claim_id": "claim_3",
                        "claim_text": (
                            "Every APOE epsilon 4 carrier "
                            "develops Alzheimer's disease."
                        ),
                        "citations": ["pubmed_33340485"],
                        "evidence_status": "unsupported",
                        "reason": "The evidence contradicts this statement.",
                    },
                ],
            }
        ],
        "agent_log": [],
        "findings": [],
    }

    result = verified_findings_agent(state)

    print("\nGENESCOPE AI - VERIFIED FINDINGS TEST")
    print("=" * 55)

    for finding in result["findings"]:
        print("Finding:", finding["statement"])
        print("Status:", finding["verification_status"])
        print("Citations:", finding["citations"])

    assert len(result["findings"]) == 1
    assert result["findings"][0]["claim_id"] == "claim_1"
    assert (
        result["findings"][0]["verification_status"]
        == "model_assessed_supported"
    )

    print("\nSUCCESS: Only supported claims were included!")


if __name__ == "__main__":
    main()
