from pathlib import Path
from typing import List
import os
import trimesh
import numpy as np

from print_doctor.models import Issue, Severity


def load_mesh(file_path: str) -> trimesh.Trimesh:
    """Load a 3D model from STL/3MF file.
    
    Args:
        file_path: Path to the model file
        
    Returns:
        Trimesh object
        
    Raises:
        ValueError: If file cannot be loaded
    """
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")
    
    try:
        mesh = trimesh.load(str(path))
        if not isinstance(mesh, trimesh.Trimesh):
            raise ValueError(f"File does not contain a valid 3D mesh: {file_path}")
        return mesh
    except Exception as e:
        raise ValueError(f"Failed to load mesh: {e}")


def validate_mesh(mesh: trimesh.Trimesh) -> List[Issue]:
    """Validate mesh for basic 3D printing issues.
    
    Args:
        mesh: Trimesh object to validate
        
    Returns:
        List of issues found
    """
    issues = []
    
    # Check if mesh is manifold
    if not mesh.is_watertight:
        issues.append(Issue(
            name="non_watertight",
            description="Mesh has holes or gaps (not watertight)",
            severity=Severity.ERROR,
            location="Mesh boundary",
            suggestion="Repair mesh in MeshLab or netfabb",
        ))
    
    # Check if mesh is manifold
    if not mesh.is_volume:
        issues.append(Issue(
            name="non_manifold",
            description="Mesh has non-manifold edges or faces",
            severity=Severity.ERROR,
            location="Mesh edges",
            suggestion="Remove duplicate faces and fix edge connections",
        ))
    
    # Check for degenerate faces
    area_threshold = 1e-10
    areas = mesh.area_faces
    degenerate_count = np.sum(areas < area_threshold)
    if degenerate_count > 0:
        issues.append(Issue(
            name="degenerate_faces",
            description=f"Found {degenerate_count} degenerate faces (zero area)",
            severity=Severity.WARNING,
            location=f"{degenerate_count} faces",
            suggestion="Remove degenerate triangles",
        ))
    
    # Check for inverted normals
    if not mesh.is_winding_consistent:
        issues.append(Issue(
            name="inverted_normals",
            description="Some faces have inverted normals",
            severity=Severity.WARNING,
            location="Various faces",
            suggestion="Flip inverted faces to ensure consistent winding",
        ))
    
    return issues


def detect_thin_walls(
    mesh: trimesh.Trimesh,
    min_thickness: float = 0.8,
    sample_count: int = 500,
) -> List[Issue]:
    """Detect walls thinner than minimum thickness.

    Samples points on the mesh surface and casts rays along inward
    normals, measuring the distance to the opposite surface. Regions
    where that distance is below `min_thickness` are reported as thin
    walls.

    Args:
        mesh: Trimesh object to analyze
        min_thickness: Minimum allowed thickness in mm
        sample_count: Number of surface points to sample

    Returns:
        List of thin wall issues
    """
    issues = []

    points, face_indices = trimesh.sample.sample_surface(mesh, sample_count)
    normals = mesh.face_normals[face_indices]
    origins = points - normals * 1e-4

    locations, ray_indices, _ = mesh.ray.intersects_location(
        origins, -normals
    )
    if len(locations) == 0:
        return issues

    distances = np.linalg.norm(locations - origins[ray_indices], axis=1)
    # Filter out self-hits (rays that immediately re-hit the origin face)
    distances = distances[distances > 0.05]

    if len(distances) == 0:
        return issues

    thin_mask = distances < min_thickness
    thin_count = int(np.sum(thin_mask))
    if thin_count > 0:
        percentage = thin_count / len(distances) * 100
        min_hit = float(distances[thin_mask].min())
        issues.append(Issue(
            name="thin_wall",
            description=(
                f"Found thin wall regions: {thin_count}/{len(distances)} "
                f"sample points ({percentage:.1f}%) have local thickness "
                f"below {min_thickness}mm (minimum measured: {min_hit:.2f}mm)"
            ),
            severity=Severity.WARNING,
            location=f"{percentage:.1f}% of sampled surface",
            suggestion=(
                f"Increase wall thickness to at least {min_thickness}mm, "
                "or hollow out and re-model the thin section"
            ),
        ))

    return issues


