import os
from pathlib import Path
from typer.testing import CliRunner
from print_doctor.cli import app

runner = CliRunner()
fixtures_dir = Path(__file__).parent / "fixtures"


def _run_check(model_name: str, extra_args=None):
    model = fixtures_dir / model_name
    assert model.exists(), f"Fixture missing: {model}"
    args = ["check", str(model)] + (extra_args or [])
    return runner.invoke(app, args)


def test_e2e_healthy_model():
    """E2E: healthy model passes with a report."""
    result = _run_check("healthy.stl")
    assert result.exit_code == 0
    assert "Printability Score" in result.output
    assert "Mesh Information" in result.output


def test_e2e_thin_wall_model():
    """E2E: thin wall model is reported."""
    result = _run_check("thin_wall.stl")
    assert result.exit_code == 0
    assert "thin_wall" in result.output


def test_e2e_overhang_model():
    """E2E: overhang model is reported."""
    result = _run_check("overhang.stl")
    assert "overhang" in result.output


def test_e2e_cost_estimation():
    """E2E: cost estimation appears in report."""
    result = _run_check("healthy.stl", ["-m", "PLA"])
    assert result.exit_code == 0
    assert "Cost Estimate" in result.output
    assert "$" in result.output


def test_e2e_output_file():
    """E2E: report written to file."""
    with __import__("tempfile").TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "report.md")
        result = _run_check("healthy.stl", ["-o", out])
        assert result.exit_code == 0
        assert Path(out).exists()
        assert "Print Doctor Report" in Path(out).read_text()


def test_e2e_no_cost_flag():
    """E2E: --no-cost omits the cost section."""
    result = _run_check("healthy.stl", ["--no-cost"])
    assert result.exit_code == 0
    assert "Cost Estimate" not in result.output
