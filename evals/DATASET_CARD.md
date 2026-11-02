# APOE v1 evaluation dataset

**Status: 40 drafted cases; zero human-reviewed labels at creation.** This is a
provisional benchmark, not a completed human-reviewed golden set. Model-written
expectations and evaluator judgments do not constitute scientific verification.

The controlled environment is the existing `genescope_research` collection:
six source documents, 13 chunks, chunk size 700, overlap 100, retrieval k=3.
`corpus.json` contains the exact indexed text and existing source metadata.
`manifest.json` records content hashes, source revision, models, and installed
runtime versions. Before and after an experiment, the runner verifies the
frozen case inputs, corpus, and active Chroma chunk IDs/content using read-only
SQLite. No collection is rebuilt and no articles are added.

The snapshot comprises the NCBI APOE gene summary and five already-indexed
PubMed abstracts (33340485, 33576571, 36348357, 40938771, 42425064). They are
abstracts, not full papers or a complete/current clinical evidence review.
Source identifiers and metadata are retained for attribution. Historical claims
must retain their dates; the corpus does not establish current treatment approval
status. Verify source licensing before redistributing this snapshot publicly.

## Case composition

`apoe_v1.jsonl` has five groups of eight: happy paths (H), edge cases (E), known
scientific risks (K), adversarial inputs (A), and workflow/review cases (W).
Every case includes expected routing, expected behavior, prohibited claims,
exact corpus passage references where applicable, and human-review fields.
References identify supporting or limiting evidence; they do not guarantee that
retrieval returns that passage. Semantic grading requires support in the actual
retrieved passages as well as correctness relative to the question.

Labeled fixtures A05, W06, W07, and W08 inject document instructions, empty
retrieval, retrieval failure, and malformed validator output respectively.
These are deterministic test overlays, not changes to the real collection.
Reports identify normal and injected cases separately. W02–W04 execute scripted
approval/rejection decisions through the real interrupt; these decisions are
never described as human scientific adjudication. W05 uses a new thread after
clarification. Duplicate questions with different review actions are intentional.

## Human review procedure

Open `apoe_v1.jsonl` and the corresponding passages in `corpus.json`. Review each
question, expected route, behavior, prohibited claims, reference completeness,
and any required candidate. Use the frozen text, not model memory. Record
`human_review.reviewer`, an ISO date in `reviewed_at`, substantive `notes`, and
change `status` to `reviewed` only after actual review. All four fields are
required for reviewed cases. The runner never fills these fields automatically.

If an expectation needs correction, correct it **before** the official baseline
and deliberately version/refreeze the dataset. Case-input hashes exclude only
human-review annotations, so adding review metadata does not change inputs.
Changing question/rubric/references invalidates v1 and requires a new manifest
and a new paired baseline. Keep the provisional baseline for traceability.

## Five metrics

1. **Evidence-grounded correctness:** separate rubric prompt judges the actual
   answer, visible findings and candidates against retrieved evidence, question,
   expected behavior, and forbidden claims. No app support verdict is supplied.
2. **Citation validity:** independent ID checks cover PubMed and NCBI, require
   existence in retrieval and corpus, and combine with separate semantic
   entailment assessment. Source existence alone never earns a semantic pass.
3. **Uncertainty handling:** separate rubric judges association/causality,
   risk/certainty, protective/immunity, mouse/human translation, temporal limits,
   refusal to prescribe, and acknowledgment of missing evidence.
4. **Workflow completion:** actual node events and state verify routing,
   stop-before-retrieval, clean threads, expected candidates, pause/resume,
   evidence preservation, exact feedback, and approval invariants. An expected
   interrupt is successful progress, not an execution error.
5. **Latency:** monotonic active wall time, segment/node durations, median and
   nearest-rank p95. Human wait and independent evaluator time are excluded.
   No invented latency service target or speed score is used.

Scores are pass/fail, ungraded, or not applicable. Reports show denominators;
judge failure is ungraded rather than a pass. Scientific stops use deterministic
no-output safeguards and workflow assertions. Evaluators preserve
unknown-ID/entailment disagreements as ungraded for adjudication: an
invalid citation mentioned in a refusal is not automatically used as evidence.
An identity-only check never passes citation entailment. Accounting corrections
can be applied to all saved outputs with cached model judgments, preserving the
original grades and requiring no new research calls.
Model-assessed scientific scores
remain provisional even after reference labels are reviewed; inspect/adjudicate
disputed model judgments. By default the separate evaluator uses the configured
application model with a separate prompt; that is independent implementation,
**not independent model identity**. Set EVAL_JUDGE_MODEL to a different available
model to reduce correlated-model bias and freeze it for both experiments.

## Baseline and comparison

One sequential run over 40 cases is the MVP baseline. Temperature zero does not
make hosted models deterministic; this is a single-pass result with no claim of
statistical significance. Root-cause investigation must inspect the saved raw
answer, retrieved passages, timing, and review lifecycle. Ranked failure labels
can overlap, are not automatically proven root causes, and expose case IDs.
Count real failures before choosing three or four agent changes.

The improved run must use the same complete 40 inputs, corpus, evaluator prompt,
models, runtime packages, concurrency, and repetition count. Comparisons reject
mismatches and report case-level improvements and regressions, not just averages.
Do not tune on a hidden holdout and then claim untouched test performance. This
MVP uses all 40 cases for development; an independent holdout is future work.
