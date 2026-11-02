# Phase 1 baseline — GeneScope AI

**40/40 cases executed; application behavior unchanged. Stop before Phase 2.**
This is a provisional automated baseline: **0/40 reference labels are
human-reviewed**. Human-review fields remain drafts. The independent evaluator
has its own implementation and rubric, but this run used the same configured
model as the application (Qwen3-30B-A3B-Instruct-2507); correlated-model bias remains.
These are automated test judgments, not verified scientific accuracy scores.

## What actually ran

The existing six-source, 13-chunk Chroma collection matched the frozen corpus
exactly before and after execution. No collection rebuild or new ingestion took
place. One sequential pass ran all 40 cases, including four labeled injected
fixtures. All research questions, original answers, retrieved passages, validation
outputs, node timings, and review transitions are retained locally.

The sandbox-only attempt (`baseline-v1`) stopped after three network failures.
It is **excluded** from the measured baseline. With authorized network access,
`baseline-live-v1` completed 40/40. A source snapshot was saved before behavior
changes. `baseline-phase1-v1` contains a deterministic offline regrade of those
same 40 outputs using the original cached semantic judgments. No new research
requests, selective model retries, or agent fixes were introduced by regrading.

The grader accounting revision (1.0.1) prevents an identity-only citation check
from passing unassessed entailment, and sends unknown-ID/refusal disagreements
to adjudication rather than declaring fabricated evidence. The original grades
are preserved in the raw run and each regraded case's `original_metrics` field.
The exact evaluator and prompt hashes are recorded. The raw original application
source snapshot and regrading evaluator snapshot remain in ignored results.

The committed [measured JSON report](baseline_phase1.json) is derived from those
records and omits raw research feedback and unverified hosted trace links.

## Five measured metrics

| Metric | Passed | Flagged | Ungraded | Not applicable |
|---|---:|---:|---:|---:|
| Evidence-grounded correctness | 32 | 6 | 2 | 0 |
| Citation validity, including entailment | 27 | 3 | 4 | 6 |
| Uncertainty handling | 36 | 3 | 1 | 0 |
| Workflow completion | 38 | 2 | 0 | 0 |

Latency is measured rather than assigned a fabricated quality score: median
**8.21 seconds**, nearest-rank p95 **25.23 seconds**, total active time **411.96
seconds**. These aggregate 40 heterogeneous cases, including fast clarification
and fault stops. Normal-case median (36 cases) was 8.39 seconds; injected-fixture
median (4 cases) was 4.16 seconds. Human waiting and offline evaluator time are
excluded. No service latency target or statistical significance is claimed.
Research/retrieval accounted for 235.88 seconds of aggregate node time,
summarization 60.32 seconds, and evidence assessment 115.17 seconds. Node-level
timing does not separate embedding-network time from local client construction.

## Three priority failure investigations

These are three observed categories, **tied at two cases each**. They are not
three statistically established root causes or three independent populations.
The JSON report separately retains raw automatic failure labels, which overlap.

| Category | Cases | Observed behavior | Recommended Phase 2 change |
|---|---|---|---|
| Pre-retrieval gating gaps | E08, K07 | A longer subject-free request triggered research; a BRCA1 request bypassed scope checking by mentioning APOE incidentally. | Extend conservative request-intent handling and distinguish the substantive requested topic from an incidental scope mention. Preserve valid alternative APOE wording. |
| Unsupported precision in visible summaries | K01, K08 | The summary inferred epsilon 4 patient prevalence from gene contribution, and supplied a nucleotide substitution absent from the indexed text. Grounding and entailment judges both flagged these; source inspection confirms the requested details are absent. | Strengthen evidence-only generation around exact quantities/molecular details and ensure unsupported summary claims are clearly withheld or qualified in the user-facing scientific answer. Retain raw output for investigation. |
| NCBI citation recognition gaps | H05, K06 | Valid retrieved `ncbi_gene_348` citations appear in claim text but are absent from the app's extracted citation lists, preventing evidence assessment/promotion. | Use a shared source-ID recognizer for PubMed and NCBI across citation checks, claim extraction, and conclusion provenance. Do not infer entailment from ID validity. |

The NCBI category is a deterministic pipeline diagnostic, separate from semantic
answer correctness: those two summaries could be correct while downstream claim
assessment still misses their citations. It is not counted as two extra accuracy
failures. The application's validator is the component under test, never the
independent ground-truth judge.

