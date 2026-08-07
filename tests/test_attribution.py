import pytest
from print_doctor.models import Defect, DefectType, RootCause
from print_doctor.attribution import attribute_causes


def _defect(t: DefectType, confidence=0.8) -> Defect:
    return Defect(type=t, confidence=confidence, evidence="test evidence")


def test_stringing_maps_to_retraction():
    causes = attribute_causes([_defect(DefectType.STRINGING)])
    assert any("retraction" in c.cause.lower() for c in causes)
    assert any(c.fix for c in causes)


def test_first_layer_maps_to_adhesion():
    causes = attribute_causes([_defect(DefectType.FIRST_LAYER_FAILURE)])
    assert any("adhesion" in c.cause.lower() for c in causes)


def test_under_extrusion_maps_to_flow():
    causes = attribute_causes([_defect(DefectType.UNDER_EXTRUSION)])
    assert any("flow" in c.cause.lower() for c in causes)


def test_ranking_by_confidence():
    causes = attribute_causes([
        _defect(DefectType.STRINGING, 0.9),
        _defect(DefectType.WARPING, 0.3),
    ])
    assert causes[0].likelihood >= causes[-1].likelihood


def test_hints_lower_likelihood():
    base = attribute_causes([_defect(DefectType.STRINGING)])
    hinted = attribute_causes(
        [_defect(DefectType.STRINGING)], hints={"temperature": "low"}
    )
    base_temp = next(c for c in base if "temperature" in c.cause.lower())
    hinted_temp = next(c for c in hinted if "temperature" in c.cause.lower())
    assert hinted_temp.likelihood <= base_temp.likelihood


def test_empty_defects_gives_empty_causes():
    assert attribute_causes([]) == []
