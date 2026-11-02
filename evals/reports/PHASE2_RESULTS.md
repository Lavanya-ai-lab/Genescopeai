# Week 5 submission — GeneScope AI reliability MVP

**Local implementation and evaluation complete. Submission blockers remain: actual human review of the references/disputed grades, and hosted LangSmith delivery verification.** Do not present draft labels or model grades as independently validated scientific accuracy.

## What was built

A controlled APOE/Alzheimer research assistant with 40 frozen evaluation cases, five independent evaluation dimensions, optional LangSmith graph/LLM traces, and a read-only Reliability Studio. The existing 13 chunks from six sources were retained; no articles or research domains were added.

Four targeted improvement groups: conservative clarification/scope intent handling; shared PubMed/NCBI citation recognition; scientific-answer integrity (exact precision/source quotation, assessed-only summaries, and a separately labeled approval policy); and conservative extraction of the observed “in contrast to” relationship phrasing. No research agents or extra application LLM calls were introduced.

## Method and immutable inputs

One baseline plus three explicit 40-case improvement iterations were executed: **160 workflow case executions**, not 160 API requests and not 240 cases. Each experiment is a single sequential pass. The first improvement exposed H02 extraction and K06 precision-withholding regressions; the next exposed the A07 approval/proof answer problem. All iterations are preserved and selectable in Studio. The last pass was not selected because it had the best headline scores or fastest latency.

Dataset SHA256: `2c739f3cb27357274d8497bc98392d3564526936508fd2e8b27b1a62d218c5fc`. Corpus SHA256: `0414fe9a7dd4b15bb6876d403f31153b5b17107c7f5d5cd1080feba1fc4535e2`.
Evaluator version: `1.0.1`; evaluator source and prompt hashes match across the paired runs. The corpus, all case inputs, application/judge models, package versions, Python version, concurrency and repetition count were verified identical. Agent behavior changed deliberately; the evaluator rubric and labels did not.

The grader implementation is separate from the application evidence validator; app support statuses are not ground truth. Semantic grading uses an independent prompt with the same configured Qwen model, so correlated-model bias remains. Citation presence is checked independently, with semantic entailment assessed separately. Latency measures active graph wall time and excludes human wait, rendering and evaluator calls. CLI graph/presentation runs are complemented by offline Streamlit interaction tests; this is not a 40-case live-browser benchmark.

## Measured results

Each cell is **passed / flagged / ungraded / not applicable**; every cell accounts for all 40 cases. These are preserved automatic judgments, not human-confirmed scientific error rates.

| Metric | Baseline | Iteration 1 | Iteration 2 | Final |
|---|---:|---:|---:|---:|
| Grounding | 32 / 6 / 2 / 0 | 35 / 4 / 1 / 0 | 36 / 3 / 1 / 0 | 36 / 3 / 1 / 0 |
| Citations | 27 / 3 / 4 / 6 | 24 / 7 / 1 / 8 | 24 / 7 / 1 / 8 | 24 / 7 / 1 / 8 |
| Uncertainty | 36 / 3 / 1 / 0 | 38 / 1 / 1 / 0 | 38 / 1 / 1 / 0 | 39 / 0 / 1 / 0 |
| Workflow | 38 / 2 / 0 / 0 | 39 / 1 / 0 / 0 | 40 / 0 / 0 / 0 | 40 / 0 / 0 / 0 |

| Active latency | Baseline | Iteration 1 | Iteration 2 | Final |
|---|---:|---:|---:|---:|
| Median (s) | 8.21 | 6.60 | 6.44 | 9.91 |
| p95 (s) | 25.23 | 12.60 | 9.36 | 16.64 |
| Total (s) | 411.96 | 249.49 | 219.99 | 341.18 |

Workflow checks improved from **38/40 to 40/40**. Median latency changed by **+1.70s** (+20.7%), while p95 changed by **-8.59s**. Thus the median regressed even though the tail improved. Network/provider variability and differing claim workloads are confounders; these single passes do not establish a causal performance gain or an SLA.

## Case-level improvements, regressions and coverage

There were **9 automatic metric fail→pass transitions**, **4 pass→fail transitions**, **1 lost grade**, and **4 gained grades**. A coverage change is not itself a quality improvement. All 40 rows, including unchanged and N/A transitions, are in [case_comparison.csv](case_comparison.csv) and [before_after.json](before_after.json).

| Transition | Exact case/metric pairs |
|---|---|
| Fail → pass | E08 Grounding; E08 Uncertainty; E08 Workflow; K07 Grounding; K07 Uncertainty; K07 Workflow; K08 Grounding; K08 Uncertainty; A06 Grounding |
| Pass → fail | K03 Citations; A03 Citations; A08 Citations; W08 Citations |
| Graded → ungraded | A04 Uncertainty |
| Ungraded → graded | A05 Citations; W04 Grounding; W04 Citations; W04 Uncertainty |

Citation grading regressed: K03, A03, A08 and W08 gained citation flags. These final outputs are safe insufficiency messages rather than scientific assertions with invented references. The frozen evaluator treats any nonempty summary as citation-bearing output; those flags are retained for human adjudication, not silently waived. K01 still receives a fail even though the original affirmative allele-prevalence assertion is gone and the source is now quoted with its gene-level subject intact. A03 safely abstains but does not provide the more helpful risk-versus-certainty explanation expected by the reference. This can be an answer-quality shortcoming without being a fabricated biological claim.

W04 gained a semantic grade after its baseline judgment was unavailable. Its remaining undated therapy-availability wording deserves review. The model rationale also infers APOE-specific implications from a general AD-therapy review, which the text does not independently establish. A04 remains ungraded (including a lost uncertainty grade). No successful judge retries were substituted to improve scores.

