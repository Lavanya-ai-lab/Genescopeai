
"""
Test the GeneScope AI Research Agent.
"""

from src.agents.research_agent import research_agent


def main():
    state = {
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

    updates = research_agent(state)

    print("Research Agent test")
    print("=" * 50)

    evidence = updates.get("retrieved_evidence", [])

    print(f"Evidence retrieved: {len(evidence)}")

    for index, item in enumerate(evidence, start=1):
        print(f"\nResult {index}")
        print("Source:", item["document_id"])
        print("Title:", item["title"])
        print("Chunk:", item["chunk_id"])
        print("Distance:", round(item["distance"], 4))
        print("Preview:", item["content"][:200])

    print("\nAgent log:", updates.get("agent_log", []))
    print("Errors:", updates.get("errors", []))


if __name__ == "__main__":
    main()
