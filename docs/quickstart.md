# Quick Start

## Install

Requires Python 3.11+.

```bash
# Install with diagnosis support (recommended)
pip install print-doctor[vision]

# Or minimal
pip install print-doctor
```

!!! note
    The `[vision]` extra adds OpenCV, needed for `diagnose` and `watch`.

## Check a model

```bash
# Analysis + cost estimate (PLA default)
print-doctor check model.stl

# Pick material and price
print-doctor check model.stl -m PETG -p 30

# Save report
print-doctor check model.stl -o report.md

# Full shop pricing (depreciation, labor, waste)
print-doctor check model.stl --quote
```

Exit code is `1` when the model has critical issues — CI friendly.

## Diagnose a failed print

```bash
print-doctor diagnose failed_print.jpg
print-doctor diagnose top.jpg side.jpg -m PLA --temperature 210
print-doctor diagnose failed_print.jpg -o diagnosis.md
```

Exit code `2` when defects are detected.

## Monitor a live print

```bash
# USB/web camera
print-doctor watch 0

# A photo directory (e.g. OctoPrint timelapse)
print-doctor watch ./snapshots -i 5

# Moonraker (Klipper) webcam snapshot
print-doctor watch "http://printer:7125/server/webcams/snapshot?name=webcam" \
  -i 5 -e ./evidence -w https://hooks.example.com/alert
```

## Quote for a customer

```bash
print-doctor quote-sheet model.stl --shop "My Print Shop" \
  --customer "Alice" --quote-number Q-001 -o quote.html
```

## What's next

- Full [CLI reference](cli.md)
- How the [printability checks](algorithms.md) work
- Reproduce the [ML classifier](training.md)
