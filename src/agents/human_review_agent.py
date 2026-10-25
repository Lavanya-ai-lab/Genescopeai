
"""
GeneScope AI - Human Review Agent.

Pauses LangGraph execution so a researcher can
approve or reject proposed scientific relationships.
"""

from langgraph.types import interrupt

from src.graph.state import ResearchState


def human_review_agent(state: ResearchState) -> dict:
    """Request human approval before finalizing relationships."""

    relationships = state.get("relationships", [])

    if not relationships:
        return {
            "review_status": "not_required",
            "review_feedback": "No relationships available for review.",
            "approved_relationships": [],
            "agent_log": state.get("agent_log", []) + [
                "Human Review skipped: no relationships."
            ],
        }

    decision = interrupt({
        "type": "scientific_relationship_review",
        "message": (
            "Please review the proposed scientific relationships. "
            "Approve or reject before finalizing."
        ),
        "relationships": relationships,
    })

    if not isinstance(decision, dict):
        decision = {}

    approved = decision.get("approved") is True
    feedback = str(decision.get("feedback", ""))

    return {
        "review_status": "approved" if approved else "rejected",
        "review_feedback": feedback,
        "approved_relationships": relationships if approved else [],
        "agent_log": state.get("agent_log", []) + [
            "Human Review completed: "
            + ("approved." if approved else "rejected.")
        ],
    }
