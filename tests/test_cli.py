import os
import tempfile
from pathlib import Path
import trimesh
from typer.testing import CliRunner
from print_doctor.cli import app

runner = CliRunner()


def test_check_command_help():
    """Test check command help."""
    result = runner.invoke(app, ["check", "--help"])
    assert result.exit_code == 0
    assert "Analyze a 3D model" in result.output


def test_version_command():
    """Test version command."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Print Doctor" in result.output


def test_check_valid_model():
    """Test check with a valid model produces a report."""
    mesh = trimesh.creation.icosphere(subdivisions=2)

    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        mesh.export(f.name)
        temp_path = f.name

    try:
        result = runner.invoke(app, ["check", temp_path])
        assert result.exit_code == 0
        assert "Printability Score" in result.output
        assert "Mesh Information" in result.output
    finally:
        os.unlink(temp_path)


def test_check_missing_file():
    """Test check with a missing file exits with error."""
    result = runner.invoke(app, ["check", "/nonexistent/model.stl"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_check_output_file():
    """Test check writes report to file."""
    mesh = trimesh.creation.box(extents=[10, 10, 10])

    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = os.path.join(tmpdir, "model.stl")
        report_path = os.path.join(tmpdir, "report.md")
        mesh.export(model_path)

        result = runner.invoke(app, ["check", model_path, "-o", report_path])
        assert result.exit_code == 0
        assert os.path.exists(report_path)
        content = Path(report_path).read_text()
        assert "Print Doctor Report" in content


def test_check_exit_code_with_errors():
    """Test that a model with ERROR-level issues exits non-zero."""
    import numpy as np
    b1 = trimesh.creation.box(extents=[10, 10, 10])
    b2 = trimesh.creation.box(extents=[10, 10, 10])
    b2.apply_translation([5, 5, 5])
    broken = trimesh.Trimesh(
        vertices=np.vstack([b1.vertices, b2.vertices]),
        faces=np.vstack([b1.faces, b2.faces + len(b1.vertices)]),
    )
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        broken.export(f.name)
        temp_path = f.name

    try:
        result = runner.invoke(app, ["check", temp_path, "--no-cost"])
        assert result.exit_code == 1
        assert "Error:" not in result.output
    finally:
        os.unlink(temp_path)


def test_check_exit_code_clean_model():
    """Test that a healthy model exits zero."""
    mesh = trimesh.creation.icosphere(subdivisions=2)
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        mesh.export(f.name)
        temp_path = f.name

    try:
        result = runner.invoke(app, ["check", temp_path, "--no-cost"])
        assert result.exit_code == 0
    finally:
        os.unlink(temp_path)


def test_diagnose_command_help():
    """Test diagnose command help."""
    result = runner.invoke(app, ["diagnose", "--help"])
    assert result.exit_code == 0
    assert "Diagnose a printed part" in result.output


def test_diagnose_command_with_photo():
    """Test diagnose with a defect photo exits with code 2."""
    photo = Path(__file__).parent / "fixtures" / "diagnose" / "stringing.jpg"
    result = runner.invoke(app, ["diagnose", "--cv", str(photo)])
    assert result.exit_code == 2
    assert "stringing" in result.output


def test_diagnose_clean_photo_exit_zero():
    """Test diagnose with a clean photo exits zero."""
    photo = Path(__file__).parent / "fixtures" / "diagnose" / "normal.jpg"
    result = runner.invoke(app, ["diagnose", "--cv", str(photo)])
    assert result.exit_code == 0


def test_check_batch_directory():
    """Test batch analysis of a directory of models."""
    fixtures = Path(__file__).parent / "fixtures"
    result = runner.invoke(app, ["check-batch", str(fixtures)])
    assert result.exit_code in (0, 1)
    assert "Batch Summary" in result.output


def test_check_batch_single_file():
    """Test batch analysis of explicit files."""
    m1 = Path(__file__).parent / "fixtures" / "healthy.stl"
    m2 = Path(__file__).parent / "fixtures" / "thin_wall.stl"
    result = runner.invoke(app, ["check-batch", str(m1), str(m2)])
    assert "| healthy.stl |" in result.output
    assert "| thin_wall.stl |" in result.output


def test_check_json_output():
    """Test check --json produces parseable JSON with cost."""
    import json
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        mesh.export(f.name)
        temp_path = f.name
    try:
        result = runner.invoke(app, ["check", temp_path, "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["filename"].endswith(".stl")
        assert "printability_score" in data
    finally:
        os.unlink(temp_path)


def test_check_quote_full_pricing():
    """Test check --quote includes machine/labor/waste costs."""
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        mesh.export(f.name)
        temp_path = f.name
    try:
        result = runner.invoke(app, ["check", temp_path, "--quote", "-o", "/tmp/q.md"])
        assert result.exit_code == 0
        content = Path("/tmp/q.md").read_text()
        assert "Machine Depreciation" in content
        assert "Labor Cost" in content
        assert "Waste Allowance" in content
    finally:
        os.unlink(temp_path)


def test_quote_sheet_command():
    """Test quote-sheet generates customer HTML with shop info."""
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        mesh.export(f.name)
        temp_path = f.name
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "quote.html")
            result = runner.invoke(app, [
                "quote-sheet", temp_path, "-o", out,
                "--shop", "Test Shop", "--customer", "Bob",
                "--quote-number", "Q-9",
            ])
            assert result.exit_code == 0
            content = Path(out).read_text()
            assert "Test Shop" in content
            assert "Bob" in content
            assert "Q-9" in content
            assert "Suggested retail price" in content
    finally:
        os.unlink(temp_path)


def test_detectors_command():
    """Test detectors command lists registered detectors."""
    result = runner.invoke(app, ["detectors"])
    assert result.exit_code == 0
    assert "thin_wall" in result.output
    assert "overhang" in result.output


def test_check_with_detector_filter():
    """Test check --detector runs only the named detectors."""
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        mesh.export(f.name)
        temp_path = f.name
    try:
        result = runner.invoke(app, ["check", temp_path, "--detector", "thin_wall", "--no-cost"])
        assert result.exit_code == 0
        assert "Printability Score" in result.output
    finally:
        os.unlink(temp_path)


def test_repair_command():
    """Test repair command on a healthy model."""
    mesh = trimesh.creation.icosphere(subdivisions=3)
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        mesh.export(f.name)
        temp_path = f.name
    try:
        result = runner.invoke(app, ["repair", temp_path])
        assert result.exit_code == 0
        assert "Input:" in result.output
        assert "Applied fixes" in result.output
    finally:
        os.unlink(temp_path)


def test_repair_command_output_file():
    """Test repair writes fixed model to file."""
    mesh = trimesh.creation.icosphere(subdivisions=3)
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        mesh.export(f.name)
        temp_path = f.name
    try:
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as out:
            out_path = out.name
        try:
            result = runner.invoke(app, ["repair", temp_path, "-o", out_path])
            assert result.exit_code == 0
            assert os.path.exists(out_path)
            assert "Saved to" in result.output
        finally:
            if os.path.exists(out_path):
                os.unlink(out_path)
    finally:
        os.unlink(temp_path)


def test_gcode_info_command(tmp_path):
    """Test gcode-info command parses a G-code file."""
    gcode = tmp_path / "test.gcode"
    gcode.write_text(""";LAYER_CHANGE
