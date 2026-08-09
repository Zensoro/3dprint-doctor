"""Tests for mesh repair (light fixes with honest boundaries)."""
import os
import tempfile

import numpy as np
import trimesh

from print_doctor.mesh import repair_mesh


def _write(mesh) -> str:
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        mesh.export(f.name)
        return f.name


def test_repair_fix_normals():
    """Partial normal inversion is fixed by repair."""
    mesh = trimesh.creation.icosphere(subdivisions=3)
    broken = mesh.copy()
    new_faces = broken.faces.copy()
    new_faces[:10] = broken.faces[:10][:, ::-1]
    broken.faces = new_faces
    assert not broken.is_winding_consistent

    path = _write(broken)
    try:
        report = repair_mesh(path)
        assert "fix_normals" in report["fixed"]
        assert report["issues_after"]["winding_consistent"] is True
    finally:
        os.unlink(path)


def test_repair_reports_holes_honestly():
    """A mesh with holes reports watertightness as not-fixable."""
    mesh = trimesh.creation.icosphere(subdivisions=3)
    broken = mesh.copy()
    broken.update_faces(np.delete(np.arange(len(broken.faces)), np.arange(50)))
    assert not broken.is_watertight

    path = _write(broken)
    try:
        report = repair_mesh(path)
        assert any("watertight" in n for n in report["not_fixable"])
    finally:
        os.unlink(path)


def test_repair_export_output():
    """Repair can write the fixed mesh to a new file."""
    mesh = trimesh.creation.icosphere(subdivisions=3)
    path = _write(mesh)
    try:
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as out:
            out_path = out.name
        try:
            report = repair_mesh(path, output_path=out_path)
            assert report["output"] == out_path
            assert os.path.exists(out_path)
            fixed = trimesh.load(out_path)
            assert fixed.is_watertight
        finally:
            if os.path.exists(out_path):
                os.unlink(out_path)
    finally:
        os.unlink(path)


def test_repair_clean_mesh_no_change():
    """A healthy mesh repairs without harm."""
    mesh = trimesh.creation.icosphere(subdivisions=3)
    path = _write(mesh)
    try:
        report = repair_mesh(path)
        assert report["issues_after"]["watertight"] is True
        assert report["issues_after"]["winding_consistent"] is True
    finally:
        os.unlink(path)
