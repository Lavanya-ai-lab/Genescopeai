
"""
Extract individual scientific claims from a research summary.

This is an initial rule-based approach.
It identifies sentences and their indexed PubMed or NCBI citations.
"""

import re
from src.agents.evidence_rules import source_ids, SOURCE_ID


def extract_claims(summary: str) -> list[dict]:
    """Extract sentences and associated indexed source IDs."""

    if not summary or not summary.strip():
        return []

    # Split on sentence-ending punctuation followed by whitespace.
    sentences = re.split(r"(?<=[.!?])\s+", summary.strip())

    claims = []

    for index, sentence in enumerate(sentences, start=1):
        sentence = sentence.strip()

        if not sentence or not any(char.isalpha() for char in SOURCE_ID.sub("", sentence)):
            continue

        citations = source_ids(sentence)

        claims.append(
            {
                "claim_id": f"claim_{index}",
                "claim_text": sentence,
                "citations": citations,
                "has_citation": bool(citations),
                "evidence_status": "not_yet_checked",
            }
        )

    return claims
