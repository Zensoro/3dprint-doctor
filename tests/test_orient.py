"""Tests for print orientation optimization."""
import numpy as np
import trimesh

from print_doctor.orient import find_orientation, _score


def test_cone_flat_has_contact():
    """A cone with base down has a large bed-contact area."""
    cone = trimesh.creation.cone(radius=5, height=10)
    overhang, contact = _score(cone)
    assert contact > 0.3
    assert overhang == 0.0


def test_cone_inverted_loses_contact():
    """Inverting the cone (tip down) removes bed contact."""
    cone = trimesh.creation.cone(radius=5, height=10)
    inv = cone.copy()
    inv.apply_transform(trimesh.transformations.rotation_matrix(
        np.pi, [1, 0, 0]))
    overhang, contact = _score(inv)
    assert contact < 0.01


def test_find_orientation_recovers_base_down():
    """find_orientation finds the base-down pose for a cone."""
    cone = trimesh.creation.cone(radius=5, height=10)
    result = find_orientation(cone, step_deg=90)
    assert result.contact_fraction > 0.3
    assert result.overhang_fraction == 0.0


def test_find_orientation_returns_candidates():
    """find_orientation returns a full candidate list."""
    cone = trimesh.creation.cone(radius=5, height=10)
    result = find_orientation(cone, step_deg=90)
    assert len(result.candidates) == 16  # 4x4 grid
    assert result.score <= 0  # good orientation has negative score
