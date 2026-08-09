# CLI Reference

The `print-doctor` command is built with Typer. Run
`print-doctor --help` or `print-doctor <command> --help` for usage.

## `check`

Analyze a 3D model for printability and estimate cost.

```bash
print-doctor check <model.stl|model.3mf> [options]
```

| Option | Description |
|---|---|
| `-o, --output` | Save report to file (Markdown by default) |
| `--html` | Generate HTML report |
| `--json` | Generate machine-readable JSON (stable schema) |
| `-m, --material` | Material type (PLA/PETG/ABS/TPU/Nylon) |
| `-p, --price` | Material price per kg (defaults by material) |
| `--quote` | Full shop pricing (depreciation, labor, waste) |
| `--no-cost` | Skip cost estimation |

Exit codes: `0` OK, `1` critical issues or error.

## `diagnose`

Diagnose a printed part from photos.

```bash
print-doctor diagnose <photo1.jpg> [photo2.jpg ...] [options]
```

| Option | Description |
|---|---|
| `-o, --output` | Save diagnosis report |
| `--material` | Material hint (PLA/PETG/ABS/TPU) |
| `--temperature` | Nozzle temperature hint |
| `--retraction` | Retraction hint (on/off) |
| `--cv` | Force traditional CV detectors instead of ML |

Exit codes: `0` no defects, `1` error, `2` defects detected.

## `watch`

Monitor a camera, directory, or webcam URL for defects in real time.

```bash
print-doctor watch <source> [options]
```

`source` is a camera index (`0`), a directory path, or an `http(s)` snapshot URL.

| Option | Description |
|---|---|
| `-i, --interval` | Seconds between frame checks (default 5) |
| `-e, --evidence-dir` | Directory for evidence screenshots |
| `-c, --cooldown` | Seconds before re-alerting (default 60) |
| `-w, --webhook` | POST JSON alert to this URL on defect |
| `-d, --duration` | Stop after N seconds (testing) |
| `-u, --user` | Basic auth user (URL sources) |
| `-P, --password` | Basic auth password (URL sources) |

## `check-batch`

Analyze multiple models.

```bash
print-doctor check-batch <file|dir>... [options]
```

| Option | Description |
|---|---|
| `-o, --output` | Save summary |
| `--json` | Machine-readable JSON output |
| `--quote` | Include cost pricing columns |
| `-m, --material` | Material type |

## `quote-sheet`

Generate a customer-facing HTML quote sheet.

```bash
print-doctor quote-sheet <model> [options]
```

| Option | Description |
|---|---|
| `-o, --output` | Output HTML path (default `quote.html`) |
| `--shop` | Shop name |
| `--contact` | Shop contact info |
| `--customer` | Customer name |
| `--quote-number` | Quote reference |
| `--notes` | Free-text notes |
| `-m, --material` | Material type |
| `-p, --price` | Material price per kg |

## `version`

Print version information.

```bash
print-doctor version
```

## `repair`

Repair common mesh issues (normals, winding, stitch, degenerate faces).

```bash
print-doctor repair <model.stl> [options]
```

| Option | Description |
|---|---|
| `-o, --output` | Save fixed model to file |
| `--no-normals` | Skip normal fix |
| `--no-winding` | Skip winding fix |
| `--no-stitch` | Skip stitch |
| `--no-degenerate` | Skip degenerate-face removal |

Reports before/after stats and honestly lists issues it cannot fix (large
holes, self-intersections).

## `gcode-info`

Analyze a sliced G-code file.

```bash
print-doctor gcode-info <model.gcode> [options]
```

| Option | Description |
|---|---|
| `-e, --e-position` | Current E position to locate (shows layer + progress %) |

Supports OrcaSlicer/PrusaSlicer (`;LAYER_CHANGE`) and Bambu Studio
(`;LAYER:n`) markers.
