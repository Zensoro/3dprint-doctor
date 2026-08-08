# Defect Diagnosis

The `diagnose` command classifies a printed part's defects from photos, then
explains the root causes and what to change.

## Two-tier model

Diagnosis is deliberately two-tier:

1. **Healthy vs defective** — reliable (~100% accuracy, 0% false positives on
   healthy prints).
2. **Which defect** — a 6-class classifier, still prototype-grade: strict
   top-1 accuracy ~0.3 (unaugmented) / ~0.5 (augmented) on weak-labeled data.

The classifier is a RandomForest over hand-crafted features:

- **Gradient orientation histogram** (HOG) — captures edges and the periodic
  layer-line texture that distinguishes defects.
- **HSV color histograms** — captures material and lighting.
- **Gray-level statistics** — mean, std, Laplacian variance.

## Detected defect classes

| Class | Evidence used |
|---|---|
| `stringing` | thin high-aspect components on the surface |
| `warping` | bottom-right corner shadow (lifted edge) |
| `layer_shift` | row-intensity jumps (displaced layer band) |
| `under_extrusion` | scattered small dark pits |
| `over_extrusion` | scattered bright blobs |
| `first_layer` | interrupted bottom-edge fill |

## Root-cause attribution

A rule-based engine combines detected defects with optional parameter hints
(material, temperature, retraction) to rank likely causes, each with a concrete
fix:

```
1. Retraction distance too low (0.90)
   Fix: increase retraction 0.5-1.0 mm
2. Nozzle temperature too high (0.90)
   Fix: lower nozzle temperature 5-10 C
```

## Honest limits

- The classifier is trained on **weak labels** (StackExchange posts whose text
  mentions a defect). Images may not perfectly match their label.
- Photos from a different camera/lighting than the training set may degrade
  accuracy. Retrain on data similar to your setup for best results.
- Classification is a ranked *candidate* list, not ground truth — combine with
  the root-cause suggestions.

## Traditional CV fallback

Before the ML model existed, diagnosis used traditional OpenCV detectors. These
are kept as a `--cv` fallback for environments without a trained model, but they
do not generalize to arbitrary real photos and are not the recommended path.

## See also

- [Dataset](dataset.md) — where the training data comes from
- [Training](training.md) — reproduce the classifier
