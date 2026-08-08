"""Hand-crafted image features for print-defect classification.

Feature vector = gradient orientation histogram (shape/texture) +
HSV color histograms + gray-level statistics. Used both by the
training script and the runtime classifier.
"""
import cv2
import numpy as np

IMG_SIZE = 128


def _hog_features(gray: np.ndarray) -> np.ndarray:
    """Gradient orientation histogram over a grid (hand-rolled HOG).

    Computes gradient magnitude and orientation per pixel, then builds
    a histogram of orientation bins per cell. Captures edges and the
    periodic layer-line texture that distinguishes defects.
    """
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)
    ang = np.degrees(np.arctan2(gy, gx)) % 180

    cell = 16
    bins = 9
    n_cells = IMG_SIZE // cell
    hist = np.zeros((n_cells, n_cells, bins))
    bin_width = 180.0 / bins
    for i in range(n_cells):
        for j in range(n_cells):
            m = mag[i * cell:(i + 1) * cell, j * cell:(j + 1) * cell]
            a = ang[i * cell:(i + 1) * cell, j * cell:(j + 1) * cell]
            b = (a / bin_width).astype(int) % bins
            np.add.at(hist[i, j], b.ravel(), m.ravel())
    eps = 1e-6
    h = hist.reshape(n_cells, n_cells, bins)
    for i in range(n_cells - 1):
        for j in range(n_cells - 1):
            block = h[i:i + 2, j:j + 2]
            norm = np.sqrt(block.sum() ** 2 + eps)
            h[i:i + 2, j:j + 2] = block / norm
    return hist.ravel()


def extract_features(img: np.ndarray) -> np.ndarray:
    """Extract a compact feature vector from an image.

    Combines gradient orientation histogram (shape/texture), HSV color
    histograms and simple gray-level statistics into one vector.
    """
    img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    hog_feat = _hog_features(gray)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    color_feat = []
    for channel in range(3):
        hist = cv2.calcHist([hsv], [channel], None, [32], [0, 256])
        hist = cv2.normalize(hist, hist).ravel()
        color_feat.append(hist)
    color_feat = np.concatenate(color_feat)

    stats = np.array([
        gray.mean(), gray.std(),
        cv2.Laplacian(gray, cv2.CV_64F).var(),
    ]) / 255.0

    return np.concatenate([hog_feat, color_feat, stats])


def augment_image(img: np.ndarray) -> list:
    """Return augmented variants (flip, small rotation, brightness)."""
    variants = [img]
    variants.append(cv2.flip(img, 1))
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), 5, 1.0)
    variants.append(cv2.warpAffine(img, m, (w, h)))
    for factor in [0.9, 1.1]:
        variants.append(cv2.convertScaleAbs(img, alpha=factor, beta=0))
    return variants
