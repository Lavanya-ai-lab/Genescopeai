
"""
Validation Agent for GeneScope AI.

First version:
Check whether citations in the research summary
refer to retrieved scientific sources.
"""

import re

from src.graph.state import ResearchState


def validation_agent(state: ResearchState) -> dict:
    """Check citations against retrieved evidence."""

    summary = state.get("research_summary", "")
    evidence = state.get("retrieved_evidence", [])

    available_sources = {
        item["document_id"]
        for item in evidence
        if item.get("document_id")
    }

    # Recognize PubMed citations, including grouped citations.
    cited_sources = set(
        re.findall(r"pubmed_\d+", summary, flags=re.IGNORECASE)
    )

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
                "All cited PubMed sources were retrieved."
                if cited_sources and not invalid_citations
                else "Missing citations or unknown PubMed sources detected."
            ),
        }
    ]

    return {
        "validation_results": results,
        "agent_log": state.get("agent_log", []) + [
            "Validation Agent completed citation-source checks."
        ],
    }
