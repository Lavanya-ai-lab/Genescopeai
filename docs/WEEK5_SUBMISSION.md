# GeneScope AI — Week 5 Builder of the Week

**Evals, Monitoring and Observability MVP.** GeneScope AI uses Streamlit, LangGraph and Chroma to investigate APOE/Alzheimer evidence with a researcher review interrupt. Week 5 keeps the original six-source, 13-chunk corpus as a controlled evaluation environment.

**Submission status:** implemented and locally verified; actual human review of the 40 draft labels and hosted LangSmith delivery verification remain outstanding. No independently validated scientific accuracy is claimed.

## Evaluation and measured results

The 40 cases cover happy paths, edge cases, known risks, adversarial inputs and review workflows. Five metrics use separate evaluation logic: grounded correctness, citation validity/entailment, uncertainty, completion and active latency. The app validator is not ground truth. The separate judge prompt uses the same model, so human adjudication remains essential.

All inputs, corpus and evaluator settings stayed frozen. One baseline and three explicit improvement passes executed **160 workflow cases**. All intermediate results are retained; no best-case scores were selected.

Each cell is **passed / flagged / ungraded / N/A**, totaling 40.

| Metric | Baseline | Final |
|---|---:|---:|
| Evidence grounding | 32 / 6 / 2 / 0 | 36 / 3 / 1 / 0 |
| Citation validity | 27 / 3 / 4 / 6 | 24 / 7 / 1 / 8 |
| Uncertainty handling | 36 / 3 / 1 / 0 | 39 / 0 / 1 / 0 |
| Workflow completion | 38 / 2 / 0 / 0 | 40 / 0 / 0 / 0 |

Active latency: median **8.21s → 9.91s**; p95 **25.23s → 16.64s**. Human wait/evaluator time are excluded. The median regressed while the tail improved; single hosted-model passes do not establish causal performance gains.

Citation grades regressed. The frozen evaluator flags several safe abstentions as uncited output and has observed false positives/negatives. All flags remain visible, including four pass→fail metric transitions, one lost grade and four gained grades. These are model judgments, not scientific error rates.

## What changed

- Corrected subject-free clarification and incidental-APOE scope bypasses (E08/K07).
- Fixed PubMed-only parsing that discarded retrieved NCBI citations (H05/K06).
- Withheld unsupported precision; retained exact source quotations and original drafts for investigation. Approval/proof questions use a separately labeled application policy, not a generated scientific finding.
- Fixed the observed contrast-clause extraction miss (H02). All final workflow checks passed, including scripted approval, rejection/reason preservation and fresh-thread clarification.

## Demonstration

Run `python -m streamlit run app.py`. The example button fills the question without starting research. Show clarification, scope stopping, source evidence and distinct approved/rejected candidate graphs.

Open **Reliability Studio** for Evaluation Overview, Failure Investigation and Before/After. Browse K01’s original unsafe answer, exact passages, evaluator rationale and final quote; inspect H02/A07 across retained iterations; show all regressions and denominators. Studio reads saved results and works without model credentials; it never launches paid evaluations.

LangSmith graph/LLM instrumentation and interrupt read-back verification are implemented and SDK-tested with mocked transport. Hosted delivery is **unverified**, not inferred from IDs. After configuring credentials, run `python -m src.observability --verify-review`; verify an actually traced saved case with `--verify-case`.

## Verification and limitations

**190 tests passed**, with syntax/compile and whitespace checks passing. Corpus/case/evaluator hashes match. Third-party deprecation warnings remain. Human labels are still **0/40 reviewed**; use the prioritized queue. Model judgments, temporal therapy wording and conservative conclusion fallbacks need review. Checkpoints remain in memory and do not survive server restarts.

[Full technical report and exact file changes](../evals/reports/PHASE2_RESULTS.md) · [40-case comparison](../evals/reports/case_comparison.csv) · [Original failure evidence](../evals/reports/BASELINE_FAILURE_AUDIT.md) · [Human review queue](../evals/reports/BASELINE_HUMAN_REVIEW.csv) · [Setup and reproducibility](../README.md)