## Review behavior and safeguards

All eight workflow cases passed their deterministic lifecycle checks. W02 paused
and recorded scripted approval; W03 rejected with the exact supplied reason;
W04 rejected with a blank reason and no invented feedback. Rejected candidates,
evidence, summary and findings stayed intact; approved lists stayed empty.
W05 clarified without retrieval, then used a fresh thread. Empty retrieval and
retrieval errors stopped generation; malformed validation produced no findings
or candidate relationships. These were scripted decisions, not human adjudication.

The ordinary vague question E07 and clearly unrelated questions A01/A02 stopped
before retrieval. The two gating failures above are the measured exceptions.

## Disputed judgments and remaining limitations

- W04's independent semantic evaluation failed to parse, leaving its three semantic
  metrics ungraded. Its actual review/rejection lifecycle still passed. No
  successful retry was substituted for that observation.
- A04/A05 mention an invalid ID while refusing to use it as evidence. Citation
  identity and semantic judgments disagree; these are ungraded for citation use,
  not declared fabricated scientific citations. A04 grounding also awaits review.
- A03/A06 were flagged for conservative conclusion cards despite supported risk
  explanations and correct resistance to the adversarial instructions. Their
  model judgments need human adjudication; do not equate these flags with proven
  scientific errors. Some judge rationales also invoke outside knowledge, another
  reason to inspect them against the frozen text rather than accept them as truth.
- The 40 case references and all disputed grades need actual human review. If
  question/rubric/reference inputs change, freeze a new version and run a new
  baseline before changing agent behavior. This MVP has no untouched holdout.
- LANGSMITH_API_KEY is absent. Instrumentation was tested with the real SDK and
  mocked uploads, including linked interrupt/resume traces and upload failure
  resilience; **hosted trace delivery has not been demonstrated**.
- Hosted model outputs are not deterministic even at temperature zero. One pass
  does not establish production accuracy, reliability, or stable tail latency.

## Phase 2, after baseline review

1. Adjudicate the disputed grades and review reference expectations. Freeze any
   necessary corrections before another official paired baseline.
2. Implement the three targeted changes above with regressions. Do not expand
   the corpus, introduce new research agents, or add automatic paid evaluations.
3. Rerun the identical 40-case dataset with the same evaluator/prompt/models,
   runtime and execution protocol. Report every improvement, regression and
   ungraded result; before/after comparison rejects mismatched settings.
4. Add Reliability Studio's Evaluation Overview, Failure Investigation and
   Before/After Comparison using the saved real artifacts. Clearly label draft
   references, model judgments, pending review and tracing availability.
5. Add the homepage's explicit guided example and honest scope messaging; finish
   demonstration instructions and connect/verify LangSmith when configured.

No agent behavior changes, homepage redesign, improved-run scores or Reliability
Studio views are included in Phase 1.

## Verification performed

- `python -m pytest -q tests`: **154 passed** (127 existing regressions and 27
  evaluation/tracing tests). No failures. One third-party LangSmith wrapper
  deprecation warning remains.
- `python -m compileall -q app.py src tests`: passed.
- `git diff --check`: passed.
- `python -m pip check`: no broken installed requirements.
- Read-only corpus/index verification: 13 matching chunks from six sources;
  exactly 40 unique cases and zero human-reviewed labels.
- Live baseline: 40/40 cases executed. All metric denominators account for
  passed, flagged, ungraded and not-applicable results without dropping cases.
- Real LangSmith SDK tests used mocked uploads and mocked model transport:
  linked pause/resume roots, raw-client LLM spans, and research success despite
  trace upload failure. They do not demonstrate remote hosted trace delivery.

## Files delivered

Modified: `app.py` (trace contexts/linked review metadata only),
`src/agents/summarize_evidence.py` and `src/agents/evidence_validator.py`
(wrapping existing SDK clients only), `requirements.txt`, `.env.example`,
`.gitignore`, and `README.md`.

Created: `src/observability.py`; `src/evaluation/dataset.py`, `evaluators.py`,
`runner.py`, `report.py`; `evals/apoe_v1.jsonl`, `corpus.json`, `manifest.json`,
`DATASET_CARD.md`, `HUMAN_REVIEW.md`; `requirements-dev.txt`;
`tests/test_evaluation.py`; this report and its measured JSON companion.

The graph/state schema, retrieval implementation, agent prompts, scientific
corpus, graph visualization, dashboard layout and review decisions were preserved.
