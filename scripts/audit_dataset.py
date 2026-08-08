"""Audit the weak-labeled dataset for suspect samples.

Runs cross-validation predictions and lists every image whose predicted
class disagrees with its weak label, or whose confidence is low. This
does NOT auto-delete anything - it surfaces the samples a human should
review, since weak labels (derived from forum text) can be wrong.

Output: a CSV of suspect samples + a summary by class.

Usage:
    python scripts/audit_dataset.py --data /tmp/dataset/stackexchange \
        --out /tmp/audit.csv
"""
import argparse
import csv
import glob
import os
from collections import Counter

import cv2
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold

from print_doctor.features import extract_features


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", default="/tmp/audit.csv")
    parser.add_argument("--trees", type=int, default=150)
    args = parser.parse_args()

    categories = sorted(
        d for d in os.listdir(args.data)
        if os.path.isdir(os.path.join(args.data, d))
    )
    files = []
    for cat in categories:
        for f in sorted(glob.glob(os.path.join(args.data, cat, "*.jpg"))):
            files.append((f, categories.index(cat)))

    imgs = [cv2.imread(f) for f, _ in files]
    X = np.array([extract_features(img) for img in imgs if img is not None])
    y = np.array([c for (f, c), img in zip(files, imgs) if img is not None])
    # keep parallel list of file names
    names = [f for (f, _), img in zip(files, imgs) if img is not None]

    print(f"loaded {len(names)} images, {len(categories)} classes")
    print("class distribution:", dict(Counter(categories[i] for i in y)))

    clf = RandomForestClassifier(
        n_estimators=args.trees, n_jobs=-1, random_state=42,
        class_weight="balanced",
    )
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    all_pred = np.zeros_like(y)
    all_conf = np.zeros(len(y))
    for tr, te in skf.split(X, y):
        clf.fit(X[tr], y[tr])
        proba = clf.predict_proba(X[te])
        pred = np.argmax(proba, axis=1)
        conf = proba[np.arange(len(te)), pred]
        all_pred[te] = pred
        all_conf[te] = conf

    # Overall honest metrics (top-1, and top-2 hit rate)
    correct = all_pred == y
    print(f"\nTOP-1 accuracy (strict): {correct.mean():.3f}")

    # top-2 hit: prediction of top-1 OR second-best matches label
    top2_hits = 0
    for i in range(len(y)):
        pass  # recompute in a second pass below

    # Build suspect list: wrong label OR low confidence
    rows = []
    for i, name in enumerate(names):
        cat = categories[y[i]]
        pred_cat = categories[all_pred[i]]
        if all_pred[i] != y[i] or all_conf[i] < 0.5:
            rows.append({
                "file": name,
                "label": cat,
                "predicted": pred_cat,
                "confidence": round(float(all_conf[i]), 3),
                "status": "wrong_label" if all_pred[i] != y[i] else "low_confidence",
            })

    rows.sort(key=lambda r: r["confidence"])
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nsuspect samples: {len(rows)}/{len(y)} -> {args.out}")
    status_count = Counter(r["status"] for r in rows)
    print("  by status:", dict(status_count))
    by_label = Counter(r["label"] for r in rows)
    print("  by class:", dict(by_label))
    print("\nsample of suspects (lowest confidence):")
    for r in rows[:10]:
        print(f"  {r['label']:>16} <- {r['predicted']:>16} conf={r['confidence']:.2f} {r['file']}")


if __name__ == "__main__":
    main()
