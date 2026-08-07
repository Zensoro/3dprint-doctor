import pytest
from print_doctor.models import (
    Severity,
    Issue,
    MeshAnalysis,
    CostEstimate,
    PrintConfig,
)


def test_severity_levels():
    """Test that severity has correct levels."""
    assert Severity.ERROR.value == "error"
    assert Severity.WARNING.value == "warning"
    assert Severity.INFO.value == "info"


def test_issue_creation():
    """Test creating an issue with all fields."""
    issue = Issue(
        name="thin_wall",
        description="Wall thickness below minimum",
        severity=Severity.WARNING,
        location="x=10, y=20, z=30",
        suggestion="Increase wall thickness to at least 0.8mm",
    )
    assert issue.name == "thin_wall"
    assert issue.severity == Severity.WARNING


def test_mesh_analysis_creation():
    """Test creating a mesh analysis result."""
    analysis = MeshAnalysis(
        filename="test.stl",
        is_watertight=True,
        is_manifold=True,
        triangle_count=1000,
        volume=100.0,
        surface_area=200.0,
        bounding_box=(10.0, 20.0, 30.0),
        issues=[],
        score=85.0,
    )
    assert analysis.filename == "test.stl"
    assert analysis.score == 85.0


def test_cost_estimate_creation():
    """Test creating a cost estimate."""
    estimate = CostEstimate(
        weight_grams=50.0,
        print_time_hours=2.5,
        material_cost=5.0,
        electricity_cost=0.25,
        total_cost=5.25,
        suggested_price=10.50,
    )
    assert estimate.weight_grams == 50.0
    assert estimate.suggested_price == 10.50


def test_print_config_defaults():
    """Test that print config has sensible defaults."""
    config = PrintConfig()
    assert config.layer_height == 0.2
    assert config.infill_percentage == 20
    assert config.material_type == "PLA"
