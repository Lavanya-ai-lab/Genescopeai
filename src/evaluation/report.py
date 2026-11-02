"""Reports computed exclusively from saved real experiment artifacts."""

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

from src.evaluation.dataset import load_cases


def build_report(directory):
    directory = Path(directory)
    metadata = json.loads((directory / "experiment.json").read_text())
    cases = {c["id"]: c for c in load_cases()}
    records = [json.loads((directory / f"{id}.json").read_text())
               for id in cases if (directory / f"{id}.json").exists()]
    metrics = {}
    for name in ("grounded_correctness", "citation_validity", "uncertainty_handling", "workflow_completion"):
        counts = Counter(r["metrics"][name]["status"] for r in records)
        graded = counts["pass"] + counts["fail"]
        metrics[name] = {"pass": counts["pass"], "fail": counts["fail"],
                         "ungraded": counts["ungraded"], "not_applicable": counts["not_applicable"],
                         "graded": graded, "pass_fraction": counts["pass"] / graded if graded else None}
    failures = {}
    for record in records:
        case_id = record["case_id"]
        labels = set(record["metrics"]["workflow_completion"].get("failures", []))
        for name, score in record["metrics"].items():
            if score["status"] == "fail":
                labels.add(score.get("failure_type", name))
        for label in labels:
            failures.setdefault(label, []).append(case_id)
    ranked = sorted(({"failure": k, "case_count": len(v), "case_ids": v}
                     for k, v in failures.items()), key=lambda r: (-r["case_count"], r["failure"]))
    seconds = sorted(r["active_seconds"] for r in records)
    # Nearest-rank p95, explicitly not a service-level guarantee.
    import math
    latency = {"count": len(seconds), "median_seconds": statistics.median(seconds) if seconds else None,
               "p95_seconds": seconds[math.ceil(.95 * len(seconds)) - 1] if seconds else None,
               "total_active_seconds": sum(seconds), "definition": "active wall time; excludes human wait and evaluator calls"}
    routing = [r["case_id"] for r in records
               if "incorrect_route" in r["metrics"]["workflow_completion"].get("failures", [])]
    unsupported = [r["case_id"] for r in records
                   if r["metrics"]["grounded_correctness"].get("failure_type") == "unsupported_claim"
                   and r["metrics"]["citation_validity"].get("failure_type") == "citation_not_entailed"]
    recognition = []
    import re
    for record in records:
        state = record.get("state", {})
        retrieved = {e.get("document_id") for e in state.get("retrieved_evidence", [])}
        for check in state.get("validation_results", []):
            for claim in check.get("claims", []):
                known_gene_cites = set(re.findall(r"ncbi_gene_\d+", claim.get("claim_text", ""))) & retrieved
                if known_gene_cites - set(claim.get("citations", [])):
                    recognition.append(record["case_id"])
                    break
            if record["case_id"] in recognition:
                break
    investigations = [{"category": name, "case_ids": ids, "case_count": len(ids), "basis": basis}
                      for name, ids, basis in (
                          ("pre_retrieval_gating", routing, "Deterministic expected-route versus actual node events"),
                          ("unsupported_visible_precision", unsupported, "Separate grounding and citation-entailment judgments agree; human review pending"),
                          ("ncbi_citation_recognition", recognition, "Known retrieved NCBI IDs in claim text are missing from the app's extracted citation list"))
                      if ids]
    return {"metadata": metadata, "completed": len(records), "expected": 40,
            "missing_case_ids": sorted(set(cases) - {r["case_id"] for r in records}),
            "metrics": metrics, "latency": latency,
            "top_failures": ranked[:3], "all_failures": ranked,
            "priority_investigations": sorted(investigations, key=lambda r: (-r["case_count"], r["category"])),
            "lanes": {lane: [r["case_id"] for r in records
                               if bool(cases[r["case_id"]].get("fixture")) == injected]
                      for lane, injected in (("normal", False), ("injected_fault", True))},
            "cases": [{"id": r["case_id"], "category": cases[r["case_id"]]["category"],
                       "fixture": r.get("fixture"), "metrics": r["metrics"],
                       "active_seconds": r["active_seconds"], "awaiting_review": r["awaiting_review"],
                       "trace_ids": r["trace_ids"]} for r in records]}


