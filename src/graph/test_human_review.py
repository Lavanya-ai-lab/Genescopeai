
"""
GeneScope AI - Human Review Pause/Resume Test
"""

from uuid import uuid4

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from src.graph.state import ResearchState
from src.agents.human_review_agent import human_review_agent


def main():
    print("\nGENESCOPE AI - HUMAN REVIEW TEST")
    print("=" * 50)

    # Test the real Human Review Agent in isolation.
    # The complete research workflow will be tested separately.
    builder = StateGraph(ResearchState)
    builder.add_node("human_review_agent", human_review_agent)
    builder.add_edge(START, "human_review_agent")
    builder.add_edge("human_review_agent", END)

    graph = builder.compile(checkpointer=InMemorySaver())

    config = {
        "configurable": {
            "thread_id": str(uuid4())
        }
    }

    initial_state = {
        "relationships": [
            {
                "gene": "APOE",
                "allele": "APOE ε4",
                "disease": "Alzheimer's disease",
                "relationship_type": "increased_risk",
                "relationship_status": "rule_extracted_candidate",
                "evidence_status": "model_assessed_supported",
                "source_claim_id": "test_claim_1",
                "citations": ["33340485"],
            }
        ],
        "agent_log": [],
        "errors": [],
    }

    # First execution should pause.
    first_result = graph.invoke(initial_state, config=config)

    assert "__interrupt__" in first_result, (
        "Expected the workflow to pause for human review."
    )

    print("\nPASSED: Workflow paused for human review.")

    # Resume with an explicit approval.
    final_result = graph.invoke(
        Command(
            resume={
                "approved": True,
                "feedback": "Reviewed and approved for demonstration.",
            }
        ),
        config=config,
    )

    assert final_result["review_status"] == "approved"
    assert len(final_result["approved_relationships"]) == 1

    print("PASSED: Workflow resumed after approval.")
    print("PASSED: Approved relationship was recorded.")


    # Test rejection using a fresh workflow thread.
    rejection_config = {
        "configurable": {
            "thread_id": str(uuid4())
        }
    }

    rejection_first = graph.invoke(
        initial_state,
        config=rejection_config,
    )

    assert "__interrupt__" in rejection_first, (
        "Expected the rejection test to pause for review."
    )

    rejected_result = graph.invoke(
        Command(
            resume={
                "approved": False,
                "feedback": "Evidence needs further review.",
            }
        ),
        config=rejection_config,
    )

    assert rejected_result["review_status"] == "rejected"
    assert rejected_result["approved_relationships"] == []
    assert rejected_result["review_feedback"] == (
        "Evidence needs further review."
    )

    print("PASSED: Workflow resumed after rejection.")
    print("PASSED: Rejected relationships were not approved.")

    print("\nSUCCESS: Human-in-the-loop approval works!")


if __name__ == "__main__":
    main()
