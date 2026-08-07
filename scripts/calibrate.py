"""Calibrate print-doctor cost estimates against OrcaSlicer.

Usage:
    python scripts/calibrate.py <model.stl> [more models...]

Requirements:
    - OrcaSlicer installed (macOS: /Applications/OrcaSlicer.app)
    - print-doctor installed (poetry run or pip install -e .)

Outputs a comparison table of print-doctor estimates vs OrcaSlicer
slicing results (time and filament weight).
"""
import argparse
import re
import subprocess
import tempfile
from pathlib import Path

from print_doctor.cost import calculate_cost
from print_doctor.mesh import load_mesh
from print_doctor.models import PrintConfig

ORCA_SLICE_BIN = "/Applications/OrcaSlicer.app/Contents/MacOS/orca-slicer"

# Default profile matching PrintConfig defaults:
# 0.2mm layer height, 0.4mm nozzle, PLA, 20% infill
DEFAULT_CONFIG = """
[print]
layer_height = 0.2
perimeters = 3
infill = 20%
infill_pattern = grid
brim_width = 0

[filament]
filament_colour = #FF8000
filament_density = 1.24
filament_type = PLA

[printer]
nozzle_diameter = 0.4
bed_shape = 220x220x250
z_offset = 0
"""
# NOTE: real OrcaSlicer configs are more complex; this is a simplified
# stand-in. For accurate calibration, export a config from OrcaSlicer:
#   File -> Export -> Export Config
# and pass it via --config <path>.


def find_orca_slicer() -> str | None:
    if Path(ORCA_SLICE_BIN).exists():
        return ORCA_SLICE_BIN
    import shutil
    return shutil.which("orca-slicer")


def slice_model(orca_bin: str, model: Path, config: Path, out_dir: Path) -> Path:
    """Run OrcaSlicer CLI in slice mode, return gcode path."""
    result = subprocess.run(
        [
            orca_bin, "--export-gcode",
            "--config", str(config),
            "-o", str(out_dir / f"{model.stem}.gcode"),
            str(model),
        ],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"OrcaSlicer failed: {result.stderr[-500:]}")
    gcode = out_dir / f"{model.stem}.gcode"
    if not gcode.exists():
        raise RuntimeError("OrcaSlicer produced no gcode")
    return gcode


def parse_gcode_stats(gcode: Path) -> dict:
    """Extract estimated time and filament weight from gcode headers."""
    text = gcode.read_text(errors="ignore")
    stats = {}

    # OrcaSlicer writes e.g. "; estimated printing time (normal mode) = 1h 2m 34s"
    m = re.search(r"estimated printing time[^\n]*=\s*([0-9hms ]+)", text)
    if m:
        parts = re.findall(r"(\d+)([hms])", m.group(1))
        seconds = 0
        for value, unit in parts:
            seconds += int(value) * {"h": 3600, "m": 60, "s": 1}[unit]
        stats["time_hours"] = seconds / 3600

    # "; filament used [g] = 12.34"
    m = re.search(r"filament used\s*\[g\]\s*=\s*([\d.]+)", text)
    if m:
        stats["weight_grams"] = float(m.group(1))

    return stats


def estimate_with_doctor(model: Path) -> dict:
    """Run print-doctor's own estimation on the model."""
    mesh = load_mesh(str(model))
    volume_cm3 = float(mesh.volume) / 1000.0
    config = PrintConfig()  # matches slicer defaults above
    est = calculate_cost(
        volume_cm3=volume_cm3,
        config=config,
        material_price_per_kg=25.0,
        electricity_price_per_kwh=0.12,
        machine_power_watts=200.0,
    )
    return {
        "volume_cm3": volume_cm3,
        "time_hours": est.print_time_hours,
        "weight_grams": est.weight_grams,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", nargs="+", type=Path)
    parser.add_argument("--config", type=Path, default=None,
                        help="OrcaSlicer config file (default: built-in)")
    args = parser.parse_args()

    orca = find_orca_slicer()
    if orca is None:
        print("OrcaSlicer not found. Install it first:")
        print("  brew install --cask orcaslicer")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)

        if args.config is None:
            config = out_dir / "profile.ini"
            config.write_text(DEFAULT_CONFIG)
        else:
            config = args.config

        print(f"{'Model':<24} {'Dr.Weight':>10} {'SliceWt':>10} {'WtErr%':>8} "
              f"{'Dr.Time':>9} {'SliceT':>9} {'TErr%':>8}")
        print("-" * 80)

        for model in args.models:
            if not model.exists():
                print(f"{model.name:<24} MISSING")
                continue
            try:
                doctor = estimate_with_doctor(model)
                gcode = slice_model(orca, model, config, out_dir)
                stats = parse_gcode_stats(gcode)

                wt_err = None
                if "weight_grams" in stats and stats["weight_grams"] > 0:
                    wt_err = (doctor["weight_grams"] - stats["weight_grams"]) \
                        / stats["weight_grams"] * 100

                t_err = None
                if "time_hours" in stats and stats["time_hours"] > 0:
                    t_err = (doctor["time_hours"] - stats["time_hours"]) \
                        / stats["time_hours"] * 100

                print(f"{model.name:<24} {doctor['weight_grams']:>10.1f} "
                      f"{stats.get('weight_grams', 0):>10.1f} "
                      f"{wt_err:>7.1f}% " if wt_err is not None
                      else f"{model.name:<24} {doctor['weight_grams']:>10.1f} "
                           f"{'N/A':>10} {'N/A':>8} "
                           f"{doctor['time_hours']:>9.1f} {'N/A':>9} {'N/A':>8}")
                if wt_err is not None:
                    print(f"{'':<24} {'':>10} {'':>10} "
                          f"{doctor['time_hours']:>9.1f} "
                          f"{stats.get('time_hours', 0):>9.1f} "
                          f"{t_err:>7.1f}%" if t_err is not None else "")
            except Exception as e:
                print(f"{model.name:<24} ERROR: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
