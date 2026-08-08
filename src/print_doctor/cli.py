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
    json: bool = typer.Option(False, "--json", help="Generate machine-readable JSON report"),
    material: str = typer.Option(
        "PLA", "-m", "--material", help="Material type (PLA/PETG/ABS/TPU)"
    ),
    price_per_kg: float = typer.Option(
        None, "-p", "--price", help="Material price per kg (defaults by material)"
    ),
    quote: bool = typer.Option(
        False, "--quote", help="Use full shop pricing (depreciation, labor, waste)"
    ),
    no_cost: bool = typer.Option(
        False, "--no-cost", help="Skip cost estimation"
    ),
) -> None:
    """Analyze a 3D model for printability issues."""
    try:
        if not json:
            console.print(f"[bold blue]Analyzing {model_path}...[/bold blue]")
        analysis = analyze_mesh(model_path)

        estimate = None
        if not no_cost and analysis.volume > 0:
            from print_doctor.cost import MATERIAL_PRICES
            from print_doctor.models import QuoteConfig

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
                quote=QuoteConfig() if quote else None,
            )

        if json:
            from print_doctor.report import generate_json_report
            report = generate_json_report(analysis, estimate)
        elif html:
            from print_doctor.report import generate_html_report
            report = generate_html_report(analysis, estimate)
        else:
            report = generate_report(analysis, estimate)

        if output:
            Path(output).write_text(report)
            if not json:
                console.print(f"[bold green]Report saved to {output}[/bold green]")
        elif json:
            print(report)  # raw JSON to stdout for piping
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
def quote_sheet(
    model_path: str = typer.Argument(..., help="Path to STL/3MF file"),
    output: str = typer.Option("quote.html", "-o", "--output", help="Output HTML path"),
    shop: str = typer.Option("Print Doctor Shop", "--shop", help="Shop name"),
    contact: str = typer.Option("", "--contact", help="Shop contact info"),
    customer: str = typer.Option("", "--customer", help="Customer name"),
    quote_number: str = typer.Option("", "--quote-number", help="Quote reference"),
    notes: str = typer.Option("", "--notes", help="Free-text notes"),
    material: str = typer.Option("PLA", "-m", "--material", help="Material type"),
    price_per_kg: float = typer.Option(None, "-p", "--price", help="Material price per kg"),
) -> None:
    """Generate a customer-facing HTML quote sheet."""
    from print_doctor.cost import MATERIAL_PRICES, calculate_cost
    from print_doctor.models import PrintConfig, QuoteConfig
    from print_doctor.quote_sheet import generate_quote_sheet

    try:
        analysis = analyze_mesh(model_path)
        price = price_per_kg if price_per_kg is not None else (
            MATERIAL_PRICES.get(material.upper(), 25.0)
        )
        estimate = None
        if analysis.volume > 0:
            estimate = calculate_cost(
                volume_cm3=analysis.volume / 1000.0,
                config=PrintConfig(material_type=material),
                material_price_per_kg=price,
                electricity_price_per_kwh=0.12,
                machine_power_watts=200.0,
                quote=QuoteConfig(),
            )
        html = generate_quote_sheet(
            analysis, estimate,
            shop_name=shop, shop_contact=contact,
            customer=customer, quote_number=quote_number, notes=notes,
        )
        Path(output).write_text(html)
        console.print(f"[bold green]Quote sheet saved to {output}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Print version information."""
    from print_doctor import __version__
    console.print(f"Print Doctor v{__version__}")


@app.command()
def check_batch(
    models: List[str] = typer.Argument(..., help="Model files or directories"),
    output: str = typer.Option(None, "-o", "--output", help="Output summary path (md)"),
    json: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
    quote: bool = typer.Option(False, "--quote", help="Include shop cost pricing"),
    material: str = typer.Option("PLA", "-m", "--material", help="Material type"),
) -> None:
    """Analyze multiple models and print a comparison summary."""
    from print_doctor.cost import MATERIAL_PRICES, calculate_cost
    from print_doctor.models import PrintConfig, QuoteConfig, Severity

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

    price = MATERIAL_PRICES.get(material.upper(), 25.0)
    results = []
    for p in paths:
        try:
            analysis = analyze_mesh(str(p))
            estimate = None
            if quote and analysis.volume > 0:
                estimate = calculate_cost(
                    volume_cm3=analysis.volume / 1000.0,
                    config=PrintConfig(material_type=material),
                    material_price_per_kg=price,
                    electricity_price_per_kwh=0.12,
                    machine_power_watts=200.0,
                    quote=QuoteConfig(),
                )
            results.append((p.name, analysis, estimate))
        except Exception as e:
            console.print(f"[yellow]Skipped {p.name}: {e}[/yellow]")

    if json:
        import json as _json
        data = {"models": []}
        for name, a, est in sorted(results, key=lambda r: r[1].score):
            item = {
                "filename": name,
                "printability_score": round(a.score, 2),
                "issues": len(a.issues),
                "errors": sum(1 for i in a.issues if i.severity == Severity.ERROR),
                "volume_cm3": round(a.volume / 1000.0, 3),
            }
            if est is not None:
                item["cost"] = {
                    "total_cost": round(est.total_cost, 4),
                    "suggested_price": round(est.suggested_price, 4),
                }
            data["models"].append(item)
        payload = _json.dumps(data, indent=2)
        if output:
            Path(output).write_text(payload)
            console.print(f"[bold green]Summary saved to {output}[/bold green]")
        else:
            print(payload)
    else:
        lines = ["# Print Doctor Batch Summary", ""]
        header = "| Model | Score | Issues | Errors | Volume (cm3) |"
        if quote:
            header += " Total Cost | Suggested Price |"
        lines.append(header)
        lines.append("|---|---|---|---|---" + ("|---|" if quote else "") + "|")
        for name, a, est in sorted(results, key=lambda r: r[1].score):
            errors = sum(1 for i in a.issues if i.severity == Severity.ERROR)
            row = f"| {name} | {a.score:.1f} | {len(a.issues)} | {errors} | {a.volume / 1000.0:.1f} |"
            if est is not None:
                row += f" ${est.total_cost:.2f} | ${est.suggested_price:.2f} |"
            lines.append(row)
        lines.append("")
        summary = "\n".join(lines)
        if output:
            Path(output).write_text(summary)
            console.print(f"[bold green]Summary saved to {output}[/bold green]")
        else:
            console.print(summary)

    worst = min((r[1] for r in results), key=lambda a: a.score, default=None)
    if worst and any(i.severity == Severity.ERROR for i in worst.issues):
        raise typer.Exit(code=1)


@app.command()
def watch(
    source: str = typer.Argument(
        ..., help="Camera index (0, 1, ...) or a directory to watch for new photos"
    ),
    interval: float = typer.Option(
        5.0, "-i", "--interval", help="Seconds between frame checks"
    ),
    evidence: str = typer.Option(
        "evidence", "-e", "--evidence-dir", help="Directory for evidence screenshots"
    ),
    cooldown: float = typer.Option(
        60.0, "-c", "--cooldown", help="Seconds to wait before re-alerting same defect"
    ),
    webhook: str = typer.Option(
        None, "-w", "--webhook", help="POST a JSON alert to this URL on defect"
    ),
    duration: float = typer.Option(
        None, "-d", "--duration", help="Stop after N seconds (for testing)"
    ),
) -> None:
    """Monitor a camera or photo directory for print defects in real time."""
    from print_doctor.monitor import PrintMonitor

    try:
        monitor = PrintMonitor(
            interval_seconds=interval,
            evidence_dir=evidence,
            cooldown_seconds=cooldown,
            webhook=webhook,
        )
        if source.isdigit():
            monitor.run_camera(int(source), stop_after=duration)
        else:
            monitor.run_directory(source, stop_after=duration)
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
