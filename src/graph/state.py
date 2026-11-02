
"""
Shared state for GeneScope AI's multi-agent workflow.

Each agent reads the research state and returns
updates to the fields it is responsible for.
"""

from typing import Any, TypedDict


class ResearchState(TypedDict):
    # Researcher's original request
    question: str

    # Gene being investigated
    gene: str

    # Clarification before research proceeds
    needs_clarification: bool
    clarification_question: str

    # Clearly unrelated to the current APOE/Alzheimer's collection
    out_of_scope: bool
    scope_message: str

    # Retrieved scientific passages with citations
    retrieved_evidence: list[dict[str, Any]]

    # Evidence-grounded research summary
    research_summary: str

    # Original generation retained for traceability, not a supported answer.
    research_summary_draft: str

    # Findings supported by scientific evidence
    findings: list[dict[str, Any]]

    relationships: list[dict[str, Any]]

    review_status: str
    review_feedback: str
    approved_relationships: list[dict[str, Any]]

    # Possible explanations or future research ideas
    # These must not be presented as established findings.
    research_hypotheses: list[dict[str, Any]]

    # Evidence review and uncertainty checks
    validation_results: list[dict[str, Any]]

    # Nodes and relationships for visualization
    knowledge_graph: dict[str, Any]

    # Agent activity and error tracking
    agent_log: list[str]
    errors: list[str]
