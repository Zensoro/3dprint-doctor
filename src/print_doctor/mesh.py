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
    min_thickness: float = 0.8
) -> List[Issue]:
    """Detect walls thinner than minimum thickness.
    
    Args:
        mesh: Trimesh object to analyze
        min_thickness: Minimum allowed thickness in mm
        
    Returns:
        List of thin wall issues
    """
    issues = []
    
    # Get bounding box dimensions
    extents = mesh.bounding_box.extents
    
    # Check each dimension
    axis_names = ['X', 'Y', 'Z']
    for i, (extent, axis) in enumerate(zip(extents, axis_names)):
        if extent < min_thickness:
            issues.append(Issue(
                name="thin_wall",
                description=f"Wall thickness in {axis} direction is {extent:.2f}mm (minimum: {min_thickness}mm)",
                severity=Severity.WARNING,
                location=f"{axis} axis: {extent:.2f}mm",
                suggestion=f"Increase {axis} dimension to at least {min_thickness}mm",
            ))
    
    return issues
