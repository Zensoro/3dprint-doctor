import pytest
from print_doctor.report import generate_report
from print_doctor.models import MeshAnalysis, CostEstimate, Issue, Severity


def _make_analysis(**overrides):
    defaults = dict(
        filename="test.stl",
        is_watertight=True,
        is_manifold=True,
        triangle_count=1000,
        volume=100.0,
        surface_area=200.0,
        bounding_box=(10.0, 20.0, 30.0),
        issues=[],
        score=85.0,
    )
    defaults.update(overrides)
    return MeshAnalysis(**defaults)


def _make_estimate(**overrides):
    defaults = dict(
        weight_grams=50.0,
        print_time_hours=2.5,
        material_cost=5.0,
        electricity_cost=0.25,
        total_cost=5.25,
        suggested_price=10.50,
    )
    defaults.update(overrides)
    return CostEstimate(**defaults)


def test_generate_report_with_analysis_and_cost():
    """Test full report with issues and cost estimate."""
    analysis = _make_analysis(issues=[
        Issue(
            name="thin_wall",
            description="Wall thickness below minimum",
            severity=Severity.WARNING,
            location="X axis: 0.5mm",
            suggestion="Increase wall thickness",
        ),
    ])

    report = generate_report(analysis, _make_estimate())

    assert "test.stl" in report
    assert "85.0" in report
    assert "thin_wall" in report
    assert "50.0g" in report
    assert "$5.25" in report
    assert "$10.50" in report
    assert "Cost Estimate" in report


def test_generate_report_without_cost():
    """Test report generation without cost estimate."""
    analysis = _make_analysis()
    report = generate_report(analysis, None)

    assert "test.stl" in report
    assert "Cost Estimate" not in report


def test_generate_report_no_issues():
    """Test report for a healthy model."""
    analysis = _make_analysis(score=100.0)
    report = generate_report(analysis, None)

    assert "No Issues Found" in report


def test_generate_report_error_first():
    """Test that errors are listed before warnings."""
    analysis = _make_analysis(issues=[
        Issue(
            name="warning_issue", description="w", severity=Severity.WARNING,
            location="l", suggestion="s",
        ),
        Issue(
            name="error_issue", description="e", severity=Severity.ERROR,
            location="l", suggestion="s",
        ),
    ])
    report = generate_report(analysis, None)

    assert report.index("error_issue") < report.index("warning_issue")


def test_generate_html_report():
    """Test HTML report generation."""
    from print_doctor.report import generate_html_report
    analysis = _make_analysis(issues=[
        Issue(
            name="thin_wall", description="d", severity=Severity.WARNING,
            location="l", suggestion="s",
        ),
    ])
    html = generate_html_report(analysis, _make_estimate())

    assert "<!DOCTYPE html>" in html
    assert "test.stl" in html
    assert "85.0" in html
    assert "thin_wall" in html
    assert "$10.50" in html


def test_generate_html_report_no_cost():
    """Test HTML report without cost estimate."""
    from print_doctor.report import generate_html_report
    html = generate_html_report(_make_analysis(score=100.0), None)

    assert "<!DOCTYPE html>" in html
    assert "No issues found" in html
    assert "Cost Estimate" not in html


def test_generate_json_report():
    """Test JSON report serialization."""
    from print_doctor.report import generate_json_report
    import json
    analysis = _make_analysis(issues=[
        Issue(
            name="thin_wall", description="d", severity=Severity.WARNING,
            location="l", suggestion="s",
        ),
    ])
    js = json.loads(generate_json_report(analysis, _make_estimate()))

    assert js["filename"] == "test.stl"
    assert js["printability_score"] == 85.0
    assert js["mesh"]["watertight"] is True
    assert js["issues"][0]["name"] == "thin_wall"
    assert js["cost"]["suggested_price"] == 10.50
    assert js["schema_version"] == 1


def test_generate_json_report_no_cost():
    """Test JSON report without cost estimate."""
    from print_doctor.report import generate_json_report
    import json
    js = json.loads(generate_json_report(_make_analysis(), None))
    assert "cost" not in js
