# Training the Classifier

The defect classifier is a RandomForest over hand-crafted image features.
Training runs entirely offline on CPU.

## Requirements

```bash
pip install scikit-learn opencv-python-headless
```

## Steps

### 1. Get the dataset

```bash
python scripts/fetch_dataset.py --out /tmp/dataset/stackexchange
```

### 2. Train

```bash
python scripts/train_classifier.py \
  --data /tmp/dataset/stackexchange \
  --augment --trees 300
```

`--augment` augments minority classes (flip, small rotation, brightness) to
balance the dataset. The model is saved to `models/defect_classifier.pkl`
(gitignored) along with the category list.

### 3. Use it

Diagnosis automatically picks up the model:

```bash
print-doctor diagnose photo.jpg
```

If the model is missing, diagnosis falls back to traditional CV detectors.

## What it learns

Features per image:

1. **Gradient orientation histogram** (hand-rolled HOG) — 8×8 grid of 9-bin
   orientation histograms over gradients, block-normalized. Captures edges and
   layer-line texture.
2. **HSV color histograms** — 3 × 32 bins. Captures material color and lighting.
3. **Gray-level stats** — mean, std, Laplacian variance.

## Measured performance

Honest numbers from 5-fold cross-validation (strict top-1, where the single
best prediction must match the label):

| Metric | Value |
|---|---|
| Healthy vs defect | ~100% accuracy, 0% false positives |
| Which-defect, unaugmented | ~0.30 top-1 |
| Which-defect, augmented | ~0.50 top-1 |
| Dataset size | 815 images, 7 classes (weak labels) |

!!! warning
    Labels are derived from forum post text and are *not verified against each
    image* — a significant share are noisy. `scripts/audit_dataset.py` outputs
    a CSV of suspect samples for human review. Treat the defect type prediction
    as a ranked candidate, not ground truth.

## Improving accuracy

- **More data** — especially cleaner labels (verify images match their class).
- **Camera-matched data** — photos from your setup for transfer.
- **Retrain periodically** as the dataset grows.
