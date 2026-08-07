import os
import tempfile
import trimesh
from print_doctor.mesh import analyze_mesh


def test_analyze_clean_mesh():
    """Test complete analysis of a clean mesh."""
    mesh = trimesh.creation.icosphere(subdivisions=2)

    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        mesh.export(f.name)
        temp_path = f.name

    try:
        analysis = analyze_mesh(temp_path)

        assert analysis.filename == os.path.basename(temp_path)
        assert analysis.is_watertight == mesh.is_watertight
        assert analysis.triangle_count == len(mesh.faces)
        assert analysis.volume > 0
        assert analysis.surface_area > 0
        assert 0 <= analysis.score <= 100
        assert analysis.bounding_box[0] > 0
        assert analysis.bounding_box[1] > 0
        assert analysis.bounding_box[2] > 0
    finally:
        os.unlink(temp_path)


def test_analyze_broken_mesh_penalized():
    """Test that a broken mesh gets a lower score."""
    # Two interleaved boxes -> self-intersections, lower score
    b1 = trimesh.creation.box(extents=[10, 10, 10])
    b2 = trimesh.creation.box(extents=[10, 10, 10])
    b2.apply_translation([5, 5, 5])
    broken = trimesh.Trimesh(
        vertices=__import__("numpy").vstack([b1.vertices, b2.vertices]),
        faces=__import__("numpy").vstack([b1.faces, b2.faces + len(b1.vertices)]),
    )

    healthy = trimesh.creation.box(extents=[10, 10, 10])

    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f1, \
         tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f2:
        broken.export(f1.name)
        healthy.export(f2.name)
        broken_path, healthy_path = f1.name, f2.name

    try:
        broken_analysis = analyze_mesh(broken_path)
        healthy_analysis = analyze_mesh(healthy_path)

        assert broken_analysis.score < healthy_analysis.score
        assert any(i.name == "self_intersection" for i in broken_analysis.issues)
    finally:
        os.unlink(broken_path)
        os.unlink(healthy_path)


def test_analyze_missing_file_raises():
    """Test that a missing file raises a clear error."""
    import pytest
    with pytest.raises(ValueError, match="not found"):
        analyze_mesh("/nonexistent/path/model.stl")
