"""Built-in mesh detectors as plugin classes.

These wrap the legacy functions in :mod:`print_doctor.mesh` behind the
:class:`~print_doctor.plugins.MeshDetector` interface, so they participate in
the same plugin system as third-party detectors.
"""
from typing import List

import trimesh

from print_doctor.mesh import (
    detect_thin_walls,
    detect_overhangs,
    detect_self_intersections,
    detect_isolated_faces,
    detect_extreme_aspect_ratio,
    validate_mesh,
)
from print_doctor.models import Issue
from print_doctor.plugins import MeshDetector, register_detector


@register_detector
class StructuralIssuesDetector(MeshDetector):
    """Watertightness, manifoldness, degenerate faces, normals."""

    name = "structural"

    def detect(self, mesh: trimesh.Trimesh) -> List[Issue]:
        return validate_mesh(mesh)


@register_detector
class ThinWallDetector(MeshDetector):
    name = "thin_wall"

    def detect(self, mesh: trimesh.Trimesh) -> List[Issue]:
        return detect_thin_walls(mesh)


@register_detector
class OverhangDetector(MeshDetector):
    name = "overhang"

    def detect(self, mesh: trimesh.Trimesh) -> List[Issue]:
        return detect_overhangs(mesh)


@register_detector
class SelfIntersectionDetector(MeshDetector):
    name = "self_intersection"

    def detect(self, mesh: trimesh.Trimesh) -> List[Issue]:
        return detect_self_intersections(mesh)


@register_detector
class IsolatedFacesDetector(MeshDetector):
    name = "isolated_faces"

    def detect(self, mesh: trimesh.Trimesh) -> List[Issue]:
        return detect_isolated_faces(mesh)


@register_detector
class SliverDetector(MeshDetector):
    name = "sliver"

    def detect(self, mesh: trimesh.Trimesh) -> List[Issue]:
        return detect_extreme_aspect_ratio(mesh)


__all__ = [
    "StructuralIssuesDetector",
    "ThinWallDetector",
    "OverhangDetector",
    "SelfIntersectionDetector",
    "IsolatedFacesDetector",
    "SliverDetector",
]
