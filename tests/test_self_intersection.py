import trimesh
import numpy as np
from print_doctor.mesh import detect_self_intersections


def test_clean_mesh_no_intersections():
    """Test that a clean mesh has no self-intersections."""
    mesh = trimesh.creation.icosphere(subdivisions=2)

    issues = detect_self_intersections(mesh)

    assert not any(issue.name == "self_intersection" for issue in issues)


def test_self_intersecting_mesh_detected():
    """Test that a mesh with intersecting faces is detected.

    Build a mesh from two interpenetrating boxes so the geometry
    genuinely self-intersects, making it a non-valid volume.
    """
    box1 = trimesh.creation.box(extents=[10, 10, 10])
    box2 = trimesh.creation.box(extents=[10, 10, 10])
    box2.apply_translation([5, 5, 5])

    vertices = np.vstack([box1.vertices, box2.vertices])
    faces = np.vstack([box1.faces, box2.faces + len(box1.vertices)])
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

    issues = detect_self_intersections(mesh)

    assert len(issues) > 0
    assert any(issue.name == "self_intersection" for issue in issues)