def detect_overhangs(
    mesh: trimesh.Trimesh,
    max_angle_degrees: float = 45.0,
) -> List[Issue]:
    """Detect faces that exceed the maximum overhang angle.

    Only faces whose normals point downward (negative Z) are
    considered. The overhang angle is measured from the vertical-down
    direction: 0 degrees means the face is horizontal (facing down,
    worst case), 90 degrees means it is nearly vertical. Faces with an
    overhang angle below `max_angle_degrees` are reported.

    Args:
        mesh: Trimesh object to analyze
        max_angle_degrees: Maximum allowed overhang angle; faces more
            horizontal than this are reported

    Returns:
        List of overhang issues
    """
    issues = []

    normals = mesh.face_normals
    nz = normals[:, 2]
    downward = nz < 0

    if not np.any(downward):
        return issues

    # Angle from vertical-down direction for downward faces
    overhang_angles = np.degrees(np.arccos(np.clip(-nz[downward], 0.0, 1.0)))

    overhang_mask = overhang_angles < max_angle_degrees
    overhang_count = int(np.sum(overhang_mask))

    if overhang_count > 0:
        total_faces = len(mesh.faces)
        overhang_percentage = overhang_count / total_faces * 100

        issues.append(Issue(
            name="overhang",
            description=(
                f"Found {overhang_count} faces ({overhang_percentage:.1f}%) "
                f"with overhang angle below {max_angle_degrees} degrees "
                "(measured from horizontal)"
            ),
            severity=Severity.WARNING,
            location=f"{overhang_count} faces",
            suggestion=(
                "Add support structures or rotate the model to reduce "
                "overhang angles below the printability threshold"
            ),
        ))

    return issues


def _segment_triangle_intersect(
    p1: np.ndarray,
    p2: np.ndarray,
    tri: np.ndarray,
    eps: float = 1e-9,
) -> bool:
    """Check whether segment p1-p2 intersects triangle tri (Möller-Trumbore)."""
    v0, v1, v2 = tri
    e1 = v1 - v0
    e2 = v2 - v0
    d = p2 - p1

    pvec = np.cross(d, e2)
    det = np.dot(e1, pvec)
    if abs(det) < eps:
        return False

    inv = 1.0 / det
    tvec = p1 - v0
    u = np.dot(tvec, pvec) * inv
    if u < -eps or u > 1.0 + eps:
        return False

    qvec = np.cross(tvec, e1)
    v = np.dot(d, qvec) * inv
    if v < -eps or u + v > 1.0 + eps:
        return False

    t = np.dot(e2, qvec) * inv
    return -eps <= t <= 1.0 + eps


def _triangles_intersect(t1: np.ndarray, t2: np.ndarray) -> bool:
    """Check whether two triangles genuinely intersect (not just touch)."""
    for i in range(3):
        if _segment_triangle_intersect(t1[i], t1[(i + 1) % 3], t2):
            return True
    for i in range(3):
        if _segment_triangle_intersect(t2[i], t2[(i + 1) % 3], t1):
            return True
    return False


