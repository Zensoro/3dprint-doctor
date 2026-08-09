"""Print orientation optimization.

Finds a good print orientation by searching rotations around the X/Y
axes, scoring each candidate by overhang faces (bad) and bed-contact
area (good). Pure geometry, offline, deterministic.

The search is coarse (15-degree steps over X and Y tilts) — enough to
recommend "tilt this way" without pretending to be a slicer's exact
optimizer. For best results, use the slicer's own auto-orientation;
this tool's value is a fast sanity check before slicing.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

import numpy as np
import trimesh


@dataclass
class OrientationResult:
    """Best-found orientation and its stats."""
    score: float
    rx_deg: float
    ry_deg: float
    overhang_fraction: float
    contact_fraction: float
    candidates: List[dict] = field(default_factory=list)


def _score(mesh: trimesh.Trimesh, max_angle: float = 45.0) -> tuple:
    """Return (overhang_fraction, contact_fraction) for the current pose."""
    nz = mesh.face_normals[:, 2]
    downward = nz < 0
    all_angles = np.degrees(np.arccos(np.clip(-nz, 0.0, 1.0)))
    zmin = float(mesh.vertices[:, 2].min())
    face_z = mesh.triangles_center[:, 2]

    contact_mask = (
        (downward) & (all_angles < 10.0) & (face_z < zmin + 0.5)
    )
    overhang_mask = (
        (downward) & (all_angles < max_angle) & ~contact_mask
    )
    n = len(mesh.faces)
    return (np.sum(overhang_mask) / n, np.sum(contact_mask) / n)


def find_orientation(
    mesh: trimesh.Trimesh,
    max_angle: float = 45.0,
    step_deg: float = 15.0,
) -> OrientationResult:
    """Search rotations around X and Y to minimize overhang + maximize contact.

    Combined score: lower is better.
        score = overhang_fraction * 10 - contact_fraction * 5

    Args:
        mesh: Mesh to orient (not modified)
        max_angle: overhang threshold in degrees
        step_deg: rotation search step in degrees

    Returns:
        OrientationResult with best pose and stats
    """
    best = None
    candidates = []

    angles = list(range(0, 360, int(step_deg)))
    for rx in angles:
        for ry in angles:
            m = mesh.copy()
            if rx:
                m.apply_transform(trimesh.transformations.rotation_matrix(
                    math.radians(rx), [1, 0, 0]))
            if ry:
                m.apply_transform(trimesh.transformations.rotation_matrix(
                    math.radians(ry), [0, 1, 0]))
            overhang, contact = _score(m, max_angle)
            score = overhang * 10.0 - contact * 5.0
            candidates.append({
                "rx": rx, "ry": ry,
                "overhang": round(float(overhang), 4),
                "contact": round(float(contact), 4),
                "score": round(float(score), 4),
            })
            if best is None or score < best["score"]:
                best = candidates[-1]

    return OrientationResult(
        score=best["score"],
        rx_deg=best["rx"],
        ry_deg=best["ry"],
        overhang_fraction=best["overhang"],
        contact_fraction=best["contact"],
        candidates=candidates,
    )
