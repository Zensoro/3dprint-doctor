import trimesh
import numpy as np
from print_doctor.mesh import detect_overhangs


def test_overhang_detection_sphere():
    """Test detection of overhangs in a sphere (has many overhangs)."""
    mesh = trimesh.creation.icosphere(subdivisions=3, radius=10)

    issues = detect_overhangs(mesh, max_angle_degrees=45)

    assert len(issues) > 0
    assert any(issue.name == "overhang" for issue in issues)


def test_flat_plate_threshold_boundary():
    """Test that the plate's downward face is detected at a sensible threshold.

    A flat plate has a horizontal downward face (overhang angle 0°).
    With a 10-degree threshold it should be flagged; with a 0-degree
    threshold (nothing more horizontal than exactly horizontal) it
    should not.
    """
    mesh = trimesh.creation.box(extents=[50, 50, 2])

    issues = detect_overhangs(mesh, max_angle_degrees=10)
    assert any(issue.name == "overhang" for issue in issues)

    issues = detect_overhangs(mesh, max_angle_degrees=0)
    assert not any(issue.name == "overhang" for issue in issues)


def test_steep_threshold_reduces_overhangs():
    """Test that a more permissive threshold finds fewer overhangs."""
    sphere = trimesh.creation.icosphere(subdivisions=3, radius=10)

    strict = detect_overhangs(sphere, max_angle_degrees=20)
    permissive = detect_overhangs(sphere, max_angle_degrees=60)

    assert len(strict) > 0 and len(permissive) > 0
    strict_percentage = float(strict[0].description.split("(")[1].split("%")[0])
    permissive_percentage = float(permissive[0].description.split("(")[1].split("%")[0])
    assert strict_percentage < permissive_percentage
