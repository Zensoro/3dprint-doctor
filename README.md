# Print Doctor

3D printing pre-flight check and cost estimation tool. Analyze STL/3MF models
for printability issues before you waste filament, get a cost estimate for
print shops, and generate readable Markdown reports.

## Features

- **Printability check** — detects thin walls, overhangs, self-intersections,
  non-watertight meshes, degenerate faces and inverted normals
- **Printability score** — 0-100 weighted score based on detected issues
- **Cost estimation** — weight, print time, material/electricity cost and
  suggested retail price based on real print configuration
- **Markdown reports** — human-readable output with severity levels and
  actionable suggestions, saveable to file
- **CLI exit codes** — critical issues exit non-zero, ready for CI integration

## Installation

Requires Python 3.11+.

```bash
# with Poetry
poetry install
poetry run print-doctor version

# or with uv
uv sync
uv run print-doctor version
```

## Usage

### Check a model

```bash
# Basic analysis with cost estimation (PLA defaults)
print-doctor check model.stl

# Choose material and price
print-doctor check model.stl -m PETG -p 30

# Save report to file
print-doctor check model.stl -o report.md

# Skip cost estimation
print-doctor check model.stl --no-cost
```

Exit code is `1` when the model has critical (error-level) issues, making it
suitable for CI pipelines.

### Supported file formats

- STL (stereolithography)
- 3MF (3D Manufacturing Format)

### Materials

PLA, PETG, ABS, TPU, Nylon — with built-in density and default price tables
(see `config/materials.yaml` and `src/print_doctor/cost.py`).

## Cost model calibration

The weight estimate models solid outer perimeters plus partial infill via a
`shell_factor` (default 0.5, calibrated against a 3DBenchy at 20% infill /
3 perimeters: estimated 10.9g vs ~11g measured). Print time uses a volumetric
flow model with a 1.3x overhead factor.

For exact calibration against your printer and OrcaSlicer profile, run:

```bash
python scripts/calibrate.py models/benchy.stl models/other.stl
```

This slices each model with OrcaSlicer's CLI and prints a comparison table of
estimated vs sliced time and weight, so you can tune `shell_factor` and the
flow model to your setup.

## Example output

```markdown
# Print Doctor Report: model.stl

## Printability Score: 85.0/100

## Mesh Information
- **Watertight:** yes
- **Manifold:** yes
- **Triangles:** 1,234
- **Volume:** 12.34 cm3
- **Surface Area:** 45.67 cm2
- **Bounding Box:** 10.0 x 20.0 x 30.0 mm

## Issues Found

### [WARNING] thin_wall
- **Description:** Found thin wall regions: 45/500 sample points (9.0%) ...
- **Location:** 9.0% of sampled surface
- **Suggestion:** Increase wall thickness to at least 0.80mm ...

## Cost Estimate
- **Weight:** 15.3g
- **Print Time:** 1.2 hours
- **Material Cost:** $0.38
- **Electricity Cost:** $0.03
- **Total Cost:** $0.41
- **Suggested Price:** $0.82
```

## Development

```bash
poetry install --with dev
poetry run pytest
```

Generate E2E fixture models:

```bash
python tests/generate_fixtures.py
```

## License

MIT License
