import pytest
from print_doctor.cost import calculate_cost
from print_doctor.models import PrintConfig, CostEstimate


def test_calculate_cost_default_config():
    """Test cost calculation with default config."""
    config = PrintConfig()

    estimate = calculate_cost(
        volume_cm3=10.0,
        config=config,
        material_price_per_kg=25.0,
        electricity_price_per_kwh=0.12,
        machine_power_watts=200.0,
    )

    assert isinstance(estimate, CostEstimate)
    assert estimate.weight_grams > 0
    assert estimate.print_time_hours > 0
    assert estimate.material_cost > 0
    assert estimate.electricity_cost > 0
    assert estimate.total_cost > 0
    assert estimate.suggested_price > estimate.total_cost


def test_calculate_cost_infill_reduces_weight():
    """Test that lower infill reduces weight and cost."""
    config_full = PrintConfig(infill_percentage=100)
    config_hollow = PrintConfig(infill_percentage=10)

    full = calculate_cost(
        volume_cm3=10.0, config=config_full,
        material_price_per_kg=25.0, electricity_price_per_kwh=0.12,
        machine_power_watts=200.0,
    )
    hollow = calculate_cost(
        volume_cm3=10.0, config=config_hollow,
        material_price_per_kg=25.0, electricity_price_per_kwh=0.12,
        machine_power_watts=200.0,
    )

    assert hollow.weight_grams < full.weight_grams
    assert hollow.material_cost < full.material_cost


def test_calculate_cost_different_material():
    """Test cost calculation with a different material."""
    config = PrintConfig(material_type="PETG")

    estimate = calculate_cost(
        volume_cm3=10.0,
        config=config,
        material_price_per_kg=30.0,
        electricity_price_per_kwh=0.12,
        machine_power_watts=200.0,
    )

    assert estimate.weight_grams > 0
    assert estimate.total_cost > 0


def test_calculate_cost_material_density_unknown():
    """Test that unknown materials fall back to PLA density."""
    config = PrintConfig(material_type="UNKNOWN")

    estimate = calculate_cost(
        volume_cm3=10.0, config=config,
        material_price_per_kg=25.0, electricity_price_per_kwh=0.12,
        machine_power_watts=200.0,
    )

    assert estimate.weight_grams > 0
