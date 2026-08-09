from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Tuple


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
    """Result of analyzing a 3D mesh.

    Note: ``volume`` is in cubic millimeters (trimesh native units,
    models are assumed to be sized in mm); ``surface_area`` is in
    square millimeters.
    """
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
    """Cost estimate for printing a model.

    cost_breakdown gives the full shop-pricing picture: material,
    electricity, machine depreciation, labor, waste, and the final
    suggested retail price.
    """
    weight_grams: float
    print_time_hours: float
    material_cost: float
    electricity_cost: float
    total_cost: float
    suggested_price: float
    machine_cost: float = 0.0
    labor_cost: float = 0.0
    waste_cost: float = 0.0


@dataclass
class QuoteConfig:
    """Shop pricing parameters for quoting prints."""
    electricity_price_per_kwh: float = 0.12
    machine_power_watts: float = 200.0
    machine_price: float = 399.0  # printer cost in USD
    machine_lifetime_hours: float = 5000.0  # useful life before replacement
    labor_rate_per_hour: float = 8.0  # operator cost
    waste_factor: float = 0.05  # failed prints / material waste ratio
    profit_margin: float = 2.0  # suggested_price = total * margin


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


class DefectType(Enum):
    """Types of print defects detectable from photos."""
    STRINGING = "stringing"
    WARPING = "warping"
    LAYER_SHIFT = "layer_shift"
    UNDER_EXTRUSION = "under_extrusion"
    OVER_EXTRUSION = "over_extrusion"
    COLOR_BLEEDING = "color_bleeding"
    FIRST_LAYER_FAILURE = "first_layer_failure"


@dataclass
class Defect:
    """A single detected defect from photo diagnosis."""
    type: DefectType
    confidence: float  # 0.0 - 1.0
    evidence: str  # explainable evidence chain


@dataclass
class RootCause:
    """A likely root cause with actionable fix."""
    cause: str
    likelihood: float  # 0.0 - 1.0
    fix: str  # which parameter to change and in which direction


@dataclass
class Diagnosis:
    """Result of diagnosing a printed part from photos."""
    filename: str
    defects: List[Defect]
    root_causes: List[RootCause]
    image_count: int
    regions: List[Dict[str, Any]] = field(default_factory=list)
