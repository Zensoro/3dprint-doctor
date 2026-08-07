"""Generate synthetic printed-part photos with known defects.

Each fixture is a 640x480 grayscale-ish image of a fake printed part
(a rounded rectangle body) with one injected defect. These let the
diagnose detectors be tested with known ground truth.

Usage:
    python tests/generate_diagnose_fixtures.py
"""
import numpy as np
import cv2
from pathlib import Path

IMG_W, IMG_H = 640, 480
BODY_COLOR = 180      # mid-gray plastic
BG_COLOR = 55         # darker background
NOISE = 2.0


def _canvas() -> np.ndarray:
    img = np.full((IMG_H, IMG_W), BG_COLOR, dtype=np.uint8)
    img = img.astype(np.float32) + np.random.normal(0, NOISE, img.shape)
    return img


def _draw_body(img: np.ndarray) -> np.ndarray:
    """Draw a rounded-rect printed part occupying most of the frame."""
    x0, y0, x1, y1 = 120, 80, 520, 400
    mask = np.zeros((IMG_H, IMG_W), dtype=np.uint8)
    cv2.rectangle(mask, (x0, y0), (x1, y1), 255, -1)
    mask = cv2.GaussianBlur(mask, (0, 0), 1.5)
    body_mask = mask > 127
    img[body_mask] = BODY_COLOR  # overwrite, not add (avoid overflow)
    # subtle shading to fake lighting
    yy, xx = np.mgrid[0:IMG_H, 0:IMG_W]
    shading = 8.0 * (yy / IMG_H - 0.5)
    img[body_mask] += shading[body_mask]
    return img


def normal() -> np.ndarray:
    img = _canvas()
    img = _draw_body(img)
    return np.clip(img, 0, 255).astype(np.uint8)


def stringing() -> np.ndarray:
    img = _canvas()
    img = _draw_body(img)
    # random thin dark strings across the body
    rng = np.random.default_rng(7)
    for _ in range(20):
        y = rng.integers(100, 380)
        x = rng.integers(140, 500)
        length = rng.integers(50, 140)
        angle = rng.uniform(-0.3, 0.3)
        dx, dy = length * np.cos(angle), length * np.sin(angle)
        x0, y0 = int(x - dx / 2), int(y - dy / 2)
        x1, y1 = int(x + dx / 2), int(y + dy / 2)
        cv2.line(img, (x0, y0), (x1, y1), BODY_COLOR - 35, 1)
    return np.clip(img, 0, 255).astype(np.uint8)


def warping() -> np.ndarray:
    img = _canvas()
    img = _draw_body(img)
    # lift the bottom-right corner: strong dark shadow under the edge
    yy, xx = np.mgrid[0:IMG_H, 0:IMG_W]
    corner = np.exp(-(((xx - 470) ** 2 + (yy - 370) ** 2) / (2 * 55.0 ** 2)))
    shadow = 75.0 * corner
    img[yy > 280] -= shadow[yy > 280]
    return np.clip(img, 0, 255).astype(np.uint8)


def layer_shift() -> np.ndarray:
    img = _canvas()
    img = _draw_body(img)
    # horizontal layer lines: periodic texture
    yy, xx = np.mgrid[0:IMG_H, 0:IMG_W]
    bands = np.abs(np.sin(yy / 6.0 * np.pi)) * 12.0
    inside = (yy > 80) & (yy < 400) & (xx > 120) & (xx < 520)
    img[inside] += bands[inside]
    # a bright z-band at mid height
    mid = (yy > 215) & (yy < 245) & inside
    img[mid] += 35
    return np.clip(img, 0, 255).astype(np.uint8)


def under_extrusion() -> np.ndarray:
    img = _canvas()
    img = _draw_body(img)
    # sparse pitting: many small dark specks
    rng = np.random.default_rng(11)
    inside = np.zeros((IMG_H, IMG_W), dtype=bool)
    inside[80:400, 120:520] = True
    ys, xs = np.where(inside)
    for _ in range(4000):
        i = rng.integers(0, len(ys))
        img[ys[i] - 1:ys[i] + 1, xs[i] - 1:xs[i] + 1] -= rng.integers(20, 45)
    return np.clip(img, 0, 255).astype(np.uint8)


def over_extrusion() -> np.ndarray:
    img = _canvas()
    img = _draw_body(img)
    # blobs of excess material on the surface
    rng = np.random.default_rng(13)
    for _ in range(20):
        x = rng.integers(140, 500)
        y = rng.integers(100, 380)
        r = rng.integers(3, 9)
        cv2.circle(img, (int(x), int(y)), int(r), BODY_COLOR + 45, -1)
    return np.clip(img, 0, 255).astype(np.uint8)


def color_bleeding() -> np.ndarray:
    img = _canvas()
    img = _draw_body(img)
    # color image: base gray body with stray colored specks
    color = cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    rng = np.random.default_rng(17)
    for _ in range(120):
        x = rng.integers(140, 500)
        y = rng.integers(100, 380)
        c = tuple(int(v) for v in rng.integers(0, 255, size=3))
        cv2.circle(color, (int(x), int(y)), 3, c, -1)
    return color


def first_layer_failure() -> np.ndarray:
    img = _canvas()
    img = _draw_body(img)
    # bottom edge has missing chunks (failed first layer adhesion)
    rng = np.random.default_rng(19)
    for _ in range(16):
        x = rng.integers(130, 500)
        w = rng.integers(15, 40)
        cv2.rectangle(img, (int(x), 385), (int(x + w), 405), BG_COLOR, -1)
    return np.clip(img, 0, 255).astype(np.uint8)


def generate_all(out_dir: str = "tests/fixtures/diagnose") -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    builders = {
        "normal": normal,
        "stringing": stringing,
        "warping": warping,
        "layer_shift": layer_shift,
        "under_extrusion": under_extrusion,
        "over_extrusion": over_extrusion,
        "color_bleeding": color_bleeding,
        "first_layer_failure": first_layer_failure,
    }
    for name, builder in builders.items():
        img = builder()
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        cv2.imwrite(str(out / f"{name}.jpg"), img)
        print(f"wrote {out / name}.jpg")


if __name__ == "__main__":
    generate_all()
