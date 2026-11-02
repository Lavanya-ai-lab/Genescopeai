"""Read-only evaluation UI. No workflow, evaluator, model, or network calls."""

import json
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

REPORTS = Path(__file__).resolve().parents[2] / "evals/reports"
BUNDLE = REPORTS / "reliability_studio.json"
NAMES = {"grounded_correctness": "Evidence grounding", "citation_validity": "Citation validity",
         "uncertainty_handling": "Uncertainty", "workflow_completion": "Workflow completion"}


@st.cache_data(show_spinner=False)
def load_results(path, modified):
    data = json.loads(Path(path).read_text())
    if data.get("schema_version") != 1 or len(data.get("cases", [])) != 40:
        raise ValueError("Expected a saved 40-case evaluation bundle.")
    if len({c["id"] for c in data["cases"]}) != 40:
        raise ValueError("Duplicate evaluation case IDs.")
    for label in ("baseline", "improved"):
        report = data.get(label)
        if report and (report.get("completed") != 40 or any(
            sum(v.get(k, 0) for k in ("pass", "fail", "ungraded", "not_applicable")) != 40
            for v in report["metrics"].values()
        )):
            raise ValueError("Incomplete metric denominators.")
    return data


def _score_rows(report, label):
    return [{"Run": label, "Metric": NAMES[name], "Passed": value["pass"],
             "Flagged": value["fail"], "Ungraded": value["ungraded"],
             "N/A": value["not_applicable"], "Graded": value["graded"],
             "Pass / graded": f"{value['pass']}/{value['graded']}"}
            for name, value in report["metrics"].items()]


def _cards(report):
    cards = []
    for name, result in report["metrics"].items():
        cards.append(f'<div class="reliability-card"><span>{escape(NAMES[name])}</span>'
                     f'<strong>{result["pass"]}<small> / {result["graded"]} graded</small></strong>'
                     f'<span>{result["fail"]} flagged · {result["ungraded"]} ungraded · {result["not_applicable"]} N/A</span></div>')
    st.markdown('<div class="reliability-cards">' + ''.join(cards) + '</div>', unsafe_allow_html=True)


def _trace_links(run):
    path = REPORTS / "langsmith_verification.json"
    try:
        verification = json.loads(path.read_text()) if path.exists() else {}
    except (ValueError, OSError):
        verification = {}
    verified = {r["run_id"]: r for r in verification.get("verified", [])}
    links = [verified[id] for id in run["trace_ids"] if id in verified]
    if not links:
        st.caption("Hosted trace not verified for this case. Local run IDs are retained; no trace link is fabricated.")
    for item in links:
        if item["url"].startswith("https://"):
            st.link_button(f"Open verified {item['phase']} trace", item["url"])