def regrade_cached(directory, destination):
    """Apply a tested mechanical grader correction without rerunning research.

All original model judgments are reused, including failures. No selective model
retries, paid requests, or human-review labels are introduced. The source run is
never modified; its original grades and source snapshot remain intact.
"""
    from src.evaluation.evaluators import VERSION, evaluate
    from src.evaluation.dataset import CORPUS, verify_frozen
    directory, destination = Path(directory), Path(destination)
    cases = load_cases()
    manifest = verify_frozen(check_index=False)
    metadata = json.loads((directory / "experiment.json").read_text())
    if metadata["dataset_sha256"] != manifest["cases_sha256"]:
        raise ValueError("Cannot regrade different inputs.")
    if any(not (directory / f"{c['id']}.json").exists() for c in cases):
        raise ValueError("Regrading requires all 40 saved outputs.")
    destination.mkdir(parents=True, exist_ok=False)
    from src.evaluation.dataset import ROOT, digest
    reviews = [json.loads((directory / f"{c['id']}.json").read_text())["human_review"] for c in cases]
    metadata = {**metadata, "experiment": destination.name, "raw_experiment": directory.name,
                "evaluator_version": VERSION,
                "evaluator_source_sha256": digest((ROOT / "src/evaluation/evaluators.py").read_text()),
                "review_annotations_sha256": digest(reviews),
                "grading_note": "Offline regrade of all 40 outputs with cached model judgments; no new model calls; original raw run unchanged."}
    (destination / "experiment.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (destination / "evaluation_snapshot").mkdir()
    for name in ("evaluators.py", "report.py"):
        (destination / "evaluation_snapshot" / name).write_text((ROOT / "src/evaluation" / name).read_text())
    corpus = json.loads(CORPUS.read_text())
    for case in cases:
        record = json.loads((directory / f"{case['id']}.json").read_text())
        original = record["metrics"]
        def cached_judge(*args):
            citation = original["citation_validity"]
            entailment = citation.get("entailment_check", citation)
            items = {"grounded_correctness": original["grounded_correctness"],
                     "citation_entailment": entailment,
                     "uncertainty_handling": original["uncertainty_handling"]}
            if any(item.get("assessor") != "independent_model_prompt_not_human" for item in items.values()):
                raise ValueError("Original independent judge result unavailable; leave ungraded.")
            return {key: {"passed": item["status"] == "pass", "reason": item["reason"],
                          "failure_type": item["failure_type"], "evidence_chunk_ids": item["evidence_chunk_ids"]}
                    for key, item in items.items()}
        record["original_metrics"] = original
        record["metrics"] = evaluate(case, record, corpus, cached_judge)
        record["grading_revision"] = VERSION
        (destination / f"{case['id']}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    report = build_report(destination)
    (destination / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def compare(before, after):
    """Fail closed for mismatched inputs/settings and missing cases."""
    for key in ("dataset_sha256", "corpus_sha256", "evaluator_version", "evaluator_source_sha256", "judge_prompt_sha256",
                "application_model", "embedding_model", "judge_model", "packages", "python",
                "review_annotations_sha256", "concurrency", "repetitions"):
        if before["metadata"].get(key) != after["metadata"].get(key):
            raise ValueError(f"Experiments are not comparable: {key}")
    b = {r["id"]: r for r in before["cases"]}
    a = {r["id"]: r for r in after["cases"]}
    if set(b) != set(a) or len(a) != 40:
        raise ValueError("Comparison requires the identical complete 40 cases.")
    paired = []
    for id in b:
        changes = {}
        for name in before["metrics"]:
            old, new = b[id]["metrics"][name]["status"], a[id]["metrics"][name]["status"]
            changes[name] = {"before": old, "after": new,
                             "regression": old == "pass" and new == "fail",
                             "improvement": old == "fail" and new == "pass",
                             "lost_grade": old in {"pass", "fail"} and new == "ungraded",
                             "gained_grade": old == "ungraded" and new in {"pass", "fail"},
                             "applicability_changed": (old == "not_applicable") != (new == "not_applicable")}
        paired.append({"id": id, "metrics": changes,
                       "latency_delta_seconds": a[id]["active_seconds"] - b[id]["active_seconds"]})
    return {"before": before["metadata"], "after": after["metadata"], "paired_cases": paired}


def publish_studio(baseline, improved, destination, intermediate=None, additional_runs=None):
    """Export saved, controlled-case results for a read-only dashboard.

Never rerender historical outputs with the new renderer. It would hide failures
such as K01. Baseline presentations were captured using its original snapshot.
"""
    baseline = Path(baseline)
    before = build_report(baseline)
    after = build_report(improved) if improved else None
    comparison = compare(before, after) if after else None
    for path in (additional_runs or {}).values():
        compare(before, build_report(path))
    cases = load_cases()
    frozen = json.loads((baseline / "presentations.json").read_text())["cases"]
    audit_path = Path(__file__).resolve().parents[2] / "evals/reports/baseline_failure_evidence.json"
    audit = {c["id"]: c for c in json.loads(audit_path.read_text())["cases"]} if audit_path.exists() else {}
    packets = []
    for case in cases:
        id = case["id"]
        runs = {}
        sources = [("baseline", baseline), ("intermediate", Path(intermediate) if intermediate else None)]
        sources += [(label, Path(path)) for label, path in (additional_runs or {}).items()]
        sources.append(("improved", Path(improved) if improved else None))
        for label, directory in sources:
            if directory is None:
                continue
            record = json.loads((directory / f"{id}.json").read_text())
            presentation = frozen[id] if label == "baseline" else record["presentation"]
            runs[label] = {"presentation": presentation, "metrics": record["metrics"],
                           "retrieved_evidence": record["state"].get("retrieved_evidence", []),
                           "validation_results": record["state"].get("validation_results", []),
                           "draft": record["state"].get("research_summary_draft"),
                           "nodes": record["nodes"], "active_seconds": record["active_seconds"],
                           "node_timings": record.get("node_timings", []), "segments": record.get("segments", []),
                           "review": {"status": record["state"].get("review_status"),
                                      "feedback": record["state"].get("review_feedback", ""),
                                      "approved_count": len(record["state"].get("approved_relationships", [])),
                                      "action_origin": record.get("human_action", "none")},
                           "awaiting_review": record["awaiting_review"], "trace_ids": record["trace_ids"]}
        packets.append({"id": id, "question": case["question"], "category": case["category"],
                        "expected_route": case["expected_route"], "expected_behavior": case["expected_behavior"],
                        "references": case["references"], "human_review": case["human_review"],
                        "fixture": case.get("fixture"), "runs": runs,
                        "audit": {k: audit.get(id, {}).get(k) for k in ("priority", "audit_classification", "audit_reason")}})
    bundle = {"schema_version": 1, "baseline": before, "improved": after,
              "comparison": comparison, "cases": packets,
              "intermediate_report": build_report(intermediate) if intermediate else None,
              "intermediate_comparison": compare(before, build_report(intermediate)) if intermediate else None,
              "additional_reports": {label: build_report(path) for label, path in (additional_runs or {}).items()},
              "changes": ["Conservative clarification/scope intent handling",
                          "Shared PubMed and NCBI source recognition",
                          "Conclusion integrity: exact-evidence precision, assessed summaries and separately labeled approval policy",
                          "Conservative extraction of the observed in-contrast-to relationship wording"],
              "notice": "Provisional automated results; all unreviewed references remain drafts. Human approval is not independent scientific verification."}
    target = Path(destination)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(target)
    return bundle


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--compare", type=Path)
    parser.add_argument("--regrade-cached-to", type=Path)
    args = parser.parse_args()
    result = regrade_cached(args.directory, args.regrade_cached_to) if args.regrade_cached_to else build_report(args.directory)
    if args.compare and not args.regrade_cached_to:
        result = compare(result, build_report(args.compare))
    print(json.dumps(result, ensure_ascii=False, indent=2))
