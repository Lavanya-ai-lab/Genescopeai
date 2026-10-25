
"""
Test the GeneScope AI LangGraph workflow.

This test executes the Research Agent through LangGraph
and checks the resulting shared state.
"""

from src.graph.workflow import build_workflow


def main():
    app = build_workflow()

    initial_state = {
        "question": (
            "What does research say about APOE epsilon 4 "
            "and Alzheimer's disease risk?"
        ),
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

    # LangGraph executes the connected nodes.
    final_state = app.invoke(initial_state)

    print("\nGeneScope AI — LangGraph Execution Test")
    print("=" * 50)

    print("Question:", final_state["question"])
    print("Gene:", final_state["gene"])

    evidence = final_state["retrieved_evidence"]
    print("Evidence retrieved:", len(evidence))

    for index, item in enumerate(evidence, start=1):
        print(f"\nEvidence {index}")
        print("Source:", item["document_id"])
        print("Title:", item["title"])
        print("Distance:", round(item["distance"], 4))

    print("\nAgent activity:")
    for entry in final_state["agent_log"]:
        print("-", entry)

    print("\nErrors:", final_state["errors"])

    assert len(evidence) == 3, (
        "Expected three retrieved evidence passages."
    )
    assert not final_state["errors"], (
        "The workflow reported an error."
    )

    print("\nSUCCESS: LangGraph executed the Research Agent!")


if __name__ == "__main__":
    main()
