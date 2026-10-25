
"""
GeneScope AI - Relationship Extraction Tests.
"""

from src.agents.analysis_agent import extract_relationships


def main():
    print("\nGENESCOPE AI - RELATIONSHIP EXTRACTION TEST")
    print("=" * 55)

    test_cases = [
        {
            "name": "APOE epsilon 4 - increased risk",
            "statement": (
                "APOE epsilon 4 increases Alzheimer's disease risk."
            ),
            "expected": [("APOE ε4", "increased_risk")],
        },
        {
            "name": "APOE epsilon 2 - reduced risk",
            "statement": (
                "APOE epsilon 2 is protective against Alzheimer's disease."
            ),
            "expected": [("APOE ε2", "reduced_risk")],
        },
        {
            "name": "Both alleles in one sentence",
            "statement": (
                "APOE epsilon 4 increases Alzheimer's disease risk, "
                "while APOE epsilon 2 is protective."
            ),
            "expected": [
                ("APOE ε4", "increased_risk"),
                ("APOE ε2", "reduced_risk"),
            ],
        },
        {
            "name": "Ambiguous relationship",
            "statement": (
                "APOE epsilon 4 and epsilon 2 influence "
                "Alzheimer's disease risk."
            ),
            "expected": [],
        },
    ]

    for case in test_cases:
        print("\nTEST:", case["name"])

        result = extract_relationships(case["statement"])

        actual = [
            (item["allele"], item["relationship_type"])
            for item in result
        ]

        print("Extracted:", actual)
        print("Expected:", case["expected"])

        assert actual == case["expected"], (
            f"Test failed: {case['name']}"
        )

        print("PASSED")

    print("\nSUCCESS: All relationship extraction tests passed!")


if __name__ == "__main__":
    main()
