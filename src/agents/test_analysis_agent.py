
"""
GeneScope AI - Analysis Agent Test.

Tests:
1. Supported findings become relationship candidates.
2. Empty findings are handled safely.
"""

from src.agents.analysis_agent import analysis_agent


def main():
    print("\nTEST 1: ANALYZE SUPPORTED FINDINGS")
    print("=" * 55)

    state = {
        "gene": "APOE",
        "findings": [
            {
                "claim_id": "claim_1",
                "statement": (
                    "APOE epsilon 4 is associated with increased "
                    "Alzheimer's disease risk."
                ),
                "citations": ["pubmed_33340485"],
                "verification_status": "model_assessed_supported",
            },
            {
                "claim_id": "claim_2",
                "statement": (
                    "APOE epsilon 2 is associated with reduced "
                    "Alzheimer's disease risk."
                ),
                "citations": ["pubmed_36348357"],
                "verification_status": "model_assessed_supported",
            },
        ],
        "agent_log": [],
    }

    result = analysis_agent(state)

    relationships = result["research_hypotheses"]

    for relationship in relationships:
        print("\nGene:", relationship["gene"])
        print("Statement:", relationship["statement"])
        print("Citations:", relationship["citations"])
        print("Status:", relationship["relationship_status"])

    assert len(relationships) == 2
    assert all(item["gene"] == "APOE" for item in relationships)
    assert all(
        item["relationship_status"] == "pending_structured_analysis"
        for item in relationships
    )

    print("\nTEST 2: EMPTY FINDINGS")
    print("=" * 55)

    empty_result = analysis_agent({
        "gene": "APOE",
        "findings": [],
        "agent_log": [],
    })

    print("Relationship candidates:",
          len(empty_result["research_hypotheses"]))

    assert empty_result["research_hypotheses"] == []

    print("\nSUCCESS: Both Analysis Agent tests passed!")


if __name__ == "__main__":
    main()