def detect_self_intersections(
    mesh: trimesh.Trimesh,
    max_triangles: int = 200_000,
) -> List[Issue]:
    """Detect self-intersecting faces in the mesh.

    Uses an R-tree over triangle bounding boxes to find candidate
    pairs, then confirms with an exact segment-triangle intersection
    test. Triangles sharing vertices (legitimate adjacency) are
    skipped.

    Args:
        mesh: Trimesh object to analyze
        max_triangles: Skip analysis for meshes larger than this
            many triangles (performance guard)

    Returns:
        List of self-intersection issues
    """
    issues = []

    triangles = mesh.triangles
    faces = mesh.faces
    n = len(triangles)

    if n < 2 or n > max_triangles:
        return issues

    mins = triangles.min(axis=1)
    maxs = triangles.max(axis=1)
    tree = mesh.triangles_tree

    intersecting_pairs = []
    for i in range(n):
        query = (
            float(mins[i][0]), float(mins[i][1]), float(mins[i][2]),
            float(maxs[i][0]), float(maxs[i][1]), float(maxs[i][2]),
        )
        for j in tree.intersection(query):
            j = int(j)
            if j <= i:
                continue
            # Skip triangles sharing vertices (adjacency, not intersection)
            if len(set(faces[i]) & set(faces[j])) > 0:
                continue
            if _triangles_intersect(triangles[i], triangles[j]):
                intersecting_pairs.append((i, j))

    if intersecting_pairs:
        issues.append(Issue(
            name="self_intersection",
            description=(
                f"Mesh has {len(intersecting_pairs)} intersecting face "
                "pairs; it cannot be sliced or printed correctly"
            ),
            severity=Severity.ERROR,
            location=f"{len(intersecting_pairs)} face pairs",
            suggestion=(
                "Repair the mesh with MeshLab (Filters -> Cleaning -> "
                "Remove Self Intersections) or re-export from CAD"
            ),
        ))

    return issues


def detect_isolated_faces(mesh: trimesh.Trimesh) -> List[Issue]:
    """Detect disconnected components (isolated shells) in the mesh.

    Args:
        mesh: Trimesh object to analyze

    Returns:
        List of issues for disconnected components
    """
    issues = []

    body_count = mesh.body_count
    if body_count > 1:
        issues.append(Issue(
            name="isolated_faces",
            description=(
                f"Mesh has {body_count} disconnected components; "
                "parts may print detached from each other"
            ),
            severity=Severity.WARNING,
            location=f"{body_count} components",
            suggestion=(
                "Join all components into a single watertight mesh in "
                "your CAD software before slicing"
            ),
        ))

    return issues


def detect_extreme_aspect_ratio(
    mesh: trimesh.Trimesh,
    min_area: float = 1e-6,
) -> List[Issue]:
    """Detect sliver triangles with very small area.

    Args:
        mesh: Trimesh object to analyze
        min_area: Area threshold below which a triangle is a sliver

    Returns:
        List of sliver triangle issues
    """
    issues = []

    areas = mesh.area_faces
    sliver_count = int(np.sum(areas < min_area))

    if sliver_count > 0:
        issues.append(Issue(
            name="sliver_triangles",
            description=(
                f"Found {sliver_count} sliver triangles with area below "
                f"{min_area:.2e}; these can cause slicing artifacts"
            ),
            severity=Severity.INFO,
            location=f"{sliver_count} triangles",
            suggestion=(
                "Simplify the mesh or remesh the affected regions to "
                "remove degenerate triangles"
            ),
        ))

    return issues


def analyze_mesh(file_path: str) -> "MeshAnalysis":
    """Perform a complete printability analysis of a 3D model.

    Runs all registered detectors (built-in + any plugin via entry
    points or :func:`print_doctor.plugins.register_detector`).

    Args:
        file_path: Path to an STL/3MF file

    Returns:
        MeshAnalysis with mesh stats, detected issues and a score

    Raises:
        ValueError: If the file cannot be loaded
    """
    return analyze_mesh_with_detectors(file_path, detector_names=None)


