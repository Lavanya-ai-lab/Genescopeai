
"""
GeneScope AI - Analysis Agent.

Extracts APOE allele-disease risk relationships from
model-assessed supported scientific findings.

Rule-based extraction; no additional LLM calls.
"""

import re

from src.graph.state import ResearchState


ALLELE_PATTERNS = {
    "APOE ε4": r"(?:epsilon|ε)\s*4\b",
    "APOE ε2": r"(?:epsilon|ε)\s*2\b",
}


RISK_PATTERNS = {
    "increased_risk": (
        r"\b(?:increas\w*|higher|elevated)\b"
        r"(?:\s+[\w'-]+){0,5}\s+risk\b"
        r"|\brisk factor\b"
    ),
    "reduced_risk": (
        r"\b(?:reduc\w*|lower|decreas\w*)\b"
        r"(?:\s+[\w'-]+){0,5}\s+risk\b"
        r"|\bprotective\b"
    ),
}



def extract_relationships(statement: str) -> list[dict]:
    """Extract risk relationships from simple evidence statements."""

    text = statement.lower()

    if "alzheimer" not in text:
        return []

    # Split contrasting clauses so each allele can be
    # evaluated against its own risk description.
    clauses = re.split(r"\bwhile\b|\bwhereas\b|;", text)

    extracted = []

    for clause in clauses:
        matched_alleles = [
            allele
            for allele, pattern in ALLELE_PATTERNS.items()
            if re.search(pattern, clause)
        ]

        matched_risks = [
            risk_type
            for risk_type, pattern in RISK_PATTERNS.items()
            if re.search(pattern, clause)
        ]

        # Only extract unambiguous allele-risk pairs.
        if len(matched_alleles) != 1 or len(matched_risks) != 1:
            continue

        extracted.append({
            "gene": "APOE",
            "allele": matched_alleles[0],
            "disease": "Alzheimer's disease",
            "relationship_type": matched_risks[0],
        })

    return extracted


def analysis_agent(state: ResearchState) -> dict:
    """Prepare structured relationships from supported findings."""

    findings = state.get("findings", [])
    relationships = []

    for finding in findings:
        if finding.get("verification_status") != "model_assessed_supported":
            continue

        statement = finding.get("statement", "")

        for relationship in extract_relationships(statement):
            relationships.append({
                **relationship,
                "source_claim_id": finding["claim_id"],
                "statement": statement,
                "citations": finding.get("citations", []),
                "evidence_status": "model_assessed_supported",
                "relationship_status": "rule_extracted_candidate",
            })

    return {
        "relationships": relationships,
        "agent_log": state.get("agent_log", []) + [
            f"Analysis Agent extracted {len(relationships)} "
            "candidate relationships."
        ],
    }
