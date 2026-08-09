"""Tests for the local web interface."""
import pytest

from fastapi.testclient import TestClient
from print_doctor.webapp import app

client = TestClient(app)


def test_index_page():
    r = client.get("/")
    assert r.status_code == 200
    assert "PRINT DOCTOR" in r.text
    assert "Drop an STL" in r.text


def test_analyze_upload():
    """Upload a valid STL returns a session id + score."""
    with open("tests/fixtures/healthy.stl", "rb") as f:
        r = client.post("/analyze", files={
            "file": ("healthy.stl", f, "application/octet-stream")})
    assert r.status_code == 200
    j = r.json()
    assert "id" in j
    assert j["filename"] == "healthy.stl"
    assert 0 <= j["score"] <= 100
    return j["id"]


def test_analyze_invalid_file():
    """Uploading a non-mesh file returns an error."""
    r = client.post("/analyze", files={
        "file": ("bad.stl", b"not a mesh", "application/octet-stream")})
    assert r.status_code == 200
    j = r.json()
    assert "error" in j


def test_view_3d_report():
    sid = test_analyze_upload()
    r = client.get(f"/view/{sid}")
    assert r.status_code == 200
    assert "PRINT DOCTOR" in r.text
    assert "THREE.WebGLRenderer" in r.text


def test_report_text():
    sid = test_analyze_upload()
    r = client.get(f"/report/{sid}")
    assert r.status_code == 200
    assert "Printability Score" in r.text


def test_api_report():
    sid = test_analyze_upload()
    r = client.get(f"/api/report/{sid}")
    j = r.json()
    assert j["filename"] == "healthy.stl"
    assert "score" in j
    assert "issues" in j


def test_view_missing_session():
    r = client.get("/view/nonexistent")
    assert r.status_code == 200
    assert "not found" in r.text
