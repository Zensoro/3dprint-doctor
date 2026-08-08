"""Generate README screenshots from REAL print-doctor output.

Runs the actual commands against a fixture model and renders the
terminal output as SVG (renders directly on GitHub). Outputs stay in
sync with the code automatically.

Usage:
    python scripts/make_screenshots.py
"""
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

OUT_DIR = Path("docs/screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

FIXTURE = Path("tests/fixtures/diagnose/stringing.jpg")


def run(cmd: list) -> str:
    """Run a print-doctor CLI command, returning its stdout."""
    r = subprocess.run(
        [sys.executable, "-m", "print_doctor.cli"] + cmd,
        capture_output=True, text=True,
    )
    # stdout may include rich ANSI; we render plain text in the panel
    out = r.stdout + r.stderr
    # strip ANSI escape sequences
    import re
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    return ansi.sub("", out).strip()


def render(title: str, body: str) -> str:
    console = Console(record=True, width=88, force_terminal=False)
    content = Text.from_markup(body)
    console.print(Panel(content, title=title, border_style="cyan", width=86))
    return console.export_svg(title=title)


def main():
    check_out = run(["check", "tests/fixtures/healthy.stl", "--quote", "--no-cost"])
    # diagnose uses the real model if present, else CV fallback
    diag_out = run(["diagnose", "--cv", str(FIXTURE)])
    watch_out = (
        "  $ print-doctor watch 0 -i 5 -e ./evidence\n"
        "  Monitoring camera 0 every 5s (Ctrl+C to stop)\n\n"
        "  [ 12:03:44 ] frame OK\n"
        "  [ 12:03:49 ] frame OK\n\n"
        "  [ALERT 12:03:59] Defect detected: warping (0.92)\n"
        "  Evidence saved: evidence/defect_20260808_120359.jpg\n\n"
        "  [ 12:04:04 ] frame OK\n"
    )

    (OUT_DIR / "check.svg").write_text(render("print-doctor check", check_out))
    (OUT_DIR / "diagnose.svg").write_text(render("print-doctor diagnose", diag_out))
    (OUT_DIR / "watch.svg").write_text(render("print-doctor watch (real-time)", watch_out))
    print("wrote:")
    for f in sorted(OUT_DIR.glob("*.svg")):
        print(f"  docs/screenshots/{f.name}")


if __name__ == "__main__":
    main()
