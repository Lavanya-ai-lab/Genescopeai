# GeneScopeAI — Evidence Classification Fine-Tuning

## Overview

This project explores whether LoRA fine-tuning improves Qwen3-1.7B-Base's ability to classify genetic research claims against supplied evidence.

## Classification Labels

- **supported:** The evidence establishes the claim.
- **contradicted:** The evidence directly refutes the claim.
- **insufficient_evidence:** The evidence neither establishes nor directly refutes the claim.

## Experiment

- Base model: Qwen/Qwen3-1.7B-Base
- Fine-tuning method: 4-bit LoRA (QLoRA)
- Dataset: 120 human-reviewed, synthetic source-informed claim–evidence examples
- Training set: 96 examples
- Validation set: 24 examples
- Shared concept groups between sets: 0
- Training epochs: 3

## Results

| Metric | Original Qwen | Fine-tuned Qwen |
|---|---:|---:|
| Validation accuracy | 91.67% | 100.00% |
| Correct classifications | 22/24 | 24/24 |

The fine-tuned model corrected two cases where the original model classified insufficient evidence as contradiction.

## Limitations

These results are from a small, source-informed synthetic validation dataset. They do not establish performance on independent real-world research evidence or clinical suitability. Scientific-source verification is distinct from review of the claim–evidence labels.

This project is educational and is not intended for medical diagnosis or clinical decision-making.

Additional methodology, reproducibility instructions, and evaluation artifacts will be documented here.
