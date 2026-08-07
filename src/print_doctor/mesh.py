from pathlib import Path
from typing import List
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
