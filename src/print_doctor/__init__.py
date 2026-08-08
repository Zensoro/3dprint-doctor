"""Print Doctor - 3D printing pre-flight check, cost estimation and defect diagnosis.

Public API:
    check(mesh_path) -> MeshAnalysis
    estimate_cost(volume_cm3, config, ...) -> CostEstimate
    diagnose(photos, hints) -> Diagnosis
"""

__version__ = "0.5.0"

from print_doctor.mesh import analyze_mesh as check
from print_doctor.cost import calculate_cost as estimate_cost
from print_doctor.diagnose import diagnose_photos as diagnose
from print_doctor.models import (
    Severity,
    Issue,
    MeshAnalysis,
    CostEstimate,
    PrintConfig,
    DefectType,
    Defect,
    RootCause,
    Diagnosis,
)

__all__ = [
    "check",
    "estimate_cost",
    "diagnose",
    "Severity",
    "Issue",
    "MeshAnalysis",
    "CostEstimate",
    "PrintConfig",
    "DefectType",
    "Defect",
    "RootCause",
    "Diagnosis",
    "__version__",
]
