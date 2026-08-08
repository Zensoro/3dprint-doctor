"""Train a lightweight print-defect classifier from real photos.

Uses hand-crafted features (HOG shape/texture + HSV color histograms)
with a scikit-learn Random Forest. Lightweight, CPU-friendly, and runs
entirely offline.

Usage:
    python scripts/train_classifier.py --data <dataset_root>
        --data points at a directory of category subfolders (jpg images):
        <root>/stringing/xxx.jpg, <root>/warping/..., etc.

Outputs:
    - trained model saved to models/defect_classifier.pkl
    - classification report + confusion matrix on a held-out test set
"""
import argparse
import glob
import os
import pickle
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split

IMG_SIZE = 128
N_CLASSES = 7


from print_doctor.features import extract_features, augment_image


def load_dataset(data_root: str):
    """Load images and labels from category subfolders.

    Returns (images, labels, categories).
    """
    images, labels, categories = [], [], []
    categories = sorted(
        d for d in os.listdir(data_root)
        if os.path.isdir(os.path.join(data_root, d))
    )
    print("categories:", categories)
    for label_idx, cat in enumerate(categories):
        files = sorted(glob.glob(os.path.join(data_root, cat, "*.jpg")))
        for f in files:
            img = cv2.imread(f)
            if img is None:
                continue
            images.append(img)
            labels.append(label_idx)
    return np.array(labels), categories


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Dataset root (category dirs)")
    parser.add_argument("--out", default="models/defect_classifier.pkl",
                        help="Output model path")
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--trees", type=int, default=300)
    parser.add_argument("--augment", action="store_true",
                        help="Augment minority classes (flip/rotate/brightness)")
    args = parser.parse_args()

    labels, categories = load_dataset(args.data)
    images = [
        cv2.imread(f)
        for f in sorted(glob.glob(os.path.join(args.data, "*", "*.jpg")))
        if cv2.imread(f) is not None
    ]
    assert len(images) == len(labels), f"{len(images)} vs {len(labels)}"
    print(f"loaded {len(images)} images across {len(categories)} classes")

    # Augment minority classes
    if args.augment:
        counts = Counter(labels)
        small = {cat for cat, c in counts.items() if c < 100}
        print("augmenting classes:", [categories[c] for c in small])
        augmented_imgs, augmented_labels = [], []
        for img, lab in zip(images, labels):
            if lab in small:
                for v in augment_image(img):
                    augmented_imgs.append(v)
                    augmented_labels.append(lab)
            else:
                augmented_imgs.append(img)
                augmented_labels.append(lab)
        images, labels = augmented_imgs, augmented_labels
        print(f"after augmentation: {len(images)} images")

    # Extract features
    print("extracting features (HOG + color + stats)...")
    X = np.array([extract_features(img) for img in images])
    y = np.array(labels)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=42, stratify=y
    )

    print(f"training RandomForest({args.trees}) on {X_train.shape}...")
    clf = RandomForestClassifier(
        n_estimators=args.trees, n_jobs=-1, random_state=42,
        class_weight="balanced",
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nTest accuracy: {acc:.3f}")
    print(classification_report(
        y_test, y_pred, target_names=categories, zero_division=0
    ))
    cm = confusion_matrix(y_test, y_pred)
    print("Confusion matrix (rows=truth, cols=pred):")
    print("        " + " ".join(f"{c[:8]:>8}" for c in categories))
    for i, row in enumerate(cm):
        print(f"{categories[i][:8]:>8} " + " ".join(f"{v:>8}" for v in row))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "wb") as f:
        pickle.dump({"model": clf, "categories": categories}, f)
    print(f"\nSaved model to {args.out}")


if __name__ == "__main__":
    main()