;Z:0.2
G1 Z0.2 E0.1
;LAYER_CHANGE
;Z:0.4
G1 Z0.4 E0.3
""")
    result = runner.invoke(app, ["gcode-info", str(gcode)])
    assert result.exit_code == 0
    assert "Layers: 2" in result.output
    assert "Total extruded" in result.output


def test_gcode_info_with_progress(tmp_path):
    """Test gcode-info with E position shows progress."""
    gcode = tmp_path / "test.gcode"
    gcode.write_text(""";LAYER_CHANGE
G1 E0.1
;LAYER_CHANGE
G1 E0.3
""")
    result = runner.invoke(app, ["gcode-info", str(gcode), "-e", "0.2"])
    assert result.exit_code == 0
    assert "Progress" in result.output


def test_check_3d_report(tmp_path):
    """Test check --3d generates an interactive HTML report."""
    mesh = trimesh.creation.icosphere(subdivisions=3)
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        mesh.export(f.name)
        temp_path = f.name
    try:
        out = str(tmp_path / "report_3d.html")
        result = runner.invoke(app, ["check", temp_path, "--3d", "-o", out])
        assert result.exit_code == 0
        assert os.path.exists(out)
        content = Path(out).read_text()
        assert "THREE.WebGLRenderer" in content
        assert '"vertices"' in content
        assert "PRINT DOCTOR" in content
    finally:
        os.unlink(temp_path)


def test_orient_command():
    """Test orient command finds a good orientation."""
    mesh = trimesh.creation.cone(radius=5, height=10)
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        mesh.export(f.name)
        temp_path = f.name
    try:
        result = runner.invoke(app, ["orient", temp_path, "--step", "90"])
        assert result.exit_code == 0
        assert "Recommended orientation" in result.output
        assert "Rotate X" in result.output
    finally:
        os.unlink(temp_path)


def test_orient_command_output(tmp_path):
    """Test orient saves the re-oriented model."""
    mesh = trimesh.creation.cone(radius=5, height=10)
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        mesh.export(f.name)
        temp_path = f.name
    try:
        out = str(tmp_path / "oriented.stl")
        result = runner.invoke(app, ["orient", temp_path, "--step", "90", "-o", out])
        assert result.exit_code == 0
        assert os.path.exists(out)
    finally:
        os.unlink(temp_path)


def test_hollow_command(tmp_path):
    """Test hollow command saves material and writes shell."""
    mesh = trimesh.creation.box(extents=[50, 50, 30])
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        mesh.export(f.name)
        temp_path = f.name
    try:
        out = str(tmp_path / "shell.stl")
        result = runner.invoke(app, ["hollow", temp_path, "-o", out, "-w", "2"])
        assert result.exit_code == 0
        assert os.path.exists(out)
        assert "Material saved" in result.output
    finally:
        os.unlink(temp_path)


def test_hollow_command_thin_rejected(tmp_path):
    """Test hollow rejects too-thin models with clear error."""
    mesh = trimesh.creation.box(extents=[10, 10, 3])
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        mesh.export(f.name)
        temp_path = f.name
    try:
        result = runner.invoke(app, ["hollow", temp_path, "-w", "2"])
        assert result.exit_code == 1
        assert "too thin" in result.output
    finally:
        os.unlink(temp_path)


def test_support_command():
    """Test support command estimates support material."""
    column = trimesh.creation.box(extents=[4, 4, 8])
    bar = trimesh.creation.box(extents=[12, 4, 2])
    bar.apply_translation([0, 0, 8])
    mesh = trimesh.util.concatenate([column, bar])
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        mesh.export(f.name)
        temp_path = f.name
    try:
        result = runner.invoke(app, ["support", temp_path])
        assert result.exit_code == 0
        assert "Support volume" in result.output
        assert "Support material cost" in result.output
    finally:
        os.unlink(temp_path)


def test_support_command_no_overhang():
    """Support command on a clean cone shows zero support."""
    cone = trimesh.creation.cone(radius=5, height=10)
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        cone.export(f.name)
        temp_path = f.name
    try:
        result = runner.invoke(app, ["support", temp_path])
        assert result.exit_code == 0
        assert "Support volume: 0.00 cm3" in result.output
    finally:
        os.unlink(temp_path)
