# Contributing

Thanks for contributing to Print Doctor! Here's how to help.

## Ways to contribute

- **Report bugs** — open an issue with a minimal repro and the `print-doctor
  --version` output.
- **Improve the dataset** — add labeled photo URLs to
  `data/stackexchange_manifest.json` (or a custom manifest) so the classifier
  gets better. See `docs/dataset.md`.
- **Documentation** — the docs live in `docs/` (MkDocs Material).
- **Code** — see below.

## Setup

```bash
# Install with dev + vision deps
uv sync --group vision
uv run python tests/generate_fixtures.py
uv run python tests/generate_diagnose_fixtures.py

# Run tests
uv run pytest
```

## Guidelines

- **TDD** — write a failing test, then implement, then confirm green.
- **Keep it explainable** — every analysis conclusion must say *why*.
- **No heavy deps** — no PyTorch/TensorFlow as hard dependencies; anything
  optional must be marked and behind an extra.
- **Pure local** — no vendor cloud APIs. Everything must run offline.
- **`print-doctor` CLI** — new capabilities should be reachable from the CLI
  and documented in `docs/cli.md`.

## Code layout

```
src/print_doctor/
  cli.py          CLI commands
  mesh.py         printability checks
  models.py       data models
  cost.py         cost / quoting
  report.py       markdown/html/json reports
  quote_sheet.py  customer quote sheets
  vision.py       traditional CV detectors
  vision_ml.py    ML classifier wrapper
  features.py     shared image features
  diagnose.py     diagnosis pipeline
  attribution.py  root-cause rules
  monitor.py      real-time monitoring
scripts/          dataset fetch, training, screenshots, calibration
octoprint-print-doctor/   OctoPrint plugin (separate)
```

## Tests

```bash
uv run pytest                 # core
uv run python -m unittest octoprint-print-doctor.tests.test_plugin
```

## Commits

Use conventional commit style (`feat:`, `fix:`, `docs:`, `ci:`, `chore:`).

## License

By contributing you agree your code is licensed under MIT.
