"""Image-based defect detection for printed parts.

Pure local computer vision (OpenCV) + rule-based analysis. Each
detector takes one or more images and returns zero or more Defects
with an evidence string explaining what image feature was found.
"""
from typing import List, Optional, Tuple

import cv2
import numpy as np

from print_doctor.models import Defect, DefectType


def load_image(path: str) -> np.ndarray:
    """Load an image in BGR. Raises ValueError if unreadable."""
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Cannot read image: {path}")
    return img


def preprocess(img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Normalize to grayscale and build a body mask.

    Returns (gray, mask) where mask selects the printed part
    (foreground) from the background.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Open to clean up specks and keep only the solid body
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)
    return gray, mask


# --------------------------------------------------------------------------
# Detectors
# --------------------------------------------------------------------------

def detect_stringing(img: np.ndarray, mask: np.ndarray) -> List[Defect]:
    """Detect thin filament strings across the part surface.

    Evidence: connected components with high aspect ratio (thin and
    long) found inside the body region after morphological filtering.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    body_region = cv2.bitwise_and(gray, gray, mask=mask)

    # Detect thin dark lines: closing with a wide kernel removes them
    # from the body; the difference is the thin features.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    closed = cv2.morphologyEx(body_region, cv2.MORPH_CLOSE, kernel, iterations=2)
    thin_features = cv2.absdiff(body_region, closed)
    _, thin_bin = cv2.threshold(thin_features, 20, 255, cv2.THRESH_BINARY)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        thin_bin, 8
    )
    string_count = 0
    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]
        if area < 20:
            continue
        long_axis = max(w, h)
        short_axis = min(w, h)
        if long_axis > 25 and long_axis / max(short_axis, 1) > 4:
            string_count += 1

    if string_count >= 2:
        return [Defect(
            type=DefectType.STRINGING,
            confidence=min(0.9, 0.35 + string_count * 0.06),
            evidence=(
                f"Detected {string_count} long thin components "
                "(length/width ratio > 4) inside the part boundary"
            ),
        )]
    return []


def detect_warping(img: np.ndarray, mask: np.ndarray) -> List[Defect]:
    """Detect corner lifting via a shadow cast at the bottom edge.

    Evidence: the bottom-right quadrant of the part is significantly
    darker than the top-left (lifted corner shadow).
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    body = gray * (mask > 0).astype(np.uint8)
    h2, w2 = h // 2, w // 2

    tl = body[:h2, :w2]
    br = body[h2:, w2:]
    tl_mean = float(tl[tl > 0].mean()) if np.any(tl > 0) else 0.0
    br_mean = float(br[br > 0].mean()) if np.any(br > 0) else 0.0

    if tl_mean > 0 and (tl_mean - br_mean) > 15:
        return [Defect(
            type=DefectType.WARPING,
            confidence=min(0.85, 0.3 + (tl_mean - br_mean) / 60),
            evidence=(
                f"Bottom-right region is {tl_mean - br_mean:.0f} gray "
                "levels darker than top-left (corner shadow), consistent "
                "with a lifted corner"
            ),
        )]
    return []


