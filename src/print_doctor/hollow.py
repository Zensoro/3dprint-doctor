"""Automatic hollowing (shell extraction) to save material.

Uses a scale-based approximation of a uniform wall: the model is shrunk
by the wall thickness around its bounding-box center, then subtracted
from the original. This is approximate — the wall is not perfectly
uniform for non-convex shapes — which we state honestly. For precise
shelling use CAD software; this tool is for quick material savings.

A model thinner than ~2x the wall thickness is rejected (would leave no
interior or negative shell).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import trimesh


@dataclass
class HollowResult:
    """Result of hollowing a mesh."""
    shell: trimesh.Trimesh
    original_volume: float
    shell_volume: float
    saved_percent: float
    wall: float


def hollow_mesh(
    mesh: trimesh.Trimesh, wall: float = 2.0
) -> Tuple[Optional[trimesh.Trimesh], Optional[str]]:
    """Hollow a mesh, keeping approximately `wall` mm of shell.

    Returns (shell, error). error is set when the model is too thin.
    """
    extents = mesh.bounding_box.extents
    if np.min(extents) <= wall * 2 + 0.01:
        return None, (
            f"model too thin for wall {wall}mm "
            f"(min extent {np.min(extents):.2f}mm)"
        )

    scale = (extents - 2 * wall) / extents
    inner = mesh.copy()
    inner.apply_scale(scale)
    inner.apply_translation(
        mesh.bounding_box.centroid - inner.bounding_box.centroid
    )
    shell = mesh.difference(inner)
    return shell, None


def hollow_file(
    model_path: str,
    output_path: str,
    wall: float = 2.0,
) -> HollowResult:
    """Hollow a model file and write the shell to output_path.

    Args:
        model_path: STL/3MF file
        output_path: output file
        wall: shell wall thickness in mm

    Returns:
        HollowResult with shell and stats

    Raises:
        ValueError: if model is too thin for the requested wall
    """
    from print_doctor.mesh import load_mesh

    mesh = load_mesh(model_path)
    shell, err = hollow_mesh(mesh, wall)
    if err:
        raise ValueError(err)

    original_volume = float(mesh.volume)
    shell_volume = float(shell.volume)
    saved_percent = (
        (1 - shell_volume / original_volume) * 100
        if original_volume > 0 else 0.0
    )

    shell.export(output_path)
    return HollowResult(
        shell=shell,
        original_volume=original_volume,
        shell_volume=shell_volume,
        saved_percent=saved_percent,
        wall=wall,
    )
