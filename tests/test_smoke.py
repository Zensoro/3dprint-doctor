"""Smoke tests for print_doctor package."""
from typer.testing import CliRunner

from print_doctor import __version__
from print_doctor.cli import app

runner = CliRunner()


def test_version_import():
    assert __version__ == "0.2.0"


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Print Doctor v0.2.0" in result.output


def test_cli_check_help():
    result = runner.invoke(app, ["check", "--help"])
    assert result.exit_code == 0
    assert "Analyze a 3D model" in result.output
