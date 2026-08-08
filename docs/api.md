# Python API

The `print_doctor` package exposes a stable programmatic interface.

## Core functions

```python
from print_doctor import check, estimate_cost, diagnose
from print_doctor.models import PrintConfig, QuoteConfig

# Analyze a mesh
analysis = check("model.stl")
# -> MeshAnalysis(filename, is_watertight, is_manifold, triangle_count,
#                 volume, surface_area, bounding_box, issues, score)

# Estimate cost
est = estimate_cost(
    14.6,                             # volume cm3
    PrintConfig(material_type="PLA"),
    25.0,                             # price per kg
    0.12,                             # electricity per kWh
    200.0,                            # machine watts
    quote=QuoteConfig(),              # optional shop pricing
)
# -> CostEstimate(weight_grams, print_time_hours, material_cost,
#                 electricity_cost, machine_cost, labor_cost,
#                 waste_cost, total_cost, suggested_price)

# Diagnose a print from photos
diag = diagnose(["photo.jpg"], hints={"material": "PLA"})
# -> Diagnosis(filename, defects, root_causes, image_count)
```

## Data models

| Class | Fields |
|---|---|
| `MeshAnalysis` | filename, is_watertight, is_manifold, triangle_count, volume (mm³), surface_area (mm²), bounding_box, issues, score |
| `Issue` | name, description, severity, location, suggestion |
| `Severity` | ERROR / WARNING / INFO |
| `CostEstimate` | weight_grams, print_time_hours, material/electricity/machine/labor/waste cost, total_cost, suggested_price |
| `PrintConfig` | layer_height, infill_percentage, material_type, nozzle_diameter, print_speed_mm_s, bed/nozzle temperature |
| `QuoteConfig` | electricity_price_per_kwh, machine_power_watts, machine_price, machine_lifetime_hours, labor_rate_per_hour, waste_factor, profit_margin |
| `Diagnosis` | filename, defects, root_causes, image_count |
| `Defect` | type, confidence, evidence |
| `RootCause` | cause, likelihood, fix |

## Real-time monitoring

```python
from print_doctor.monitor import PrintMonitor

monitor = PrintMonitor(interval_seconds=5, evidence_dir="evidence")
defects = monitor.check_frame(frame)     # frame: BGR numpy array
# monitor.run_camera(0)
# monitor.run_directory("snapshots")
# monitor.run_url("http://.../snapshot")
```

## Full list

```python
import print_doctor
print_doctor.__all__
```
