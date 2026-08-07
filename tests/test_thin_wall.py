import pytest
import trimesh
import numpy as np
from print_doctor.mesh import detect_thin_walls


def test_thin_plate_detection():
    """Test detection of a thin plate (0.3mm thick)."""
    # A 10x10x0.3mm plate is thinner than the 0.8mm minimum
    mesh = trimesh.creation.box(extents=[10, 10, 0.3])

    issues = detect_thin_walls(mesh, min_thickness=0.8)

    assert len(issues) > 0
    assert any(issue.name == "thin_wall" for issue in issues)


def test_hollow_shell_detection():
    """Test detection of a hollow shell with 0.5mm walls.

    The outer box is 10x10x2mm with an inner cavity of 9x9x1mm,
    leaving a 0.5mm wall thickness on each side. This is a real
    thin-wall case that bounding-box checks would miss entirely.
    """
    outer = trimesh.creation.box(extents=[10, 10, 2])
    inner = trimesh.creation.box(extents=[9, 9, 1])
    shell = outer.difference(inner)

    issues = detect_thin_walls(shell, min_thickness=0.8, sample_count=800)

    assert any(issue.name == "thin_wall" for issue in issues)


def test_thick_wall_no_issues():
    """Test that a thick solid box doesn't trigger detection."""
    mesh = trimesh.creation.box(extents=[10, 10, 2])

    issues = detect_thin_walls(mesh, min_thickness=0.8)

    assert not any(issue.name == "thin_wall" for issue in issues)


def test_custom_min_thickness():
    """Test that the threshold parameter is respected."""
    mesh = trimesh.creation.box(extents=[10, 10, 0.3])

    # Very permissive threshold: 0.3mm wall is not thin
    issues = detect_thin_walls(mesh, min_thickness=0.2)
    assert not any(issue.name == "thin_wall" for issue in issues)

    # Strict threshold: 0.3mm wall is thin
    issues = detect_thin_walls(mesh, min_thickness=0.5)
    assert any(issue.name == "thin_wall" for issue in issues)
