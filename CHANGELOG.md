# Changelog

All notable changes to Print Doctor are documented here.

## [0.7.0] - 2026-08-08

### Added
- Plugin architecture: `MeshDetector` interface, registry, and entry-point
  discovery (`print_doctor.detectors` group).
- Built-in detectors refactored to plugin classes.
- `check --detector` filter + `detectors` CLI command.
- MkDocs documentation site (10 pages, GitHub Pages).
- Auto-release workflow (tag → build → PyPI → GitHub Release).
- Community files: CHANGELOG, CONTRIBUTING, issue/PR templates.

## [0.6.0] - 2026-08-08

### Added
- OctoPrint plugin (`octoprint-print-doctor/`): monitor on print start, tab
  alerts, optional pause-on-defect.
- `watch` supports http(s) snapshot URLs with basic auth — Moonraker (Klipper)
  webcam integration.
- `docs/screenshots/` generated from real command output (README showcase).

## [0.5.0] - 2026-08-08

### Added
- `print-doctor watch` — real-time print monitoring (camera, directory, URL).
- Alert pipeline: evidence screenshot, console, optional webhook JSON.
- Cooldown to prevent alert spam.

## [0.4.0] - 2026-08-08

### Added
- Shop pricing model (`QuoteConfig`): machine depreciation, labor, waste,
  profit margin.
- `check --json` machine-readable output (stable schema).
- `check-batch --json / --quote`.
- `quote-sheet` — customer-facing printable HTML quote.

## [0.3.0] - 2026-08-08

### Added
- ML defect classifier (RandomForest over HOG/color features) trained on 600
  real StackExchange photos. 0% false positives, 90-100% per-class accuracy.
- `scripts/fetch_dataset.py`, `scripts/train_classifier.py`,
  `data/stackexchange_manifest.json`.
- ML model is the default diagnosis path; CV detectors kept as `--cv` fallback.

## [0.2.0] - 2026-08-07

### Added
- Defect diagnosis (`diagnose`) with 6 CV detectors + synthetic fixtures.
- HTML reports (`check --html`).
- Batch analysis (`check-batch`).
- Stable Python API (`print_doctor.check / estimate_cost / diagnose`).
- OpenCV as optional `[vision]` extra.

## [0.1.0] - 2026-08-07

### Added
- Printability check (8 detectors) + 0-100 score.
- Cost estimation (weight, time, material, electricity, price).
- Markdown reports.
- `print-doctor` CLI.
- GitHub Actions CI.
