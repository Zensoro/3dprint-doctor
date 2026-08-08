# Cost Model

Print Doctor estimates print cost with a configurable model, from a simple
estimate to full shop pricing.

## Weight

Real prints have solid outer perimeters and solid top/bottom layers (100%
infill) plus partial infill inside, so scaling volume by infill alone
understates weight. The model uses a shell factor:

```
effective_volume = volume * (shell_factor + (1 - shell_factor) * infill_ratio)
weight = effective_volume * density
```

`shell_factor` defaults to 0.5, calibrated against a 3DBenchy at 20% infill /
3 perimeters (~11g measured vs 10.9g estimated). It is size-dependent — see
[calibration](cost.md#calibration).

## Print time

Volumetric flow model:

```
flow_cm3/h = (layer_height × nozzle_diameter) × print_speed × 3600 / 1000
time = volume_cm3 / flow_cm3/h × 1.3   # 1.3 = travel/heating overhead
```

## Basic cost

```
total = material + electricity
price = total × profit_margin
```

## Full shop pricing (`--quote`)

With a `QuoteConfig`, the estimate adds:

| Component | Formula |
|---|---|
| Material | weight_kg × price_per_kg |
| Electricity | kW × time_h × price_per_kWh |
| Machine depreciation | (machine_price / lifetime_h) × time_h |
| Labor | labor_rate_per_hour × time_h |
| Waste allowance | (material + electricity + machine + labor) × waste_factor |
| **Total** | sum of the above |
| **Suggested price** | total × profit_margin |

## Configuration

`QuoteConfig` fields (defaults):

```python
QuoteConfig(
    electricity_price_per_kwh=0.12,
    machine_power_watts=200.0,
    machine_price=399.0,        # printer cost USD
    machine_lifetime_hours=5000.0,
    labor_rate_per_hour=8.0,
    waste_factor=0.05,
    profit_margin=2.0,
)
```

## Calibration

Weight and time estimates should be calibrated against your printer and
OrcaSlicer profile:

```bash
python scripts/calibrate.py models/benchy.stl models/other.stl
```

This slices each model with OrcaSlicer's CLI and prints a comparison table of
estimated vs sliced time and weight, so you can tune `shell_factor` and the
flow model.

## JSON schema

`check --json` emits a stable schema (version 1) with mesh stats, issues, and
an optional `cost` object:

```json
{
  "schema_version": 1,
  "filename": "benchy.stl",
  "printability_score": 60.0,
  "mesh": { "...": "..." },
  "issues": [ { "name": "...", "severity": "error" } ],
  "cost": {
    "weight_grams": 10.9,
    "print_time_hours": 1.1,
    "material_cost": 0.27,
    "electricity_cost": 0.03,
    "machine_cost": 0.09,
    "labor_cost": 8.8,
    "waste_cost": 0.46,
    "total_cost": 9.64,
    "suggested_price": 19.29
  }
}
```
