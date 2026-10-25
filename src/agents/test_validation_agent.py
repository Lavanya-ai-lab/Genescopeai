
"""
Test GeneScope AI's citation Validation Agent.

Three scenarios:
1. Valid citation
2. Fabricated citation
3. Missing citation
"""

from src.agents.validation_agent import validation_agent


def make_state(summary: str) -> dict:
    return {
        "question": "What is the relationship between APOE and Alzheimer's disease?",
        "gene": "APOE",
        "needs_clarification": False,
        "clarification_question": "",
        "retrieved_evidence": [
            {
                "document_id": "pubmed_33340485",
                "title": "APOE and Alzheimer's disease",
                "content": "APOE epsilon 4 is a genetic risk factor.",
            },
            {
                "document_id": "pubmed_33576571",
                "title": "APOE genetic modifiers",
                "content": "Genetic modifiers may influence APOE-related risk.",
            },
        ],
        "research_summary": summary,
        "findings": [],
        "research_hypotheses": [],
        "validation_results": [],
        "knowledge_graph": {"nodes": [], "edges": []},
        "agent_log": [],
        "errors": [],
    }


def run_test(name: str, summary: str, expected_pass: bool):
    print(f"\n{name}")
    print("=" * 50)

    state = make_state(summary)
    updates = validation_agent(state)

    result = updates["validation_results"][0]

    print("Passed:", result["passed"])
    print("Valid citations:", result["valid_citations"])
    print("Invalid citations:", result["invalid_citations"])
    print("Message:", result["message"])

    assert result["passed"] == expected_pass, (
        f"{name} produced an unexpected result."
    )


def main():
    run_test(
        "TEST 1: VALID CITATION",
        "APOE epsilon 4 increases genetic risk [pubmed_33340485].",
        True,
    )

    run_test(
        "TEST 2: FABRICATED CITATION",
        "APOE epsilon 4 increases genetic risk [pubmed_99999999].",
        False,
    )

    run_test(
        "TEST 3: MISSING CITATION",
        "APOE epsilon 4 increases genetic risk.",
        False,
    )

    run_test(
        "TEST 4: MIXED VALID AND FABRICATED CITATIONS",
        (
            "APOE epsilon 4 increases genetic risk "
            "[pubmed_33340485, pubmed_99999999]."
        ),
        False,
    )


    print("\nSUCCESS: All four citation tests passed!")


if __name__ == "__main__":
    main()
