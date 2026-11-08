# GeneScopeAI — Fine-Tuned Qwen Model Card

## 1. Model Overview

GeneScopeAI explores evidence-grounded classification of genetic research claims.

This experiment fine-tunes Qwen3-1.7B-Base using Low-Rank Adaptation (LoRA) to determine whether a scientific claim is supported, contradicted, or not established by the supplied evidence.

The objective is to improve evidence-based reasoning without treating general scientific knowledge as proof that a particular reference supports a claim.

## 2. Model Details

| Attribute | Value |
|---|---|
| Base model | Qwen/Qwen3-1.7B-Base |
| Fine-tuning method | LoRA with 4-bit quantization (QLoRA-style training) |
| Framework | PyTorch, Transformers, PEFT |
| Training platform | Google Colab |
| GPU | NVIDIA Tesla T4 |
| Task | Three-class claim–evidence classification |
| Model output | Classification label |

The original base-model parameters were kept frozen, while LoRA adapters were trained.

## 3. Classification Labels

**supported:** The supplied evidence establishes the claim.

**contradicted:** The supplied evidence directly refutes the claim.

**insufficient_evidence:** The evidence does not establish or directly refute the claim.

An important principle is that a scientifically false claim is not automatically classified as contradicted. The supplied evidence itself must establish the contradiction.

## 4. Training Dataset

The experiment used 120 synthetic, source-informed genetic research claim–evidence pairs.

The examples were manually reviewed for evidence-label consistency.

| Dataset | Records |
|---|---:|
| Training | 96 |
| Held-out validation | 24 |
| Total | 120 |

The training and validation sets were separated using concept group identifiers, with zero overlapping group IDs.

The dataset contains examples involving APOE, Alzheimer's disease genetics, gene locations, genetic risk, and inheritance.

Human review of classifications does not imply that every paraphrased scientific source was independently verified.

## 5. LoRA Configuration

| Parameter | Value |
|---|---|
| LoRA rank | 8 |
| LoRA alpha | 16 |
| LoRA dropout | 0.05 |
| Target modules | q_proj, k_proj, v_proj, o_proj |
| Trainable parameters | 3,211,264 |
| Trainable parameter percentage | 0.1863% |
| Epochs | 3 |
| Batch size | 2 |
| Gradient accumulation steps | 4 |
| Learning rate | 0.0001 |
| Optimizer steps | 36 |

Training was performed on label-completion tokens, with prompt tokens excluded from the loss.

## 6. Evaluation Method

The original and fine-tuned models were evaluated against the same 24 held-out validation examples.

Both evaluations used the same classification prompt and candidate-label log-likelihood scoring method.

Metrics included accuracy, precision, recall, F1 score, and confusion matrices.

## 7. Results

| Metric | Original model | Fine-tuned model |
|---|---:|---:|
| Accuracy | 91.67% | 100.00% |
| Correct predictions | 22/24 | 24/24 |
| Macro F1 | Approximately 0.92 | 1.00 |

The measured validation accuracy improvement was 8.33 percentage points.

The fine-tuned model corrected two errors:

- GSA-003: contradicted → insufficient_evidence
- GSA-009: contradicted → insufficient_evidence

No previously correct predictions became incorrect in this evaluation.

## 8. Training Loss

| Epoch | Average training loss |
|---|---:|
| 1 | 0.3875 |
| 2 | 0.0275 |
| 3 | 0.0812 |

The training completed successfully. The increase in average training loss during the final epoch does not, by itself, establish overfitting.

## 9. Intended Use

This model is an educational research experiment intended to explore:

- Evidence-grounded classification
- Fine-tuning small language models
- Distinguishing contradiction from insufficient evidence
- Human review and AI evaluation
- Before-and-after performance measurement

## 10. Limitations

- Only 96 examples were used for training.
- Evaluation used 24 held-out examples.
- The dataset is synthetic and source-informed.
- Some source passages have not been independently verified against their original publications.
- Related examples may share patterns beyond their recorded group IDs.
- The same validation set was used to compare the original and fine-tuned models.
- No independent external test set was used.
- A 100% validation score does not establish perfect generalization.
- The model has not been validated for clinical use.

This model should not be used for medical diagnosis, treatment recommendations, or clinical decision-making.

## 11. Future Improvements

Future work includes:

- Testing on independently collected research passages
- Expanding the dataset with more challenging claim–evidence relationships
- Verifying source passages against authoritative publications
- Evaluating robustness to paraphrasing and ambiguous evidence
- Measuring performance across additional genetic research topics
- Comparing multiple training configurations and random seeds

## 12. Model Availability

The trained LoRA adapter was saved and retained separately from this public repository.

The GitHub repository contains the training notebook, dataset splits, and evaluation artifacts. The adapter weights are not published here.

## 13. Conclusion

This experiment demonstrated improved evidence-classification accuracy on a small held-out validation set after LoRA fine-tuning.

The main improvement was correcting cases where the original model confused insufficient evidence with direct contradiction.

The findings support further experimentation but do not establish production or clinical readiness.
