# GeneScopeAI Fine-Tuning Dataset

This folder contains the training and validation data used in the GeneScopeAI LoRA fine-tuning experiment.

- `GeneScopeAI_train.csv`: 96 training examples
- `GeneScopeAI_validation.csv`: 24 held-out validation examples

The full dataset contains 120 synthetic, source-informed claim–evidence pairs, reviewed for classification consistency.

Each example has one of three labels:

- `supported`
- `contradicted`
- `insufficient_evidence`

The split was performed using `group_id` to keep examples from the same research concept together. There are no shared group IDs between training and validation.

The validation set was used for before-and-after model comparison. It was not used for gradient updates.

**Limitations:** The dataset is small and synthetic. Human review of classification labels does not necessarily mean every scientific source passage was independently verified. Results should not be interpreted as clinical validation.
