from typing import Optional

from print_doctor.models import PrintConfig, CostEstimate, QuoteConfig


# Material densities in g/cm³
MATERIAL_DENSITIES = {
    "PLA": 1.24,
    "PETG": 1.27,
    "ABS": 1.04,
    "TPU": 1.21,
    "Nylon": 1.14,
}

# Default prices per kg in USD (rough market values)
MATERIAL_PRICES = {
    "PLA": 25.0,
    "PETG": 30.0,
    "ABS": 28.0,
    "TPU": 35.0,
    "Nylon": 45.0,
}


def get_material_density(material_type: str) -> float:
    """Return density (g/cm³) for a material, defaulting to PLA."""
    return MATERIAL_DENSITIES.get(material_type.upper(), 1.24)


def calculate_cost(
    volume_cm3: float,
    config: PrintConfig,
    material_price_per_kg: float,
    electricity_price_per_kwh: float,
    machine_power_watts: float,
    profit_margin: float = 2.0,
    shell_factor: float = 0.5,
    quote: Optional[QuoteConfig] = None,
) -> CostEstimate:
    """Calculate printing cost estimate.

    Weight is estimated from model volume, material density, infill
    ratio and a shell factor (see below). Print time uses a volumetric
    flow model with an overhead factor.

    When ``quote`` is provided, the estimate is expanded with shop
    pricing: machine depreciation, labor, waste and a suggested retail
    price based on the configured margin. Otherwise it keeps the
    simple model (total = material + electricity, price = total *
    profit_margin).

    Shell model:
        effective_volume = volume * (shell_factor
                                     + (1 - shell_factor) * infill_ratio)

    Args:
        volume_cm3: Model volume in cubic centimeters
        config: Print configuration
        material_price_per_kg: Material cost per kilogram
        electricity_price_per_kwh: Electricity cost per kWh
        machine_power_watts: Printer power consumption in watts
        profit_margin: Profit multiplier for suggested price
        shell_factor: Fraction of material in solid outer shell
        quote: Optional shop-pricing parameters

    Returns:
        CostEstimate with cost breakdown
    """
    density = get_material_density(config.material_type)

    infill_ratio = config.infill_percentage / 100.0
    effective_ratio = shell_factor + (1.0 - shell_factor) * infill_ratio
    effective_volume = volume_cm3 * effective_ratio
    weight_grams = effective_volume * density

    # Volumetric flow: cross-section area (mm²) x speed (mm/s) x 3600 s/h
    cross_section_mm2 = config.layer_height * config.nozzle_diameter
    flow_mm3_per_h = cross_section_mm2 * config.print_speed_mm_s * 3600
    flow_cm3_per_h = flow_mm3_per_h / 1000.0

    overhead_factor = 1.3  # travel moves, heating, retractions
    print_time_hours = (volume_cm3 / flow_cm3_per_h) * overhead_factor

    material_cost = (weight_grams / 1000.0) * material_price_per_kg
    electricity_cost = (
        (machine_power_watts / 1000.0)
        * print_time_hours
        * electricity_price_per_kwh
    )

    if quote is not None:
        # Machine depreciation per hour of use
        machine_cost = (
            quote.machine_price / quote.machine_lifetime_hours
        ) * print_time_hours
        labor_cost = quote.labor_rate_per_hour * print_time_hours
        base = material_cost + electricity_cost + machine_cost + labor_cost
        waste_cost = base * quote.waste_factor
        total_cost = base + waste_cost
        suggested_price = total_cost * quote.profit_margin
        return CostEstimate(
            weight_grams=weight_grams,
            print_time_hours=print_time_hours,
            material_cost=material_cost,
            electricity_cost=electricity_cost,
            machine_cost=machine_cost,
            labor_cost=labor_cost,
            waste_cost=waste_cost,
            total_cost=total_cost,
            suggested_price=suggested_price,
        )

    total_cost = material_cost + electricity_cost
    suggested_price = total_cost * profit_margin

    return CostEstimate(
        weight_grams=weight_grams,
        print_time_hours=print_time_hours,
        material_cost=material_cost,
        electricity_cost=electricity_cost,
        total_cost=total_cost,
        suggested_price=suggested_price,
    )
