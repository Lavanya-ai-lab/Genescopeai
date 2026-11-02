
"""
Validation Agent for GeneScope AI.

First version:
Check whether citations in the research summary
refer to retrieved scientific sources.
"""

from src.graph.state import ResearchState
from src.agents.evidence_rules import source_ids


def validation_agent(state: ResearchState) -> dict:
    """Check citations against retrieved evidence."""

    summary = state.get("research_summary", "")
    evidence = state.get("retrieved_evidence", [])

    available_sources = {
        item["document_id"]
        for item in evidence
        if item.get("document_id")
    }

    cited_sources = set(source_ids(summary))

    invalid_citations = sorted(
        cited_sources - available_sources
    )

    valid_citations = sorted(
        cited_sources & available_sources
    )

    results = [
        {
            "check": "citation_source_validation",
            "passed": bool(cited_sources) and not invalid_citations,
            "available_sources": sorted(available_sources),
            "valid_citations": valid_citations,
            "invalid_citations": invalid_citations,
            "citation_count": len(cited_sources),
            "message": (
                "All cited indexed sources were retrieved."
                if cited_sources and not invalid_citations
                else "Missing citations or unknown indexed sources detected."
            ),
        }
    ]

    return {
        "validation_results": results,
        "agent_log": state.get("agent_log", []) + [
            "Validation Agent completed citation-source checks."
        ],
    }
