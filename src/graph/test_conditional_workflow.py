
"""
Test both branches of the GeneScope AI workflow.

Scenario 1: Clear question -> retrieve evidence.
Scenario 2: Ambiguous question -> ask for clarification.
"""

from src.graph.workflow import build_workflow


def make_initial_state(question: str) -> dict:
    return {
        "question": question,
        "gene": "APOE",
        "needs_clarification": False,
        "clarification_question": "",
        "retrieved_evidence": [],
        "research_summary": "",
        "findings": [],
        "research_hypotheses": [],
        "validation_results": [],
        "knowledge_graph": {"nodes": [], "edges": []},
        "agent_log": [],
        "errors": [],
    }


def main():
    app = build_workflow()

    # Test 1: Clear research question
    print("\nTEST 1: CLEAR QUESTION")
    print("=" * 50)

    clear_state = app.invoke(
        make_initial_state(
            "What does research say about APOE epsilon 4 "
            "and Alzheimer's disease risk?"
        )
    )

    print("Needs clarification:", clear_state["needs_clarification"])
    print("Evidence retrieved:", len(clear_state["retrieved_evidence"]))
    print("Agent log:", clear_state["agent_log"])
    print("Errors:", clear_state["errors"])

    assert clear_state["needs_clarification"] is False
    assert len(clear_state["retrieved_evidence"]) == 3
    assert clear_state["errors"] == []

    # Test 2: Ambiguous research question
    print("\nTEST 2: AMBIGUOUS QUESTION")
    print("=" * 50)

    vague_state = app.invoke(
        make_initial_state("What should we investigate next?")
    )

    print("Needs clarification:", vague_state["needs_clarification"])
    print("Clarification question:", vague_state["clarification_question"])
    print("Evidence retrieved:", len(vague_state["retrieved_evidence"]))
    print("Agent log:", vague_state["agent_log"])
    print("Errors:", vague_state["errors"])

    assert vague_state["needs_clarification"] is True
    assert vague_state["clarification_question"]
    assert len(vague_state["retrieved_evidence"]) == 0
    assert vague_state["errors"] == []

    print("\nSUCCESS: Both workflow branches passed!")


if __name__ == "__main__":
    main()
