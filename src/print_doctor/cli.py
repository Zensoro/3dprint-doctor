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
    view3d: bool = typer.Option(False, "--3d", help="Generate interactive 3D HTML report with defect highlighting"),
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
    detectors: List[str] = typer.Option(
        None, "-D", "--detector", help="Run only these detectors (repeatable). "
        "List available: print-doctor detectors"
    ),
) -> None:
    """Analyze a 3D model for printability issues."""
    try:
        if not json:
            console.print(f"[bold blue]Analyzing {model_path}...[/bold blue]")
        if detectors:
            from print_doctor.mesh import analyze_mesh_with_detectors
            analysis = analyze_mesh_with_detectors(model_path, detectors)
        else:
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

        view3d_done = False
        if view3d:
            from print_doctor.visualize import generate_3d_report
            out_path = output or "report_3d.html"
            generate_3d_report(model_path, out_path, analysis)
            console.print(f"[bold green]3D report saved to {out_path}[/bold green]")
            view3d_done = True
        else:
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

    if view3d_done:
        raise typer.Exit(code=0)

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
def repair(
    model_path: str = typer.Argument(..., help="Path to STL/3MF file"),
    output: str = typer.Option(None, "-o", "--output", help="Output fixed model path"),
    no_normals: bool = typer.Option(False, "--no-normals", help="Skip normal fix"),
    no_winding: bool = typer.Option(False, "--no-winding", help="Skip winding fix"),
    no_stitch: bool = typer.Option(False, "--no-stitch", help="Skip stitch"),
    no_degenerate: bool = typer.Option(False, "--no-degenerate", help="Skip degenerate-face removal"),
) -> None:
    """Repair common mesh issues (normals, winding, stitch, degenerate faces).

    Note: large holes and self-intersections are NOT fixable by this tool;
    the report states them honestly.
    """
    from print_doctor.mesh import repair_mesh

    try:
        report = repair_mesh(
            model_path,
            output_path=output,
            fix_normals=not no_normals,
            fix_winding=not no_winding,
            stitch=not no_stitch,
            remove_degenerate=not no_degenerate,
        )
        console.print(f"[bold blue]Input:[/bold blue] {report['input']}")
        console.print(f"  vertices: {report['issues_before']['vertices']} -> "
                      f"{report['issues_after']['vertices']}")
        console.print(f"  faces: {report['issues_before']['faces']} -> "
                      f"{report['issues_after']['faces']}")
        console.print(f"  watertight: {report['issues_before']['watertight']} -> "
                      f"{report['issues_after']['watertight']}")
        console.print(f"  winding: {report['issues_before']['winding_consistent']} -> "
                      f"{report['issues_after']['winding_consistent']}")
        console.print(f"[bold green]Applied fixes:[/bold green] "
                      f"{', '.join(report['fixed']) or 'none needed'}")
        if report["not_fixable"]:
            console.print("[bold yellow]Not fixable (honest):[/bold yellow]")
            for n in report["not_fixable"]:
                console.print(f"  - {n}")
        if output:
            console.print(f"[bold green]Saved to {output}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(code=1)


@app.command()
def orient(
    model_path: str = typer.Argument(..., help="Path to STL/3MF file"),
    step: float = typer.Option(15.0, "--step", help="Rotation search step in degrees"),
    output: str = typer.Option(None, "-o", "--output", help="Save re-oriented model"),
) -> None:
    """Find a good print orientation (minimize overhangs, maximize bed contact)."""
    from print_doctor.mesh import load_mesh
    from print_doctor.orient import find_orientation

    try:
        mesh = load_mesh(model_path)
        console.print(f"[bold blue]Searching orientations for {model_path}...[/bold blue]")
        result = find_orientation(mesh, step_deg=step)

        console.print(f"[bold green]Recommended orientation:[/bold green]")
        console.print(f"  Rotate X: {result.rx_deg} degrees")
        console.print(f"  Rotate Y: {result.ry_deg} degrees")
        console.print(f"  Overhang faces: {result.overhang_fraction * 100:.1f}%")
        console.print(f"  Bed contact: {result.contact_fraction * 100:.1f}%")

        if output:
            rotated = mesh.copy()
            import math
            if result.rx_deg:
                rotated.apply_transform(
                    __import__("trimesh").transformations.rotation_matrix(
                        math.radians(result.rx_deg), [1, 0, 0]))
            if result.ry_deg:
                rotated.apply_transform(
                    __import__("trimesh").transformations.rotation_matrix(
                        math.radians(result.ry_deg), [0, 1, 0]))
            rotated.export(output)
            console.print(f"[bold green]Saved oriented model to {output}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(code=1)


@app.command()
def hollow(
    model_path: str = typer.Argument(..., help="Path to STL/3MF file"),
    output: str = typer.Option("hollowed.stl", "-o", "--output", help="Output shell file"),
    wall: float = typer.Option(2.0, "-w", "--wall", help="Shell wall thickness in mm"),
) -> None:
    """Hollow a model to save material (approximate equal-wall shell)."""
    from print_doctor.hollow import hollow_file

    try:
        result = hollow_file(model_path, output, wall=wall)
        console.print(f"[bold blue]Hollowing {model_path}...[/bold blue]")
        console.print(f"  Original volume: {result.original_volume / 1000.0:.1f} cm3")
        console.print(f"  Shell volume:    {result.shell_volume / 1000.0:.1f} cm3")
        console.print(f"  Material saved:  [bold green]{result.saved_percent:.1f}%[/bold green]")
        console.print(f"  Wall thickness:  {result.wall:.1f} mm")
        console.print(f"[bold green]Saved to {output}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Print version information."""
    from print_doctor import __version__
    console.print(f"Print Doctor v{__version__}")


@app.command()
def detectors() -> None:
    """List all registered (built-in + plugin) detectors."""
    from print_doctor.plugins import load_plugins, get_registered_detectors
    import print_doctor.builtin_detectors  # noqa: F401

    registry = load_plugins()
    for name in sorted(registry):
        console.print(f"  {name}")


@app.command()
def support(
    model_path: str = typer.Argument(..., help="Path to STL/3MF file"),
    max_angle: float = typer.Option(45.0, "--max-angle", help="Overhang threshold (degrees)"),
    density: float = typer.Option(0.15, "--density", help="Support density factor"),
    price: float = typer.Option(25.0, "-p", "--price", help="Material price per kg"),
) -> None:
    """Estimate support material needed (volume, weight, cost)."""
    from print_doctor.support import estimate_support_file

    try:
        est = estimate_support_file(model_path, max_angle=max_angle, density=density)
        console.print(f"[bold blue]Support estimate for {model_path}:[/bold blue]")
        console.print(f"  Overhang area: {est.overhang_area_mm2:.0f} mm2")
        console.print(f"  Avg support height: {est.avg_support_height_mm:.1f} mm")
        console.print(f"  Support volume: {est.support_volume_mm3 / 1000.0:.2f} cm3")
        console.print(f"  Support weight: {est.support_weight_g:.1f} g")
        console.print(f"  Support material cost: [bold green]${est.support_cost(price):.2f}[/bold green] "
                      f"(PLA @ ${price}/kg)")
        console.print("[dim](estimate only — calibrate --density against your slicer)[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(code=1)


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
def gcode_info(
    gcode_path: str = typer.Argument(..., help="Path to G-code file"),
    e_position: float = typer.Option(None, "-e", "--e-position",
                                     help="Current E position to locate (progress)"),
) -> None:
    """Analyze a sliced G-code file: layers, extrusion, progress."""
    from print_doctor.gcode import parse_gcode_file

    try:
        a = parse_gcode_file(gcode_path)
        console.print(f"[bold blue]G-code:[/bold blue] {a.filename}")
        console.print(f"  Layers: {a.layer_count}")
        console.print(f"  Max Z: {a.max_z:.2f} mm")
        console.print(f"  Total extruded: {a.total_extruded:.2f} (mm of filament)")
        console.print(f"  Extruder moves: {a.total_moves}")

        if e_position is not None:
            layer = a.layer_at(e_position)
            progress = a.progress_at(e_position)
            console.print(f"  At E={e_position:.2f}:")
            if layer is not None:
                z_str = f"{layer.z:.2f}" if layer.z is not None else "-"
                console.print(f"    Layer {layer.number} (Z={z_str} mm)")
            else:
                console.print("    (beyond last layer)")
            console.print(f"    Progress: {progress * 100:.1f}%")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(code=1)


@app.command()
def watch(
    source: str = typer.Argument(
        ..., help="Camera index (0,1,...), a directory, or an http(s) snapshot URL"
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
    user: str = typer.Option(None, "-u", "--user", help="Basic auth user (URL sources)"),
    password: str = typer.Option(None, "-P", "--password", help="Basic auth password (URL sources)"),
    gcode: str = typer.Option(
        None, "--gcode", help="G-code file for progress context (layer/percent display)"
    ),
    progress: float = typer.Option(
        None, "--progress", min=0.0, max=1.0,
        help="Manual print progress 0-1 (with --gcode, shows current layer)"
    ),
    moonraker: str = typer.Option(
        None, "--moonraker",
        help="Moonraker printer URL (e.g. http://printer:7125) to auto-fetch progress"
    ),
) -> None:
    """Monitor a camera, photo directory, or webcam snapshot URL for print defects."""
    from print_doctor.monitor import PrintMonitor, moonraker_progress_provider

    try:
        progress_provider = None
        if progress is not None:
            progress_provider = lambda: progress  # noqa: E731
        elif moonraker:
            progress_provider = moonraker_progress_provider(moonraker)

        monitor = PrintMonitor(
            interval_seconds=interval,
            evidence_dir=evidence,
            cooldown_seconds=cooldown,
            webhook=webhook,
            gcode_path=gcode,
            progress_provider=progress_provider,
        )
        if source.isdigit():
            monitor.run_camera(int(source), stop_after=duration)
        elif source.startswith(("http://", "https://")):
            auth = (user, password) if user and password else None
            monitor.run_url(source, stop_after=duration, auth=auth)
        else:
            monitor.run_directory(source, stop_after=duration)
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
