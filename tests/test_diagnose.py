from pathlib import Path
from print_doctor.models import DefectType
from print_doctor.diagnose import diagnose_photos, generate_diagnosis_report

FIXTURES = Path(__file__).parent / "fixtures" / "diagnose"


def test_diagnose_stringing_photo():
    d = diagnose_photos([str(FIXTURES / "stringing.jpg")])
    assert any(dd.type == DefectType.STRINGING for dd in d.defects)
    assert d.root_causes
    assert d.image_count == 1


def test_diagnose_clean_photo():
    d = diagnose_photos([str(FIXTURES / "normal.jpg")])
    assert len(d.defects) <= 1


def test_diagnose_multiple_photos_merged():
    d = diagnose_photos([
        str(FIXTURES / "stringing.jpg"),
        str(FIXTURES / "warping.jpg"),
    ])
    types = {dd.type for dd in d.defects}
    assert DefectType.STRINGING in types
    assert DefectType.WARPING in types


def test_diagnosis_report_content():
    d = diagnose_photos([str(FIXTURES / "first_layer_failure.jpg")])
    report = generate_diagnosis_report(d)
    assert "first_layer_failure" in report
    assert "Likely Root Causes" in report
    assert "Fix:" in report


def test_diagnose_with_hints():
    d = diagnose_photos(
        [str(FIXTURES / "stringing.jpg")], hints={"temperature": "210"}
    )
    assert d.root_causes
    assert all(rc.likelihood <= 1.0 for rc in d.root_causes)


def test_diagnose_missing_file_raises():
    import pytest
    from print_doctor.vision import load_image
    with pytest.raises(ValueError):
        load_image("/nonexistent/photo.jpg")
