from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class Severity(Enum):
    """Issue severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Issue:
    """A single issue found in mesh analysis."""
    name: str
    description: str
    severity: Severity
    location: str
    suggestion: str


@dataclass
class MeshAnalysis:
    """Result of analyzing a 3D mesh."""
    filename: str
    is_watertight: bool
    is_manifold: bool
    triangle_count: int
    volume: float
    surface_area: float
    bounding_box: Tuple[float, float, float]
    issues: List[Issue]
    score: float


@dataclass
class CostEstimate:
    """Cost estimate for printing a model."""
    weight_grams: float
    print_time_hours: float
    material_cost: float
    electricity_cost: float
    total_cost: float
    suggested_price: float


@dataclass
class PrintConfig:
    """Print configuration parameters."""
    layer_height: float = 0.2
    infill_percentage: int = 20
    material_type: str = "PLA"
    nozzle_diameter: float = 0.4
    print_speed_mm_s: float = 60.0
    bed_temperature: float = 60.0
    nozzle_temperature: float = 200.0
