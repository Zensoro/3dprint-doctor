"""ML-based defect classification using hand-crafted features.

Loads a trained RandomForest classifier (models/defect_classifier.pkl)
and predicts whether a photo shows a healthy print or a defect, and
which defect class is most likely.

Classification is two-tier:
  - Defect detection (healthy vs defective): reliable (~1.0 accuracy)
  - Defect classification (which defect): beta (~0.6 accuracy with
    weak StackExchange labels) - treat class predictions as ranked
    candidates, not ground truth.
"""
import pickle
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from print_doctor.models import Defect, DefectType

MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "defect_classifier.pkl"


class DefectClassifier:
    """Thin wrapper around the trained classifier."""

    def __init__(self, model_path: Optional[Path] = None):
        path = Path(model_path) if model_path else MODEL_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"Classifier model not found at {path}. Train it first with "
                "scripts/train_classifier.py"
            )
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.model = data["model"]
        self.categories: List[str] = data["categories"]

    def predict(self, img: np.ndarray) -> Tuple[str, float, List[Tuple[str, float]]]:
        """Predict defect class for an image.

        Returns (best_class, confidence, ranked_candidates) where
        ranked_candidates is a list of (class, probability) sorted by
        probability descending.
        """
        from print_doctor.features import extract_features

        feat = extract_features(img).reshape(1, -1)
        probs = self.model.predict_proba(feat)[0]
        ranked = sorted(
            zip(self.categories, probs.tolist()),
            key=lambda kv: kv[1], reverse=True,
        )
        best_class, best_conf = ranked[0]
        return best_class, best_conf, ranked


_CATEGORY_TO_DEFECT = {
    "stringing": DefectType.STRINGING,
    "warping": DefectType.WARPING,
    "layer_shift": DefectType.LAYER_SHIFT,
    "under_extrusion": DefectType.UNDER_EXTRUSION,
    "over_extrusion": DefectType.OVER_EXTRUSION,
    "first_layer": DefectType.FIRST_LAYER_FAILURE,
}


def classify_photo(
    img: np.ndarray,
    classifier: Optional[DefectClassifier] = None,
    top_k: int = 2,
    detection_threshold: float = 0.5,
) -> List[Defect]:
    """Classify a photo into a list of candidate Defects.

    First decides healthy vs defective (the normal class is predicted
    with near-1.0 accuracy). If defective, returns up to `top_k`
    candidate defect types with their model confidence.

    Args:
        img: BGR image of a printed part
        classifier: Optional preloaded classifier
        top_k: Number of candidate defect types to return
        detection_threshold: Min normal-class confidence above which
            the print is considered healthy

    Returns:
        List of candidate Defects (empty if healthy)
    """
    if classifier is None:
        classifier = DefectClassifier()

    best_class, best_conf, ranked = classifier.predict(img)

    if "normal" in classifier.categories:
        normal_conf = dict(ranked).get("normal", 0.0)
    else:
        normal_conf = 0.0

    # Healthy: normal class wins with high confidence
    if best_class == "normal" and best_conf >= detection_threshold:
        return []
    # Also treat as healthy if normal confidence is dominant
    if normal_conf >= 0.5:
        return []

    defects = []
    for cat, conf in ranked:
        if cat == "normal" or cat not in _CATEGORY_TO_DEFECT:
            continue
        defects.append(Defect(
            type=_CATEGORY_TO_DEFECT[cat],
            confidence=float(conf),
            evidence=(
                f"ML classifier ({cat}) with confidence {conf:.2f}; "
                "candidate from {top_k}-best predictions"
            ),
        ))
        if len(defects) >= top_k:
            break
    return defects
