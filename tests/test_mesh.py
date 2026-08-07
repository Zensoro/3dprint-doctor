import pytest
import tempfile
import os
from pathlib import Path
from print_doctor.mesh import load_mesh, validate_mesh


def test_load_stl():
    """Test loading a valid STL file."""
    import trimesh
    import numpy as np
    
    # Create a simple mesh
    mesh = trimesh.creation.icosahedron()
    
    with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as f:
        mesh.export(f.name)
        temp_path = f.name
    
    try:
        loaded = load_mesh(temp_path)
        assert loaded is not None
        assert len(loaded.faces) > 0
    finally:
        os.unlink(temp_path)


def test_validate_manifold_mesh():
    """Test validating a manifold mesh."""
    import trimesh
    mesh = trimesh.creation.icosahedron()
    issues = validate_mesh(mesh)
    # Icosahedron should be manifold
    assert not any(issue.name == "non_manifold" for issue in issues)


def test_validate_watertight_mesh():
    """Test validating a watertight mesh."""
    import trimesh
    mesh = trimesh.creation.icosahedron()
    issues = validate_mesh(mesh)
    # Icosahedron should be watertight
    assert not any(issue.name == "non_watertight" for issue in issues)
