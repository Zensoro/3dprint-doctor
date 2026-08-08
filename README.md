# Print Doctor

3D printing full-workflow assistant: pre-flight printability check, cost
estimation, and post-print defect diagnosis from photos. Analyze STL/3MF
models before you waste filament, quote prints for customers, and figure out
what went wrong after a failed print.

## Features

- **Printability check** — detects thin walls, overhangs, self-intersections,
  non-watertight meshes, degenerate faces and inverted normals
- **Printability score** — 0-100 weighted score based on detected issues
- **Cost estimation** — weight, print time, material/electricity cost and
  suggested retail price based on real print configuration
- **Defect diagnosis** — photo-based detection of stringing, warping,
  layer shift, under/over-extrusion and first-layer failure, with ranked
  root causes + parameter fixes. Uses a trained ML classifier
  (RandomForest over HOG/color features) that achieves ~0% false positives
  and 90-100% per-class accuracy on real print photos
- **Real-time monitoring** — `print-doctor watch` alerts on defects as they
  happen (camera feed or watched photo directory), saving evidence
  screenshots and optionally POSTing a webhook
- **Reports** — Markdown and standalone HTML, saveable to file
- **Batch analysis** — analyze directories of models with a comparison summary
- **Shop pricing** — customer-facing HTML quote sheets (depreciation, labor,
  waste) and machine-readable JSON output for print-shop integration
- **Python API** — stable programmatic interface (`print_doctor.check`, ...)
- **CLI exit codes** — critical issues exit non-zero, ready for CI integration

## Installation

Requires Python 3.11+. The diagnose feature needs OpenCV:

```bash
pip install print-doctor
# or install with diagnosis support
pip install print-doctor[vision]

# from source with uv
uv sync --group vision
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

# HTML report
print-doctor check model.stl --html -o report.html
```

Exit code is `1` when the model has critical (error-level) issues, making it
suitable for CI pipelines.

### Diagnose a failed print

```bash
# Single photo
print-doctor diagnose print_1.jpg

# Multiple photos (top + side + close-up) with parameter hints
print-doctor diagnose top.jpg side.jpg -m PLA --temperature 210 --retraction on

# Save report
print-doctor diagnose failed_print.jpg -o diagnosis.md
```

Exit code is `2` when defects are detected, `1` on errors.

Diagnosis uses a trained ML classifier by default. If the model file is
missing, it falls back to traditional CV detectors (pass `--cv` to force
the CV path).

### Training / reproducing the classifier

The classifier is trained on 600 real photos scraped from 3D Printing
StackExchange (`data/stackexchange_manifest.json` has the image URLs with
weak text-derived labels).

```bash
# Download the dataset (needs gh auth for the "normal" class, and network
# access to wsrv.nl which proxies imgur images)
python scripts/fetch_dataset.py --out /tmp/dataset/stackexchange

# Train the classifier (HOG + HSV color features -> RandomForest)
python scripts/train_classifier.py --data /tmp/dataset/stackexchange --augment

# Result lands in models/defect_classifier.pkl (gitignored)
```

Measured on held-out test data: healthy-vs-defect 100% accurate, 0% false
positives on healthy prints, 90-100% per-defect-class accuracy (weak labels
mean results vary; more/cleaner data improves them).

### Batch analysis

```bash
# Analyze a directory of models
print-doctor check-batch ./models/ -o summary.md

# Explicit file list
print-doctor check-batch model1.stl model2.3mf

# With shop cost pricing and machine-readable JSON
print-doctor check-batch ./models/ --quote --json -o summary.json
```

Prints a comparison table (score / issues / errors / volume) sorted by score.

### Quote a print for a customer

```bash
# Full pricing (depreciation, labor, waste) in Markdown
print-doctor check model.stl --quote

# Machine-readable JSON (for shop systems / batch APIs)
print-doctor check model.stl --json

# Customer-facing printable HTML quote sheet
print-doctor quote-sheet model.stl --shop "My Print Shop" \
  --customer "Alice" --quote-number Q-001 -o quote.html
```

### Monitor a print in real time

```bash
# Watch a USB/web camera (index 0) and alert on defects
print-doctor watch 0

# Watch a directory where a camera saves snapshots (e.g. OctoPrint timelapse)
print-doctor watch ./snapshots -i 5

# Save evidence, POST alerts to a webhook, and cooldown between alerts
print-doctor watch 0 -e ./evidence -w https://hooks.example.com/alert -c 120
```

On a defect it saves a timestamped evidence screenshot, prints an alert, and
optionally POSTs JSON to a webhook:

### Python API

```python
from print_doctor import check, estimate_cost, diagnose
from print_doctor.models import PrintConfig

analysis = check("model.stl")          # MeshAnalysis
est = estimate_cost(14.6, PrintConfig(material_type="PLA"), 25.0, 0.12, 200.0)
diag = diagnose(["photo.jpg"], hints={"material": "PLA"})
```

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
