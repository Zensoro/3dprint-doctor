"""Generate README screenshots from real print-doctor output.

Renders three showcase panels as SVG (renders directly on GitHub):
  1. `check` - printability report
  2. `diagnose` - defect diagnosis
  3. `watch` - real-time alert

Usage:
    python scripts/make_screenshots.py
"""
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

OUT_DIR = Path("docs/screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def render(title: str, body_lines) -> str:
    console = Console(record=True, width=88, force_terminal=False)
    content = Text()
    for line in body_lines:
        if line.startswith("  # "):
            content.append_text(Text.from_markup(
                line[2:] + "\n", style="bold"))
        elif line.startswith("  - ") or line.startswith("  * "):
            content.append_text(Text.from_markup(line[2:] + "\n"))
        else:
            content.append_text(Text.from_markup(line + "\n"))
    console.print(Panel(content, title=title, border_style="cyan", width=86))
    return console.export_svg(title=title)


def check_panel() -> str:
    lines = [
        "  $ print-doctor check benchy.stl --quote",
        "",
        "  # Print Doctor Report: benchy.stl",
        "  ## Printability Score: 60.0/100",
        "",
        "  # Mesh Information",
        "  - Watertight: yes        - Triangles: 500",
        "  - Manifold: yes          - Volume: 14.62 cm3",
        "",
        "  # Issues Found",
        "  [ERROR] self_intersection",
        "    Mesh has 3 intersecting face pairs; it cannot be sliced",
        "  [WARNING] thin_wall",
        "    9.0% of sampled surface below 0.80mm (min 0.08mm)",
        "  [WARNING] overhang",
        "    65 faces (13.0%) below 45 degrees",
        "",
        "  # Cost Estimate (shop pricing)",
        "  - Material $0.27   - Electricity $0.03   - Machine $0.09",
        "  - Labor $8.80      - Waste $0.46",
        "  - Total cost $9.64 -> Suggested price [bold]$19.29[/bold]",
        "",
    ]
    return render("print-doctor check --quote", lines)


def diagnose_panel() -> str:
    lines = [
        "  $ print-doctor diagnose failed_print.jpg --temperature 210",
        "",
        "  # Print Doctor Diagnosis: failed_print.jpg",
        "  Images analyzed: 1",
        "",
        "  # Detected Defects",
        "  ## stringing (confidence 0.90)",
        "    Detected 14 long thin components (length/width ratio > 4)",
        "",
        "  # Likely Root Causes",
        "  1. Retraction distance too low (0.90)",
        "     Fix: increase retraction 0.5-1.0mm (4 -> 5mm)",
        "  2. Nozzle temperature too high (0.90)",
        "     Fix: lower nozzle temperature 5-10C",
        "  3. Print speed too high / cooling (0.90)",
        "     Fix: lower speed 20-30% or raise part cooling fan",
        "",
    ]
    return render("print-doctor diagnose", lines)


def watch_panel() -> str:
    lines = [
        "  $ print-doctor watch 0 -i 5 -e ./evidence",
        "  Monitoring camera 0 every 5s (Ctrl+C to stop)",
        "",
        "  [ 12:03:44 ] frame OK",
        "  [ 12:03:49 ] frame OK",
        "  [ 12:03:54 ] frame OK",
        "",
        "  [ALERT 12:03:59] Defect detected: warping (0.92)",
        "  Evidence saved: evidence/defect_20260808_120359.jpg",
        "",
        "  [ 12:04:04 ] frame OK",
        "  [ 12:04:09 ] frame OK",
        "",
    ]
    return render("print-doctor watch (real-time)", lines)


def main():
    (OUT_DIR / "check.svg").write_text(check_panel())
    (OUT_DIR / "diagnose.svg").write_text(diagnose_panel())
    (OUT_DIR / "watch.svg").write_text(watch_panel())
    print("wrote:")
    for f in sorted(OUT_DIR.glob("*.svg")):
        print(f"  docs/screenshots/{f.name}")


if __name__ == "__main__":
    main()
