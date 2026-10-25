
"""
GeneScope AI LangGraph workflow.

Clarification -> Research -> Summarization -> Validation
"""

from langgraph.graph import StateGraph, START, END

from src.graph.state import ResearchState
from src.agents.clarification_agent import clarification_agent
from src.agents.research_agent import research_agent
from src.agents.summarize_evidence import summarize_evidence
from src.agents.validation_agent import validation_agent
from src.agents.evidence_validator import evidence_validator
from src.agents.verified_findings import verified_findings_agent
from src.agents.analysis_agent import analysis_agent
from langgraph.checkpoint.memory import InMemorySaver
from src.agents.human_review_agent import human_review_agent


def route_after_clarification(state: ResearchState) -> str:
    """Stop before retrieval for vague or clearly out-of-scope questions."""
    if state.get("needs_clarification") or state.get("out_of_scope"):
        return "end"

    return "research"


def route_after_research(state: ResearchState) -> str:
    """Only summarize when retrieval succeeds."""
    if state.get("errors") or not state.get("retrieved_evidence"):
        return "end"

    return "summarize"


def route_after_summarization(state: ResearchState) -> str:
    """Only validate when a summary was generated."""
    if state.get("errors") or not state.get("research_summary"):
        return "end"

    return "validate"


def build_workflow():
    """Build and compile the GeneScope AI workflow."""

    workflow = StateGraph(ResearchState)

    workflow.add_node("clarification_agent", clarification_agent)
    workflow.add_node("research_agent", research_agent)
    workflow.add_node("summarize_evidence", summarize_evidence)
    workflow.add_node("validation_agent", validation_agent)
    workflow.add_node("evidence_validator", evidence_validator)
    workflow.add_node("verified_findings_agent", verified_findings_agent)
    workflow.add_node("analysis_agent", analysis_agent)
    workflow.add_node("human_review_agent", human_review_agent)

    workflow.add_edge(START, "clarification_agent")

    workflow.add_conditional_edges(
        "clarification_agent",
        route_after_clarification,
        {
            "research": "research_agent",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "research_agent",
        route_after_research,
        {
            "summarize": "summarize_evidence",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "summarize_evidence",
        route_after_summarization,
        {
            "validate": "validation_agent",
            "end": END,
        },
    )

    workflow.add_edge("validation_agent", "evidence_validator")
    workflow.add_edge("evidence_validator", "verified_findings_agent")
    workflow.add_edge("verified_findings_agent", "analysis_agent")
    workflow.add_edge("analysis_agent", "human_review_agent")
    workflow.add_edge("human_review_agent", END)

    checkpointer = InMemorySaver()
    return workflow.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    app = build_workflow()
    print("GeneScope AI workflow compiled successfully!")
    print(app.get_graph().draw_ascii())
