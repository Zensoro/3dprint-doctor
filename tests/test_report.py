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