def analyze_mesh_with_detectors(
    file_path: str, detector_names: list = None
) -> "MeshAnalysis":
    """Analyze a mesh running only the named detectors.

    Args:
        file_path: Path to an STL/3MF file
        detector_names: List of detector names to run (None = all
            registered). Unknown names are ignored.

    Returns:
        MeshAnalysis with mesh stats, detected issues and a score
    """
    from print_doctor.models import MeshAnalysis
    from print_doctor.plugins import load_plugins, get_registered_detectors
    import print_doctor.builtin_detectors  # noqa: F401 - registers built-ins

    mesh = load_mesh(file_path)

    registry = load_plugins()
    detectors = registry
    if detector_names is not None:
        wanted = set(detector_names)
        detectors = {k: v for k, v in registry.items() if k in wanted}

    issues = []
    for cls in detectors.values():
        try:
            issues.extend(cls().detect(mesh))
        except Exception:
            continue

    penalty = 0
    for issue in issues:
        if issue.severity == Severity.ERROR:
            penalty += 20
        elif issue.severity == Severity.WARNING:
            penalty += 10
        else:
            penalty += 5

    score = max(0.0, 100.0 - penalty)

    return MeshAnalysis(
        filename=os.path.basename(file_path),
        is_watertight=mesh.is_watertight,
        is_manifold=mesh.is_volume,
        triangle_count=len(mesh.faces),
        volume=float(mesh.volume) if mesh.volume is not None else 0.0,
        surface_area=float(mesh.area),
        bounding_box=tuple(float(x) for x in mesh.bounding_box.extents),
        issues=issues,
        score=score,
    )


def repair_mesh(
    file_path: str,
    output_path: str = None,
    fix_normals: bool = True,
    fix_winding: bool = True,
    stitch: bool = True,
    remove_degenerate: bool = True,
) -> dict:
    """Repair common mesh issues (light fixes only).

    Performs the fixes trimesh can reliably do:
      - fix_normals: unify face winding (partial inversions)
      - fix_winding: consistent outward orientation
      - stitch: merge duplicate vertices / disconnected seams
      - remove_degenerate: drop zero-area faces

    NOT attempted (trimesh cannot do these reliably):
      - large holes / missing regions
      - self-intersections

    Returns a dict describing what was found and what was fixed, with
    honest "not_fixable" entries for issues outside repair scope.
    """
    import trimesh.repair as trepair

    mesh = load_mesh(file_path)
    report = {
        "input": os.path.basename(file_path),
        "issues_before": {},
        "issues_after": {},
        "fixed": [],
        "not_fixable": [],
    }

    # ---- assess before ----
    before = {
        "watertight": mesh.is_watertight,
        "winding_consistent": mesh.is_winding_consistent,
        "degenerate_faces": int(np.sum(mesh.area_faces < 1e-10)),
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
    }
    report["issues_before"] = before

    # ---- apply fixes ----
    if fix_normals:
        trepair.fix_normals(mesh)
        report["fixed"].append("fix_normals")
    if fix_winding:
        trepair.fix_winding(mesh)
        report["fixed"].append("fix_winding")
    if stitch:
        try:
            trepair.stitch(mesh)
            report["fixed"].append("stitch")
        except Exception:
            # stitch fails on meshes with no duplicate vertices to merge;
            # that's fine - nothing to stitch
            pass
    if remove_degenerate:
        # broken_faces returns indices of degenerate faces; remove them
        broken = trepair.broken_faces(mesh)
        if len(broken) > 0:
            mask = np.ones(len(mesh.faces), dtype=bool)
            mask[broken] = False
            mesh.update_faces(mask)
        report["fixed"].append("remove_degenerate")

    # ---- assess after ----
    after = {
        "watertight": mesh.is_watertight,
        "winding_consistent": mesh.is_winding_consistent,
        "degenerate_faces": int(np.sum(mesh.area_faces < 1e-10)),
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
    }
    report["issues_after"] = after

    # ---- honest not-fixable ----
    if not mesh.is_watertight:
        report["not_fixable"].append(
            "watertightness (holes): trimesh cannot reliably fill holes; "
            "use a dedicated repair tool for large gaps"
        )
    from print_doctor.mesh import detect_self_intersections
    if detect_self_intersections(mesh):
        report["not_fixable"].append(
            "self-intersections: no automatic repair; re-export from CAD"
        )

    if output_path:
        mesh.export(output_path)
        report["output"] = output_path

    return report
