
"""
Test evidence-grounded summarization for GeneScope AI.

1. Retrieve scientific evidence.
2. Generate a summary using the retrieved evidence.
3. Display the summary, citations, and errors.
"""

from src.agents.research_agent import research_agent
from src.agents.summarize_evidence import summarize_evidence


def main():
    state = {
        "question": (
            "What does scientific research say about APOE epsilon 4 "
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

    print("\nSTEP 1: Retrieving scientific evidence")
    print("=" * 50)

    retrieval_updates = research_agent(state)
    state.update(retrieval_updates)

    print("Evidence retrieved:", len(state["retrieved_evidence"]))

    if state["errors"] or not state["retrieved_evidence"]:
        print("Retrieval failed or returned no evidence.")
        print("Errors:", state["errors"])
        return

    print("\nSTEP 2: Generating evidence-grounded summary")
    print("=" * 50)

    summary_updates = summarize_evidence(state)
    state.update(summary_updates)

    print("\nRESEARCH SUMMARY")
    print("-" * 50)
    print(state["research_summary"])

    print("\nAVAILABLE SOURCE IDS")
    print("-" * 50)
    source_ids = {
        item["document_id"]
        for item in state["retrieved_evidence"]
    }

    for source_id in sorted(source_ids):
        print("-", source_id)

    print("\nAGENT ACTIVITY")
    for entry in state["agent_log"]:
        print("-", entry)

    print("\nERRORS:", state["errors"])

    assert state["research_summary"].strip(), (
        "Expected a non-empty research summary."
    )
    assert not state["errors"], (
        "The test reported an error."
    )

    print("\nSUCCESS: Research summary generated!")


if __name__ == "__main__":
    main()
