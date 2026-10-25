
"""
Test the complete GeneScope AI research workflow.

Tests:
1. Clear question -> retrieval -> summarization.
2. Vague question -> clarification -> stop.
"""

from src.graph.workflow import build_workflow


def make_initial_state(question: str) -> dict:
    return {
        "question": question,
        "gene": "APOE",
        "needs_clarification": False,
        "clarification_question": "",
        "retrieved_evidence": [],
        "research_summary": "",
        "findings": [],
        "research_hypotheses": [],
        "validation_results": [],
        "knowledge_graph": {"nodes": [], "edges": []},
        "agent_log": [],
        "errors": [],
    }


def main():
    app = build_workflow()

    print("\nTEST 1: COMPLETE RESEARCH WORKFLOW")
    print("=" * 55)

    result = app.invoke(
        make_initial_state(
            "What does research say about APOE epsilon 4 "
            "and Alzheimer's disease risk?"
        )
    )

    print("Evidence retrieved:", len(result["retrieved_evidence"]))
    print("\nRESEARCH SUMMARY:")
    print(result["research_summary"])

    print("\nAGENT ACTIVITY:")
    for entry in result["agent_log"]:
        print("-", entry)


    
    print("\nVALIDATION RESULTS:")

    for check in result["validation_results"]:
        print("Check:", check["check"])
        print("Passed:", check["passed"])

        if check["check"] == "citation_source_validation":
            print("Valid citations:", check["valid_citations"])
            print("Invalid citations:", check["invalid_citations"])
            print("Message:", check["message"])


    assert result["validation_results"], (
        "Validation Agent did not produce results."
    )
    assert result["validation_results"][0]["passed"], (
        "Citation validation failed."
    )


    print("\nCLAIM-LEVEL EVIDENCE VALIDATION:")
    print("=" * 55)

    evidence_checks = [
        check
        for check in result["validation_results"]
        if check["check"] == "claim_evidence_validation"
    ]

    assert len(evidence_checks) == 1, (
        "Expected exactly one claim-level validation result."
    )

    evidence_check = evidence_checks[0]

    for claim in evidence_check["claims"]:
        print(f"\n{claim['claim_id']}")
        print("Claim:", claim["claim_text"])
        print("Status:", claim["evidence_status"])
        print("Reason:", claim["reason"])

    print("\nAll claims supported:", evidence_check["passed"])

    assert evidence_check["claims"], (
        "Evidence Validator did not assess any claims."
    )


    print("\nMODEL-ASSESSED SUPPORTED FINDINGS:")
    print("=" * 55)

    findings = result["findings"]

    for finding in findings:
        print("\nFinding:", finding["statement"])
        print("Citations:", finding["citations"])
        print("Status:", finding["verification_status"])

    print("\nTotal supported findings:", len(findings))

    evidence_claims = evidence_check["claims"]

    supported_claims = [
        claim for claim in evidence_claims
        if claim["evidence_status"] == "supported"
    ]

    assert len(findings) == len(supported_claims), (
        "Findings count does not match supported claims."
    )

    assert all(
        finding["verification_status"] == "model_assessed_supported"
        for finding in findings
    ), "Unexpected finding verification status."



    print("\nERRORS:", result["errors"])

    assert result["needs_clarification"] is False
    assert len(result["retrieved_evidence"]) == 3
    assert result["research_summary"].strip()
    assert not result["errors"]

    print("\nTEST 2: AMBIGUOUS RESEARCH QUESTION")
    print("=" * 55)

    vague_result = app.invoke(
        make_initial_state(
            "What should we investigate next?"
        )
    )

    print("Needs clarification:", vague_result["needs_clarification"])
    print("Clarification question:", vague_result["clarification_question"])
    print("Evidence retrieved:", len(vague_result["retrieved_evidence"]))
    print("Research summary:", repr(vague_result["research_summary"]))
    print("Errors:", vague_result["errors"])

    assert vague_result["needs_clarification"] is True
    assert vague_result["clarification_question"]
    assert len(vague_result["retrieved_evidence"]) == 0
    assert not vague_result["research_summary"]
    assert not vague_result["errors"]

    print("\nSUCCESS: Both complete workflow tests passed!")


if __name__ == "__main__":
    main()
