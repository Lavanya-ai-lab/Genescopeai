
"""
Test scientific claim extraction for GeneScope AI.
"""

from src.agents.extract_claims import extract_claims


def main():
    summary = (
        "The APOE epsilon 4 allele increases Alzheimer's disease risk "
        "[pubmed_33340485]. "
        "Not all APOE epsilon 4 carriers develop Alzheimer's disease "
        "[pubmed_33576571]. "
        "APOE variants affect more than half of Alzheimer's cases "
        "[pubmed_36348357]. "
        "More research is needed to understand genetic modifiers."
    )

    claims = extract_claims(summary)

    print("\nGENESCOPE AI - CLAIM EXTRACTION")
    print("=" * 55)

    for claim in claims:
        print(f"\nClaim ID: {claim['claim_id']}")
        print(f"Statement: {claim['claim_text']}")
        print(f"Citations: {claim['citations']}")
        print(f"Has citation: {claim['has_citation']}")
        print(f"Evidence status: {claim['evidence_status']}")

    assert len(claims) == 4
    assert claims[0]["citations"] == ["pubmed_33340485"]
    assert claims[1]["citations"] == ["pubmed_33576571"]
    assert claims[2]["citations"] == ["pubmed_36348357"]
    assert claims[3]["has_citation"] is False

    print("\nSUCCESS: All four claims extracted correctly!")


if __name__ == "__main__":
    main()
