"""Tests for the detector plugin system."""
import trimesh
import pytest

from print_doctor.models import Issue, Severity
from print_doctor.plugins import (
    MeshDetector,
    register_detector,
    get_registered_detectors,
    load_plugins,
    run_detectors,
)
from print_doctor.mesh import analyze_mesh, analyze_mesh_with_detectors


def test_builtin_detectors_registered():
    """All built-in detectors are in the registry."""
    import print_doctor.builtin_detectors  # noqa: F401
    registry = get_registered_detectors()
    for name in ("structural", "thin_wall", "overhang",
                 "self_intersection", "isolated_faces", "sliver"):
        assert name in registry


def test_register_custom_detector():
    """A custom detector is picked up by the registry."""
    class MyDetector(MeshDetector):
        name = "my_detector"

        def detect(self, mesh):
            return [Issue(name="my_issue", description="d",
                          severity=Severity.INFO, location="l",
                          suggestion="s")]

    register_detector(MyDetector)
    assert "my_detector" in get_registered_detectors()


def test_run_detectors_calls_custom(tmp_path):
    """run_detectors includes custom detector issues."""
    import print_doctor.builtin_detectors  # noqa: F401

    class FlagDetector(MeshDetector):
        name = "flag_detector"

        def detect(self, mesh):
            return [Issue(name="flag", description="flagged",
                          severity=Severity.INFO, location="all",
                          suggestion="none")]

    register_detector(FlagDetector)
    mesh = trimesh.creation.icosphere(subdivisions=2)
    issues = run_detectors(mesh)
    assert any(i.name == "flag" for i in issues)


def test_analyze_with_named_detectors(tmp_path):
    """analyze_mesh_with_detectors runs only the named set."""
    import print_doctor.builtin_detectors  # noqa: F401
    from print_doctor.mesh import load_mesh

    mesh = trimesh.creation.box(extents=[10, 10, 10])
    model = tmp_path / "box.stl"
    mesh.export(str(model))

    # only 'structural' detector
    a = analyze_mesh_with_detectors(str(model), detector_names=["structural"])
    names = {i.name for i in a.issues}
    assert names <= {"non_watertight", "non_manifold",
                     "degenerate_faces", "inverted_normals"}

    # no matching detectors -> no issues (still valid analysis)
    b = analyze_mesh_with_detectors(str(model), detector_names=["nope"])
    assert b.score == 100.0


def test_load_plugins_handles_missing_entry_points():
    """load_plugins never raises (broken plugins are skipped)."""
    registry = load_plugins()
    assert isinstance(registry, dict)
