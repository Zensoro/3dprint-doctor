"""Support material estimation for print costing.

Estimates how much support material a model needs, purely from
geometry: overhang faces are projected downward to the nearest surface,
and support volume is estimated as overhang area x average support
height x a density factor.

This is a *costing* estimate, not a support-path generator (slicers do
that). The density factor is a default guess — calibrate it against your
slicer for accurate quoting.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh

# support volume as fraction of the overhang prism volume
DEFAULT_SUPPORT_DENSITY = 0.15


@dataclass
class SupportEstimate:
    """Estimated support material needed."""
    overhang_area_mm2: float
    avg_support_height_mm: float
    support_volume_mm3: float
    support_weight_g: float
    density_factor: float

    def support_cost(self, material_price_per_kg: float) -> float:
        return self.support_weight_g / 1000.0 * material_price_per_kg


def overhang_face_indices(
    mesh: trimesh.Trimesh, max_angle: float = 45.0
) -> np.ndarray:
    """Return indices of faces that need support (downward + near-horizontal,
    excluding the bed-contact bottom)."""
    nz = mesh.face_normals[:, 2]
    downward = nz < 0
    all_angles = np.degrees(np.arccos(np.clip(-nz, 0.0, 1.0)))
    zmin = float(mesh.vertices[:, 2].min())
    face_z = mesh.triangles_center[:, 2]
    contact_mask = (downward) & (all_angles < 10.0) & (face_z < zmin + 0.5)
    overhang_mask = (downward) & (all_angles < max_angle) & ~contact_mask
    return np.where(overhang_mask)[0]


def estimate_support(
    mesh: trimesh.Trimesh,
    max_angle: float = 45.0,
    density: float = DEFAULT_SUPPORT_DENSITY,
) -> SupportEstimate:
    """Estimate support material needed for a mesh.

    Args:
        mesh: The mesh (not modified)
        max_angle: overhang threshold (degrees)
        density: support density factor (fraction of prism volume)

    Returns:
        SupportEstimate
    """
    overhangs = overhang_face_indices(mesh, max_angle)
    overhang_area = float(mesh.area_faces[overhangs].sum()) if len(overhangs) else 0.0

    if len(overhangs) == 0:
        return SupportEstimate(
            overhang_area_mm2=0.0,
            avg_support_height_mm=0.0,
            support_volume_mm3=0.0,
            support_weight_g=0.0,
            density_factor=density,
        )

    centers = mesh.triangles_center[overhangs]
    origins = centers + np.array([0.0, 0.0, 0.02])
    dirs = np.tile([0.0, 0.0, -1.0], (len(centers), 1))
    locations, ray_idx, tri_idx = mesh.ray.intersects_location(origins, dirs)

    heights: dict = {}
    for loc, ridx, tidx in zip(locations, ray_idx, tri_idx):
        if tidx == overhangs[ridx]:
            continue  # self-hit
        d = float(origins[ridx][2] - loc[2])
        if d <= 0.02:
            continue
        if ridx not in heights or d < heights[ridx]:
            heights[ridx] = d

    total_h = sum(heights.values()) if heights else 0.0
    avg_h = total_h / len(heights) if heights else 0.0
    support_volume = overhang_area * avg_h * density

    return SupportEstimate(
        overhang_area_mm2=overhang_area,
        avg_support_height_mm=avg_h,
        support_volume_mm3=support_volume,
        support_weight_g=support_volume / 1000.0 * 1.24,  # PLA density
        density_factor=density,
    )


def estimate_support_file(model_path: str, **kwargs) -> SupportEstimate:
    """Estimate support for a model file."""
    from print_doctor.mesh import load_mesh
    return estimate_support(load_mesh(model_path), **kwargs)
