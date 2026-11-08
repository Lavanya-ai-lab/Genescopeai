# GeneScopeAI — Fine-Tuning Evaluation Results

## Objective

Evaluate whether LoRA fine-tuning improves Qwen3-1.7B-Base's ability to classify genetic research claims using only the supplied evidence.

## Experimental Setup

| Parameter | Value |
|---|---|
| Base model | Qwen/Qwen3-1.7B-Base |
| Fine-tuning method | 4-bit LoRA (QLoRA) |
| Dataset | 120 synthetic, source-informed examples |
| Training set | 96 examples |
| Validation set | 24 examples |
| Shared concept groups | 0 |
| Training epochs | 3 |
| Optimizer steps | 36 |

## Before and After Fine-Tuning

| Metric | Baseline | Fine-tuned |
|---|---:|---:|
| Accuracy | 91.67% | 100.00% |
| Correct predictions | 22/24 | 24/24 |
| Macro F1 score | Approximately 0.92 | 1.00 |

**Accuracy improvement: +8.33 percentage points.**

## Error Analysis

The original model made two classification errors:

| Record | Actual | Baseline prediction | Fine-tuned prediction |
|---|---|---|---|
| GSA-003 | insufficient_evidence | contradicted | insufficient_evidence |
| GSA-009 | insufficient_evidence | contradicted | insufficient_evidence |

Both errors were corrected after fine-tuning, with no new errors on the 24-example validation set.

These errors highlight an important distinction: a claim can be scientifically false without being directly contradicted by the supplied evidence.

## Training Loss

| Epoch | Average training loss |
|---|---:|
| 1 | 0.3875 |
| 2 | 0.0275 |
| 3 | 0.0812 |

Training loss decreased substantially overall, although it increased in the third epoch. Validation results are necessary to assess performance beyond the training data.

## Limitations

- The validation set contains only 24 examples.
- The dataset is synthetic and source-informed.
- The split prevents overlap in recorded concept groups, but this does not eliminate every possible similarity between examples.
- The same validation set was evaluated before and after fine-tuning.
- An independent external test set is still needed to assess generalization.
- These results do not establish clinical reliability or suitability for medical decision-making.

## Conclusion

Fine-tuning improved accuracy from 91.67% to 100% on the held-out validation set and corrected two cases where the original model confused insufficient evidence with contradiction.

The findings are encouraging but require confirmation on larger, independently constructed datasets.
## LoRA Merge and Smoke Test

The trained GeneScopeAI LoRA adapter was successfully merged into the original Qwen3-1.7B-Base model using PEFT's `merge_and_unload()` method.

The merged model was loaded on a Tesla T4 GPU and tested against five held-out validation examples.

**Smoke Test Results:**
- Total examples tested: 5
- Correct predictions: 5
- Incorrect predictions: 0
- Smoke-test accuracy: 100%

The smoke test confirmed that the merged model could perform inference and correctly classify all five selected examples.

**Evidence:** `GeneScopeAI_merge_smoke_test.csv`

**Limitation:** This is a small smoke test, not an independent assessment of generalization. The original fine-tuned model's 24-example validation accuracy was measured separately.

## Full Merged-Model Validation Results

After successfully merging the trained LoRA adapter into Qwen3-1.7B-Base using PEFT's `merge_and_unload()`, I evaluated the merged model against the full 24-example held-out validation set.

### Results

| Metric | Result |
|---|---|
| Total validation examples | 24 |
| Correct predictions | 24 |
| Incorrect predictions | 0 |
| Accuracy | 100.00% |
| Macro precision | 1.00 |
| Macro recall | 1.00 |
| Macro F1 | 1.00 |

All three categories—supported, contradicted, and insufficient_evidence—achieved precision, recall, and F1 scores of 1.00, with eight validation examples per category.

### Before-and-After Comparison

| Model | Accuracy |
|---|---|
| Original Qwen3-1.7B-Base | 91.67% |
| Fine-tuned Qwen with LoRA | 100.00% |
| Merged fine-tuned Qwen | 100.00% |

The merged model preserved the fine-tuned model's observed classification performance on this validation set.

### Evidence

- `GeneScopeAI_merge_smoke_test.csv`
- `GeneScopeAI_merged_validation_predictions.csv`
- `GeneScopeAI_merged_confusion_matrix.png`

### Limitations

These results come from a small, synthetic, source-informed dataset. Although the validation examples were separated from training by concept group, the results do not establish generalization to independently collected research passages or clinical use.