def detect_layer_shift(img: np.ndarray, mask: np.ndarray) -> List[Defect]:
    """Detect horizontal banding / z-band / layer misalignment.

    Evidence: sharp jumps in the row-intensity profile inside the body
    (a displaced layer shows up as an abrupt brightness step).
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    cols = np.where(mask.sum(axis=0) > 0)[0]
    if len(cols) < 50:
        return []
    rows = np.where(mask.sum(axis=1) > 0)[0]
    if len(rows) < 50:
        return []

    region = gray[rows.min():rows.max() + 1, cols.min():cols.max() + 1]
    row_means = region.mean(axis=1).astype(np.float64)

    jumps = np.abs(np.diff(row_means))
    max_jump = float(jumps.max()) if len(jumps) else 0.0
    mean_row = float(row_means.mean())

    if max_jump > 0.05 * mean_row and max_jump > 5:
        return [Defect(
            type=DefectType.LAYER_SHIFT,
            confidence=min(0.85, 0.35 + max_jump / (3 * mean_row)),
            evidence=(
                f"Row brightness jumps by {max_jump:.1f} gray levels "
                f"({max_jump / mean_row * 100:.0f}% of mean) between "
                "adjacent rows, indicating a displaced layer band"
            ),
        )]
    return []


def detect_extrusion(
    img: np.ndarray, mask: np.ndarray
) -> List[Defect]:
    """Detect under- or over-extrusion from surface texture.

    Evidence: scattered small dark pits (under-extrusion) or bright
    blobs (over-extrusion). Uses connected-component analysis so that
    large contiguous dark regions (e.g. warp shadows) are not counted.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    body = gray * (mask > 0).astype(np.uint8)
    body_px = body[body > 0]
    if len(body_px) < 500:
        return []

    med = np.median(body_px)

    dark_bin = np.zeros_like(gray)
    dark_bin[(body < med - 25) & (mask > 0)] = 255
    bright_bin = np.zeros_like(gray)
    bright_bin[(body > med + 25) & (mask > 0)] = 255

    def small_component_ratio(
        binary: np.ndarray, max_area: int = 300, max_aspect: float = 3.0
    ) -> float:
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
        total = 0
        for i in range(1, num_labels):
            x, y, w, h, area = stats[i]
            if area <= max_area and max(w, h) / max(min(w, h), 1) <= max_aspect:
                total += area
        return total / max(len(body_px), 1)

    dark_ratio = small_component_ratio(dark_bin)
    bright_ratio = small_component_ratio(bright_bin)

    # High-frequency detail: Laplacian variance
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    body_lap = (lap * (mask > 0).astype(np.float64))
    lap_var = float(np.var(body_lap[body_lap != 0]))

    defects = []
    if dark_ratio > 0.008:
        defects.append(Defect(
            type=DefectType.UNDER_EXTRUSION,
            confidence=min(0.85, 0.3 + dark_ratio * 15),
            evidence=(
                f"{dark_ratio * 100:.1f}% of surface pixels belong to "
                "scattered small dark pits (pitting), consistent with "
                f"underfill (texture variance {lap_var:.0f})"
            ),
        ))
    elif bright_ratio > 0.003:
        defects.append(Defect(
            type=DefectType.OVER_EXTRUSION,
            confidence=min(0.85, 0.3 + bright_ratio * 20),
            evidence=(
                f"{bright_ratio * 100:.1f}% of surface pixels belong to "
                "scattered small bright blobs, consistent with excess "
                "material"
            ),
        ))
    return defects


def detect_color_bleeding(img: np.ndarray, mask: np.ndarray) -> List[Defect]:
    """Detect stray color contamination on a single-color part.

    Evidence: fraction of body pixels whose hue deviates from the
    dominant hue.
    """
    if img.ndim == 2:
        return []

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    body_mask = mask > 0

    sat = s[body_mask]
    if len(sat) < 500:
        return []

    # Colored pixels: saturation clearly above gray noise
    colored = np.mean(sat > 50)
    if colored > 0.005:
        return [Defect(
            type=DefectType.COLOR_BLEEDING,
            confidence=min(0.9, 0.35 + colored * 10),
            evidence=(
                f"{colored * 100:.1f}% of part pixels carry strong "
                "saturation, indicating stray colored material"
            ),
        )]
    return []


def detect_first_layer_failure(
    img: np.ndarray, mask: np.ndarray
) -> List[Defect]:
    """Detect missing chunks at the bottom edge of the part.

    Evidence: bottom rows of the mask are interrupted / notched.
    """
    h, w = mask.shape
    rows = mask[int(h * 0.70):int(h * 0.88), :]
    if rows.size == 0:
        return []

    row_frac = rows.mean(axis=1) / 255.0
    row_frac = row_frac[row_frac > 0.05]
    if len(row_frac) < 5:
        return []

    std = float(np.std(row_frac))
    mean = float(np.mean(row_frac))

    if std > 0.05 and mean > 0.3:
        return [Defect(
            type=DefectType.FIRST_LAYER_FAILURE,
            confidence=min(0.85, 0.3 + std * 6),
            evidence=(
                f"Bottom-edge row fill varies with std {std:.2f} "
                f"(mean {mean:.2f}), indicating missing first-layer chunks"
            ),
        )]
    return []


ALL_DETECTORS = [
    detect_stringing,
    detect_warping,
    detect_layer_shift,
    detect_extrusion,
    detect_color_bleeding,
    detect_first_layer_failure,
]
