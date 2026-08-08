<div align="center">

# 🩺 3DPrint Doctor

**The complete 3D printing assistant — check, quote, monitor, and diagnose.**

One CLI that covers a print's full lifecycle: pre-flight printability check
and cost quoting, real-time defect monitoring while printing, and photo-based
defect diagnosis after a failure.

[![PyPI version](https://img.shields.io/pypi/v/print-doctor.svg?style=flat-square)](https://pypi.org/project/print-doctor/)
[![PyPI downloads](https://img.shields.io/pypi/dm/print-doctor.svg?style=flat-square)](https://pypi.org/project/print-doctor/)
[![CI](https://github.com/Zensoro/3dprint-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/Zensoro/3dprint-doctor/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?style=flat-square)](https://www.python.org/)

*Analyze STL/3MF models before you waste filament, quote prints for customers,
catch failures while they happen, and figure out what went wrong after.*

</div>

---

## Why you need it

- **Netfabb shut down.** Autodesk retired its mesh-repair tool and there is no
  modern free replacement for *printability pre-check* — until now.
- **"Upload and print" fails.** Non-manifold meshes, thin walls, overhangs and
  holes waste hours of print time and filament.
- **Print shops quote by hand.** Weight, time, material, electricity and labor
  estimated manually — slow and inconsistent.
- **Failed prints stay a mystery.** Stringing? Warping? Z-band? New users stare
  at a failed part and don't know which knob to turn.

Print Doctor answers all three: **is this model printable? what does it cost?
what went wrong?**

## One CLI, three moments of a print

| Moment | Command | What it does |
|---|---|---|
| 🛠 **Before** | `print-doctor check` | 8 printability checks, 0-100 score, cost quote |
| 👁 **During** | `print-doctor watch` | real-time defect alerts (camera / webcam URL) |
| 🔍 **After** | `print-doctor diagnose` | ML photo diagnosis + root-cause fixes |

## Showcase

| | |
|---|---|
| **Check & quote** (before printing) | **Diagnose** (after a failure) |
| <img src="docs/screenshots/check.svg" alt="print-doctor check" width="420"> | <img src="docs/screenshots/diagnose.svg" alt="print-doctor diagnose" width="420"> |
| **Watch** (during printing) | |
| <img src="docs/screenshots/watch.svg" alt="print-doctor watch" width="420"> | |

## Features

### Printability check (`check`)
Detects **non-watertight meshes, non-manifold edges, inverted normals,
degenerate faces, thin walls (ray-cast), overhangs, self-intersections,
isolated components and sliver triangles** — each with a severity level and an
actionable fix. Outputs a 0-100 score.

### Cost quoting (`check --quote`, `quote-sheet`)
Full shop pricing: material, electricity, **machine depreciation, labor,
waste allowance** and a suggested retail price. Emits Markdown, HTML, or
machine-readable **JSON** — print-shop ready.

### Real-time monitoring (`watch`)
Samples a webcam, a watched directory, or a **Moonraker (Klipper) snapshot
URL**, classifies each frame with ML, and alerts on defects — saving an
evidence screenshot and optionally POSTing a webhook. Ships with an
**OctoPrint plugin** (`octoprint-print-doctor/`) that can pause the print on
defect.

### Photo diagnosis (`diagnose`)
Trained on **600 real photos** from 3D Printing StackExchange. Classifies
stringing, warping, layer shift, under/over-extrusion and first-layer failure,
then explains *why* and *what to change*. Measured: **0% false positives on
healthy prints, 90-100% per-class accuracy.**

### Shop & batch workflows
- `check-batch` — analyze directories, sortable comparison table
- `--json` — stable machine-readable schema (integration / APIs)
- `quote-sheet` — customer-facing printable HTML quote
- Exit codes for CI (critical issues → exit 1; defects → exit 2)

## Quick start

```bash
pip install print-doctor

# Check a model (printability score + cost estimate)
print-doctor check model.stl

# Diagnose a failed print from a photo
print-doctor diagnose failed_print.jpg

# Monitor your printer's webcam in real time
print-doctor watch 0
```

Requires Python 3.11+. Diagnosis needs OpenCV: `pip install print-doctor[vision]`.

## How it compares

| Capability | **Print Doctor** | Netfabb (retired) | Orca/Prusa slicers |
|---|---|---|---|
| Pre-print printability check | ✅ | ✅ (gone) | ⚠ basic |
| Cost / shop quoting | ✅ | ❌ | ⚠ partial |
| Real-time defect alerts | ✅ | ❌ | ❌ |
| Photo defect diagnosis | ✅ | ❌ | ❌ |
| Batch / API integration | ✅ | ❌ | ❌ |
| Free & open source | ✅ | ❌ | ✅ |

## Full usage

### Check a model

```bash
print-doctor check model.stl                    # analysis + cost (PLA)
print-doctor check model.stl -m PETG -p 30      # pick material/price
print-doctor check model.stl -o report.md       # save report
print-doctor check model.stl --html -o r.html   # HTML report
print-doctor check model.stl --json             # machine-readable JSON
print-doctor check model.stl --quote            # full shop pricing
```

Exit code `1` when the model has critical issues → CI friendly.

### Diagnose a failed print

```bash
print-doctor diagnose print_1.jpg
print-doctor diagnose top.jpg side.jpg -m PLA --temperature 210
print-doctor diagnose failed_print.jpg -o diagnosis.md
```

Exit code `2` when defects are detected.

### Monitor in real time

```bash
print-doctor watch 0                                      # webcam
print-doctor watch ./snapshots -i 5                       # photo dir
print-doctor watch "http://printer:7125/server/webcams/snapshot?name=webcam" \
  -i 5 -e ./evidence -w https://hooks.example.com/alert   # Moonraker
```

### Quote for a customer

```bash
print-doctor quote-sheet model.stl --shop "My Print Shop" \
  --customer "Alice" --quote-number Q-001 -o quote.html
```

### Batch analysis

```bash
print-doctor check-batch ./models/ --quote --json -o summary.json
```

## Python API

```python
from print_doctor import check, estimate_cost, diagnose

analysis = check("model.stl")                    # MeshAnalysis
est = estimate_cost(14.6, PrintConfig(material_type="PLA"), 25.0, 0.12, 200.0)
diag = diagnose(["photo.jpg"], hints={"material": "PLA"})
```

## Reproducing the ML classifier

Trained on 600 real photos (URLs + weak labels in
`data/stackexchange_manifest.json`):

```bash
python scripts/fetch_dataset.py --out /tmp/dataset/stackexchange
python scripts/train_classifier.py --data /tmp/dataset/stackexchange --augment
```

Healthy-vs-defect detection is ~100% accurate with 0% false positives;
per-defect-class accuracy 90-100% (weak labels → more/cleaner data improves it).

## Print-farm integration

- **OctoPrint** — see `octoprint-print-doctor/` for a plugin (monitor on print
  start, tab alerts, optional pause-on-defect).
- **Klipper / Moonraker** — point `watch` at the webcam snapshot URL (see
  `octoprint-print-doctor/README.md`).

## Development

```bash
uv sync --group vision
uv run pytest
uv run python tests/generate_fixtures.py
uv run python tests/generate_diagnose_fixtures.py
```

## License

MIT License
