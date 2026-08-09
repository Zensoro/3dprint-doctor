"""Tests for automatic hollowing."""
import os
import tempfile

import numpy as np
import trimesh
import pytest

from print_doctor.hollow import hollow_mesh, hollow_file


def test_hollow_box_saves_material():
    """A box hollowed with 2mm wall saves significant material."""
    box = trimesh.creation.box(extents=[50, 50, 30])
    shell, err = hollow_mesh(box, wall=2.0)
    assert err is None
    assert shell.is_watertight
    savings = (1 - shell.volume / box.volume) * 100
    assert 60 < savings < 90  # expected ~78%


def test_hollow_thin_model_rejected():
    """A model thinner than 2x wall is rejected with a clear error."""
    thin = trimesh.creation.box(extents=[10, 10, 3])
    shell, err = hollow_mesh(thin, wall=2.0)
    assert shell is None
    assert "too thin" in err


def test_hollow_sphere_keeps_volume_below_original():
    """Shell volume must be less than original."""
    sphere = trimesh.creation.icosphere(subdivisions=2, radius=20)
    shell, err = hollow_mesh(sphere, wall=2.0)
    assert err is None
    assert shell.volume < sphere.volume


def test_hollow_file(tmp_path):
    """hollow_file writes the shell and returns stats."""
    box = trimesh.creation.box(extents=[50, 50, 30])
    src = tmp_path / "box.stl"
    box.export(str(src))
    out = tmp_path / "shell.stl"

    result = hollow_file(str(src), str(out), wall=2.0)
    assert os.path.exists(out)
    assert result.saved_percent > 60
    assert result.wall == 2.0


def test_hollow_file_raises_on_thin():
    """hollow_file raises ValueError on too-thin models."""
    thin = trimesh.creation.box(extents=[10, 10, 3])
    src = "/tmp/thin_test.stl"
    thin.export(src)
    try:
        with pytest.raises(ValueError, match="too thin"):
            hollow_file(src, "/tmp/thin_out.stl", wall=2.0)
    finally:
        if os.path.exists(src):
            os.unlink(src)
        if os.path.exists("/tmp/thin_out.stl"):
            os.unlink("/tmp/thin_out.stl")
