import typer
from rich.console import Console

app = typer.Typer(
    name="print-doctor",
    help="3D printing pre-flight check and cost estimation tool",
)
console = Console()


@app.command()
def check(
    model_path: str = typer.Argument(..., help="Path to STL/3MF file"),
    output: str = typer.Option(None, "-o", "--output", help="Output report path"),
) -> None:
    """Analyze a 3D model for printability issues."""
    console.print(f"[bold green]Analyzing {model_path}...[/bold green]")
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command()
def version() -> None:
    """Print version information."""
    from print_doctor import __version__
    console.print(f"Print Doctor v{__version__}")