def show_reliability_studio():
    st.subheader("Reliability Studio")
    st.caption("Inspect the evidence behind the evaluation. Follow every improvement and every regression.")
    if not BUNDLE.exists():
        st.info("No saved evaluation bundle is available yet. Evaluations run explicitly from the command line; opening this page never starts one.")
        return
    try:
        data = load_results(str(BUNDLE), BUNDLE.stat().st_mtime_ns)
    except (ValueError, KeyError, OSError) as exc:
        st.error("The saved evaluation results could not be loaded: " + str(exc))
        return
    st.markdown("""<style>
    .reliability-cards {display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:12px 0 20px;}
    .reliability-card {border:1px solid #dce4f1;border-radius:12px;padding:16px;background:linear-gradient(140deg,#fff,#f5f8ff);color:#183158;}
    .reliability-card span {display:block;font-size:.85rem;line-height:1.6;}
    .reliability-card strong {display:block;font-size:1.6rem;margin:8px 0;}
    .reliability-card small {font-size:.8rem;font-weight:400;}
    </style>""", unsafe_allow_html=True)
    st.warning(data["notice"])
    st.caption("Fixed APOE corpus · 40 cases · One sequential pass per version · Same-model independent rubric · No untouched holdout")
    overview, investigate, paired = st.tabs(["Evaluation Overview", "Failure Investigation", "Before/After"])
    before, after = data["baseline"], data.get("improved")

    with overview:
        report = after or before
        st.markdown("#### Latest saved run")
        st.caption(report["metadata"]["experiment"])
        _cards(report)
        latency = report["latency"]
        st.write(f"Active latency: **{latency['median_seconds']:.2f}s median** · **{latency['p95_seconds']:.2f}s p95**")
        st.caption("Human wait and independent evaluator time excluded. Mixed-case latency includes clarification and fault stops; no SLA is claimed.")
        rows = _score_rows(before, "Baseline") + (_score_rows(after, "Improved") if after else [])
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.caption("Pass fractions use graded cases only. Ungraded and N/A cases stay visible. These are provisional automated judgments, not independently validated scientific accuracy.")
        if after:
            chart = pd.DataFrame({label: {NAMES[k]: v["pass_fraction"] for k, v in r["metrics"].items()}
                                  for label, r in (("Baseline", before), ("Improved", after))})
            st.bar_chart(chart, color=["#91a5c8", "#2965b8"], horizontal=True)
        else:
            st.info("The improved run is pending. No before/after values are simulated.")
        with st.expander("Reproducibility and tracing"):
            st.json({k: report["metadata"].get(k) for k in (
                "dataset_sha256", "corpus_sha256", "evaluator_version", "evaluator_source_sha256",
                "judge_prompt_sha256", "application_model", "judge_model", "reviewed_cases", "tracing")})
            st.write("36 normal cases and 4 labeled fault-injection fixtures. Scripted approval/rejection is not human adjudication of the benchmark.")
        if data.get("intermediate_report"):
            with st.expander("Intermediate run retained — no best-case selection"):
                st.write("The first improved pass exposed a precision-withholding regression and missed contrast-clause extraction. It remains available for investigation; the final pass followed explicit fixes.")
                st.dataframe(pd.DataFrame(_score_rows(data["intermediate_report"], "Intermediate")), hide_index=True, use_container_width=True)
                for name, historical in data.get("additional_reports", {}).items():
                    st.caption("Retained run: " + historical["metadata"]["experiment"])
                    st.dataframe(pd.DataFrame(_score_rows(historical, name)), hide_index=True, use_container_width=True)
        st.download_button("Download measured results", json.dumps(data, ensure_ascii=False, indent=2),
                           file_name="genescope-reliability-results.json", mime="application/json", key="reliability_download")

    with investigate:
        st.markdown("#### Follow a case from question to evidence")
        priority_only = st.toggle("Prioritize flagged and disputed review cases", value=True, key="reliability_priority")
        options = [c for c in data["cases"] if not priority_only or c["audit"].get("priority") or any(
            score["status"] in {"fail", "ungraded"} for r in c["runs"].values() for score in r["metrics"].values())]
        options.sort(key=lambda c: (c["audit"].get("priority") or "P2", c["id"]))
        if not options:
            st.info("No cases match this filter.")
        else:
            ids = [c["id"] for c in options]
            case_id = st.selectbox("Case", ids, format_func=lambda id: next(
                f"{c['id']} · {c['question'] or '(empty question)'}" for c in options if c["id"] == id), key="reliability_case")
            case = next(c for c in options if c["id"] == case_id)
            label = st.selectbox("Saved run", list(case["runs"]),
                                 format_func=lambda label: {"baseline": "Baseline", "intermediate": "Iteration 1", "iteration_2": "Iteration 2", "improved": "Final improved"}.get(label, label),
                                 key="reliability_run")
            run = case["runs"][label]
            st.markdown("**Researcher's original question**")
            st.write(case["question"] or "(empty question)")
            st.caption(f"Reference review: {case['human_review']['status']} · Category: {case['category']} · Fixture: {case.get('fixture') or 'none'}")
            if case["audit"].get("audit_reason"):
                with st.container(border=True):
                    st.markdown("**Baseline audit — AI inspection, human adjudication pending**")
                    st.write(case["audit"]["audit_reason"])
                    st.caption("The audit is separate from the preserved automated score. It includes evaluator false positives and false negatives.")
            left, right = st.columns(2)
            with left:
                st.markdown("**Reference expectation**")
                st.write(case["expected_behavior"])
                st.caption("Expected route: " + case["expected_route"])
            with right:
                st.markdown("**Actual displayed answer**")
                st.write(run["presentation"].get("conclusion") or "No scientific conclusion: clarification or scope stop.")
            with st.expander("Original displayed research summary", expanded=True):
                st.write(run["presentation"].get("summary") or "No scientific summary was generated.")
            st.dataframe(pd.DataFrame([{"Metric": NAMES.get(k, k), "Verdict": v["status"], "Explanation": v["reason"]}
                                      for k, v in run["metrics"].items()]), hide_index=True, use_container_width=True)
            st.caption(f"Active time: {run['active_seconds']:.2f}s · Awaiting research review: {run['awaiting_review']}")
            _trace_links(run)
            with st.expander("Execution, latency and review decision"):
                st.dataframe(pd.DataFrame(run.get("node_timings", [])), hide_index=True, use_container_width=True)
                st.json({"segments": run.get("segments", []), "review": run.get("review", {})})
                st.caption("Scripted review decisions test workflow behavior. They do not constitute human adjudication or independent scientific verification.")
            with st.expander("Actual retrieved passages and reference passages"):
                for e in run["retrieved_evidence"]:
                    st.markdown(f"**{e.get('document_id')} · {e.get('chunk_id')}**")
                    st.write(e.get("content", ""))
                if not run["retrieved_evidence"]:
                    st.write("No evidence retrieved.")
                for ref in case["references"]:
                    st.caption("Reference: " + ref["chunk_id"])
                    st.write(ref["quote"])
            with st.expander("Findings, candidates and application assessments"):
                st.caption("The application's assessment is the component under test, not independent ground truth.")
                st.json({"findings": run["presentation"].get("findings"), "candidates": run["presentation"].get("candidates"),
                         "review_status": run["presentation"].get("review_status"), "application_assessment": run["validation_results"]})
            if run.get("draft"):
                with st.expander("Unassessed original draft — investigation only"):
                    st.warning("Forensic model output may contain unsupported assertions. It is not the supported scientific answer.")
                    st.write(run["draft"])
        queue = REPORTS / "BASELINE_HUMAN_REVIEW.csv"
        if queue.exists():
            st.download_button("Download prioritized human review queue", queue.read_text(),
                               file_name=queue.name, mime="text/csv", key="reliability_review_queue")

    with paired:
        st.markdown("#### What changed, and what did it cost?")
        for change in data["changes"]:
            st.write("• " + change)
        comparison = data.get("comparison")
        if not comparison:
            st.info("A paired comparison appears only after the identical 40-case improved run is saved.")
        else:
            pairs = comparison["paired_cases"]
            improvements = sum(v["improvement"] for p in pairs for v in p["metrics"].values())
            regressions = sum(v["regression"] for p in pairs for v in p["metrics"].values())
            lost = sum(v.get("lost_grade", False) for p in pairs for v in p["metrics"].values())
            st.write(f"**{improvements} metric improvements · {regressions} metric regressions · {lost} lost grades** across 40 paired cases.")
            st.caption("A metric improvement is fail → pass; a regression is pass → fail. Coverage gains and losses are separate from quality gains.")
            table = [{"Case": p["id"], **{NAMES[k]: v["before"] + " → " + v["after"] for k, v in p["metrics"].items()},
                      "Active latency Δ (s)": round(p["latency_delta_seconds"], 2)} for p in pairs]
            st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True)
            selected = st.selectbox("Inspect before/after output", [c["id"] for c in data["cases"]], key="reliability_pair")
            case = next(c for c in data["cases"] if c["id"] == selected)
            st.write(case["question"] or "(empty question)")
            columns = st.columns(2)
            for column, label in zip(columns, ("baseline", "improved")):
                with column:
                    st.markdown("**" + label.title() + "**")
                    value = case["runs"][label]
                    st.write(value["presentation"].get("conclusion") or "Clarification/scope stop; no scientific conclusion.")
                    st.write(value["presentation"].get("summary") or "No scientific summary.")
                    st.caption(f"{value['active_seconds']:.2f}s active time")
