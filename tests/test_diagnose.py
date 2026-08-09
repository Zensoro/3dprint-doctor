from pathlib import Path
from print_doctor.models import DefectType
from print_doctor.diagnose import diagnose_photos, generate_diagnosis_report

FIXTURES = Path(__file__).parent / "fixtures" / "diagnose"


def test_diagnose_stringing_photo_cv():
    """CV detectors still detect stringing on synthetic fixtures."""
    d = diagnose_photos([str(FIXTURES / "stringing.jpg")], use_ml=False)
    assert any(dd.type == DefectType.STRINGING for dd in d.defects)
    assert d.root_causes
    assert d.image_count == 1


def test_diagnose_clean_photo_cv():
    """A normal synthetic print triggers few CV detectors."""
    d = diagnose_photos([str(FIXTURES / "normal.jpg")], use_ml=False)
    assert len(d.defects) <= 1


def test_diagnose_multiple_photos_merged_cv():
    d = diagnose_photos([
        str(FIXTURES / "stringing.jpg"),
        str(FIXTURES / "warping.jpg"),
    ], use_ml=False)
    types = {dd.type for dd in d.defects}
    assert DefectType.STRINGING in types
    assert DefectType.WARPING in types


def test_diagnosis_report_content_cv():
    d = diagnose_photos([str(FIXTURES / "first_layer_failure.jpg")], use_ml=False)
    report = generate_diagnosis_report(d)
    assert "first_layer_failure" in report
    assert "Likely Root Causes" in report
    assert "Fix:" in report


def test_diagnose_with_hints():
    d = diagnose_photos(
        [str(FIXTURES / "stringing.jpg")], hints={"temperature": "210"},
        use_ml=False,
    )
    assert d.root_causes
    assert all(rc.likelihood <= 1.0 for rc in d.root_causes)


def test_diagnose_missing_file_raises():
    import pytest
    from print_doctor.vision import load_image
    with pytest.raises(ValueError):
        load_image("/nonexistent/photo.jpg")


def test_ml_path_absent_model_falls_back():
    """If the ML model file is missing, diagnose still works (CV fallback)."""
    import print_doctor.vision_ml as vm

    orig = vm.MODEL_PATH
    vm.MODEL_PATH = Path("/nonexistent/model.pkl")
    try:
        d = diagnose_photos([str(FIXTURES / "stringing.jpg")], use_ml=True)
        # Either ML path failed silently -> CV fallback produced defects,
        # or model somehow loaded. Either way it must not crash.
        assert d.image_count == 1
    finally:
        vm.MODEL_PATH = orig


def test_diagnose_includes_regions():
    """Diagnosis includes anomaly region localization."""
    d = diagnose_photos([str(FIXTURES / "stringing.jpg")], use_ml=False)
    # localization runs regardless of defects
    assert hasattr(d, "regions")
    report = generate_diagnosis_report(d)
    assert "Anomaly Regions" in report
