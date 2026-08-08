import typer
from pathlib import Path
from typing import List
from rich.console import Console

from print_doctor.mesh import analyze_mesh
from print_doctor.cost import calculate_cost
from print_doctor.report import generate_report
from print_doctor.diagnose import diagnose_photos, generate_diagnosis_report
from print_doctor.models import PrintConfig, Severity

app = typer.Typer(
    name="print-doctor",
    help="3D printing pre-flight check, cost estimation and defect diagnosis",
)
console = Console()


@app.command()
def check(
    model_path: str = typer.Argument(..., help="Path to STL/3MF file"),
    output: str = typer.Option(None, "-o", "--output", help="Output report path"),
    html: bool = typer.Option(False, "--html", help="Generate HTML report instead of Markdown"),
    material: str = typer.Option(
        "PLA", "-m", "--material", help="Material type (PLA/PETG/ABS/TPU)"
    ),
    price_per_kg: float = typer.Option(
        None, "-p", "--price", help="Material price per kg (defaults by material)"
    ),
    no_cost: bool = typer.Option(
        False, "--no-cost", help="Skip cost estimation"
    ),
) -> None:
    """Analyze a 3D model for printability issues."""
    try:
        console.print(f"[bold blue]Analyzing {model_path}...[/bold blue]")
        analysis = analyze_mesh(model_path)

        estimate = None
        if not no_cost and analysis.volume > 0:
            from print_doctor.cost import MATERIAL_PRICES

            price = price_per_kg if price_per_kg is not None else (
                MATERIAL_PRICES.get(material.upper(), 25.0)
            )
            config = PrintConfig(material_type=material)
            estimate = calculate_cost(
                volume_cm3=analysis.volume / 1000.0,  # mm3 -> cm3
                config=config,
                material_price_per_kg=price,
                electricity_price_per_kwh=0.12,
                machine_power_watts=200.0,
            )

        if html:
            from print_doctor.report import generate_html_report
            report = generate_html_report(analysis, estimate)
        else:
            report = generate_report(analysis, estimate)

        if output:
            Path(output).write_text(report)
            console.print(f"[bold green]Report saved to {output}[/bold green]")
        else:
            console.print(report)

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(code=1)

    if any(i.severity == Severity.ERROR for i in analysis.issues):
        raise typer.Exit(code=1)


@app.command()
def diagnose(
    photos: List[str] = typer.Argument(..., help="One or more print photos (jpg/png)"),
    output: str = typer.Option(None, "-o", "--output", help="Output report path"),
    material: str = typer.Option(None, "--material", help="Material hint (PLA/PETG/ABS/TPU)"),
    temperature: str = typer.Option(None, "--temperature", help="Nozzle temperature hint, e.g. 210"),
    retraction: str = typer.Option(None, "--retraction", help="Retraction hint: on/off"),
    cv: bool = typer.Option(False, "--cv", help="Use traditional CV detectors instead of the ML classifier"),
) -> None:
    """Diagnose a printed part from photos (stringing, warping, ...)."""
    try:
        hints = {}
        if material:
            hints["material"] = material
        if temperature:
            hints["temperature"] = temperature
        if retraction:
            hints["retraction"] = retraction

        diagnosis = diagnose_photos(photos, hints=hints, use_ml=not cv)
        report = generate_diagnosis_report(diagnosis)

        if output:
            Path(output).write_text(report)
            console.print(f"[bold green]Report saved to {output}[/bold green]")
        else:
            console.print(report)

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(code=1)

    if diagnosis.defects:
        raise typer.Exit(code=2)


@app.command()
def version() -> None:
    """Print version information."""
    from print_doctor import __version__
    console.print(f"Print Doctor v{__version__}")


@app.command()
def check_batch(
    models: List[str] = typer.Argument(..., help="Model files or directories"),
    output: str = typer.Option(None, "-o", "--output", help="Output summary path (md)"),
    material: str = typer.Option("PLA", "-m", "--material", help="Material type"),
) -> None:
    """Analyze multiple models and print a comparison summary."""
    paths: List[Path] = []
    for m in models:
        p = Path(m)
        if p.is_dir():
            paths.extend(sorted(p.glob("*.stl")) + sorted(p.glob("*.3mf")))
        else:
            paths.append(p)

    if not paths:
        console.print("[bold red]No model files found[/bold red]")
        raise typer.Exit(code=1)

    results = []
    for p in paths:
        try:
            analysis = analyze_mesh(str(p))
            results.append((p.name, analysis))
        except Exception as e:
            console.print(f"[yellow]Skipped {p.name}: {e}[/yellow]")

    from print_doctor.models import Severity

    lines = ["# Print Doctor Batch Summary", ""]
    lines.append("| Model | Score | Issues | Errors | Volume (cm3) |")
    lines.append("|---|---|---|---|---|")
    for name, a in sorted(results, key=lambda r: r[1].score):
        errors = sum(1 for i in a.issues if i.severity == Severity.ERROR)
        lines.append(
            f"| {name} | {a.score:.1f} | {len(a.issues)} | {errors} "
            f"| {a.volume / 1000.0:.1f} |"
        )
    lines.append("")

    summary = "\n".join(lines)
    if output:
        Path(output).write_text(summary)
        console.print(f"[bold green]Summary saved to {output}[/bold green]")
    else:
        console.print(summary)

    worst = min((a for _, a in results), key=lambda a: a.score, default=None)
    if worst and any(i.severity == Severity.ERROR for i in worst.issues):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
