"""Tests for support material estimation."""
import numpy as np
import trimesh

from print_doctor.support import estimate_support, estimate_support_file, overhang_face_indices


def test_cone_no_support():
    """A cone with base down needs no support."""
    cone = trimesh.creation.cone(radius=5, height=10)
    est = estimate_support(cone)
    assert est.support_volume_mm3 == 0.0
    assert est.support_weight_g == 0.0


def test_bar_overhang_has_support():
    """A bar overhanging its column needs support."""
    column = trimesh.creation.box(extents=[4, 4, 8])
    bar = trimesh.creation.box(extents=[12, 4, 2])
    bar.apply_translation([0, 0, 8])
    mesh = trimesh.util.concatenate([column, bar])

    est = estimate_support(mesh)
    assert est.support_volume_mm3 > 0
    assert est.support_weight_g > 0
    assert len(overhang_face_indices(mesh)) > 0


def test_support_cost():
    """support_cost scales with price."""
    cone = trimesh.creation.cone(radius=5, height=10)
    est = estimate_support(cone)
    assert est.support_cost(25.0) == 0.0


def test_estimate_support_file(tmp_path):
    """estimate_support_file loads and estimates."""
    cone = trimesh.creation.cone(radius=5, height=10)
    p = tmp_path / "cone.stl"
    cone.export(str(p))
    est = estimate_support_file(str(p))
    assert est.support_volume_mm3 == 0.0


def test_estimate_support_density_factor():
    """Density factor scales volume (external overhang)."""
    # a wide top bar supported by a narrow column -> external overhang
    column = trimesh.creation.box(extents=[4, 4, 8])
    bar = trimesh.creation.box(extents=[12, 4, 2])
    bar.apply_translation([0, 0, 8])
    mesh = trimesh.util.concatenate([column, bar])

    est_lo = estimate_support(mesh, density=0.1)
    est_hi = estimate_support(mesh, density=0.5)
    assert est_hi.support_volume_mm3 > est_lo.support_volume_mm3
    assert est_hi.support_volume_mm3 > 0
