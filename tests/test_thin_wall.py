import pytest
import trimesh
import numpy as np
from print_doctor.mesh import detect_thin_walls


def test_thin_wall_detection():
    """Test detection of thin walls in a mesh."""
    # Create a box with thin walls (0.3mm thickness)
    # Box dimensions: 10x10x0.3 mm
    mesh = trimesh.creation.box(extents=[10, 10, 0.3])
    
    # Detect thin walls (minimum thickness 0.8mm for PLA)
    issues = detect_thin_walls(mesh, min_thickness=0.8)
    
    # Should find thin wall issues
    assert len(issues) > 0
    assert any(issue.name == "thin_wall" for issue in issues)


def test_thick_wall_no_issues():
    """Test that thick walls don't trigger detection."""
    # Create a box with thick walls (2mm thickness)
    mesh = trimesh.creation.box(extents=[10, 10, 2])
    
    # Detect thin walls (minimum thickness 0.8mm)
    issues = detect_thin_walls(mesh, min_thickness=0.8)
    
    # Should not find thin wall issues
    assert not any(issue.name == "thin_wall" for issue in issues)