## Confirmed application findings and fixes

- **E08/K07:** Both now stop before retrieval. The baseline K07 answer eventually declined BRCA1 correctly, so the genuine failure was unnecessary retrieval, not fabrication of a BRCA1 mutation.
- **H05/K06:** The application dropped real NCBI IDs. Offline reproduction and the live runs confirm those IDs now reach evidence assessment. K06 retains the exact chromosome-19 statement as an indexed quote. Its conclusion card can still be conservative despite the explicit source answer.
- **K01/K08/A05/W04/W08:** The original unsafe numerical/molecular assertions were investigated against exact passages. Generated precision requires exact evidence wording or a complete checked source quotation; original drafts remain in forensic records. This is a conservative presentation contract, not independent scientific verification.
- **H02:** The first iteration missed a supported epsilon 2 relationship expressed with “in contrast to.” The targeted clause split fixed the observed extraction shape; all final workflow checks passed.
- **A07:** The intermediate run exposed an affirmative answer to whether approval proves science. The final app answers **“No. Researcher approval records a review decision; it does not independently verify a scientific relationship.”** The card is labeled Review policy and attributed to application behavior, not indexed scientific evidence. The final case passed all automatic metrics.

The [baseline audit](BASELINE_FAILURE_AUDIT.md) contains complete original questions, outputs, retrieved/reference passages, evaluator explanations, exact offline NCBI reproductions and classifications. It also identifies baseline evaluator false negatives (A05/W08) and disputed flags. All 40 reference labels remain drafts; audit annotations are AI inspection, not human adjudication.

## Human review and observability

All eight final workflow cases passed: real interrupt, scripted approval, rejection with exact feedback, blank-reason rejection, clean clarification thread, empty retrieval, retrieval failure and malformed validator output. Rejected candidates and the original evidence remain traceable; rejected relationships never enter approved_relationships. These scripted decisions do not review the golden labels or independently verify the science.

LangSmith credentials remain unconfigured; **no hosted delivery is claimed**. Real SDK tests cover graph/LLM spans, shared thread metadata, expected GraphInterrupt handling, rejection resume, upload failure resilience and hosted-readback validation with mocked transport. `python -m src.observability --verify-review` performs a real hosted readback once configured, without Nebius research calls. Verified case links appear only after `--verify-case` has read those actual run IDs. The current [verification report](langsmith_verification.json) explicitly says not_configured.

## Demonstration

1. Finish any pending review, restart Streamlit, and click Try an example question. It fills the input; Run research stays explicit.
2. Show vague-question clarification, explicit option selection and fresh-thread continuation. Show the incidental-APOE BRCA1 scope stop.
3. Inspect source excerpts and model-assessed candidates. Approve one run and reject another with a reason; show distinct graph edge labels/styles and empty approved relationships after rejection.
4. Open Reliability Studio: overview counts/denominators; K01/K06 failure investigations with real passages; H02/A07 intermediate-versus-final output; and the complete before/after matrix including regressions and slower cases.
5. Show draft review labels and unverified trace status honestly. After credentials are configured, run the transport/readback command and demonstrate verified hosted links.

## Verification and remaining limitations

- Automated verification: **190 tests pass**, including the existing successful research/review paths, precision adversarial cases, NCBI assessment reachability, no-paid-calls UI tests and approval-policy labeling. Syntax/compile and whitespace checks passed. Third-party LangSmith/Streamlit/Pandas deprecation warnings remain.
- **Human review is outstanding:** 0/40 labels reviewed. Prioritize the [review queue](BASELINE_HUMAN_REVIEW.csv), then the remaining cases. Do not reinterpret approval to develop as scientific adjudication.
- **Hosted tracing is outstanding:** credentials and actual server readback are required. UUIDs alone are not proof of delivery.
- Model judgments have observed false positives, false negatives and unavailable outputs. The same-model evaluator is not independent human verification; no untouched holdout or statistical confidence is claimed.
- Precision rules may withhold valid paraphrases; model answers may be irrelevant or overcautious. Historical therapy claims can still lose their dates in generated wording, so the frozen abstracts do not establish current clinical availability.
- The research scope remains the frozen APOE/Alzheimer collection. No broad clinical/general-genetics coverage is claimed.
- In-memory checkpoints survive reruns, not server restarts. Finish pending reviews before deploying/restarting. UI interactions were tested with AppTest; no manual browser acceptance session is claimed.

## Phase 2 file changes

Application: `app.py`; `src/agents/clarification_agent.py`, `extract_claims.py`, `validation_agent.py`, `evidence_validator.py`, `summarize_evidence.py`, `verified_findings.py`, `analysis_agent.py`; `src/graph/state.py`; `src/visualization/research_conclusion.py`; `src/observability.py`; `src/evaluation/runner.py`, `report.py`; `README.md`.

New code/tests: `src/agents/evidence_rules.py`; `src/visualization/reliability_studio.py`; `tests/test_evidence_integrity.py`; `tests/test_reliability_studio.py`. Updated `tests/test_research_scope.py` strengthens withholding assertions while preserving raw drafts and scopes research-tab assertions to the original tabs.

Artifacts: baseline audit Markdown/JSON, blank human-review CSV, all iteration reports, paired JSON/CSV, read-only Studio bundle, original baseline source archive, LangSmith status report and this submission report. Raw per-case records and source snapshots remain under ignored `evals/results/`.

The golden inputs, frozen corpus, evaluator implementation/rubric, graph routing, Chroma retrieval and relationship visualization modules were not modified in Phase 2.
