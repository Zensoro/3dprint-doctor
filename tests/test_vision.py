"""Tests for vision defect detectors using synthetic fixtures."""
import cv2
from pathlib import Path
from print_doctor.models import DefectType
from print_doctor.vision import (
    load_image,
    preprocess,
    detect_stringing,
    detect_warping,
    detect_layer_shift,
    detect_extrusion,
    detect_color_bleeding,
    detect_first_layer_failure,
)

FIXTURES = Path(__file__).parent / "fixtures" / "diagnose"


def _load(name: str):
    img = load_image(str(FIXTURES / f"{name}.jpg"))
    gray, mask = preprocess(img)
    return img, mask


def _types(defects):
    return {d.type for d in defects}


def test_stringing_detected():
    img, mask = _load("stringing")
    defects = detect_stringing(img, mask)
    assert DefectType.STRINGING in _types(defects)
    assert defects[0].evidence


def test_warping_detected():
    img, mask = _load("warping")
    defects = detect_warping(img, mask)
    assert DefectType.WARPING in _types(defects)


def test_layer_shift_detected():
    img, mask = _load("layer_shift")
    defects = detect_layer_shift(img, mask)
    assert DefectType.LAYER_SHIFT in _types(defects)


def test_under_extrusion_detected():
    img, mask = _load("under_extrusion")
    defects = detect_extrusion(img, mask)
    assert DefectType.UNDER_EXTRUSION in _types(defects)


def test_over_extrusion_detected():
    img, mask = _load("over_extrusion")
    defects = detect_extrusion(img, mask)
    assert DefectType.OVER_EXTRUSION in _types(defects)


def test_color_bleeding_detected():
    img, mask = _load("color_bleeding")
    defects = detect_color_bleeding(img, mask)
    assert DefectType.COLOR_BLEEDING in _types(defects)


def test_first_layer_failure_detected():
    img, mask = _load("first_layer_failure")
    defects = detect_first_layer_failure(img, mask)
    assert DefectType.FIRST_LAYER_FAILURE in _types(defects)


def test_normal_image_clean():
    """A normal print should trigger few or no detectors."""
    img, mask = _load("normal")
    all_detected = set()
    all_detected |= _types(detect_stringing(img, mask))
    all_detected |= _types(detect_warping(img, mask))
    all_detected |= _types(detect_layer_shift(img, mask))
    all_detected |= _types(detect_extrusion(img, mask))
    all_detected |= _types(detect_color_bleeding(img, mask))
    all_detected |= _types(detect_first_layer_failure(img, mask))
    assert len(all_detected) <= 1  # allow at most one borderline hit
