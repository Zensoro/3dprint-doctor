import typer
from pathlib import Path
from rich.console import Console

from print_doctor.mesh import analyze_mesh
from print_doctor.cost import calculate_cost
from print_doctor.report import generate_report
from print_doctor.models import PrintConfig, Severity

app = typer.Typer(
    name="print-doctor",
    help="3D printing pre-flight check and cost estimation tool",
)
console = Console()


@app.command()
def check(
    model_path: str = typer.Argument(..., help="Path to STL/3MF file"),
    output: str = typer.Option(None, "-o", "--output", help="Output report path"),
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
                volume_cm3=analysis.volume,
                config=config,
                material_price_per_kg=price,
                electricity_price_per_kwh=0.12,
                machine_power_watts=200.0,
            )

        report = generate_report(analysis, estimate)

        if output:
            Path(output).write_text(report)
            console.print(f"[bold green]Report saved to {output}[/bold green]")
        else:
            console.print(report)

        if any(i.severity == Severity.ERROR for i in analysis.issues):
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Print version information."""
    from print_doctor import __version__
    console.print(f"Print Doctor v{__version__}")


if __name__ == "__main__":
    app()
