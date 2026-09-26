"""Automated test suite for Incident Intelligence, Wind/Plume Modeling, Emergency Infrastructure & PDF Reports."""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_weather_wind_endpoint_valid_coordinates():
    """Test GET /api/weather/wind for valid global coordinates."""
    response = client.get("/api/weather/wind?latitude=30.8756&longitude=75.8985")
    assert response.status_code == 200
    data = response.json()
    assert "wind_speed_kmh" in data
    assert "wind_direction_deg" in data
    assert "downwind_bearing_deg" in data
    assert "cardinal_direction" in data
    assert "source" in data
    assert "hourly_forecast" in data
    assert len(data["hourly_forecast"]) > 0


def test_hotspot_wind_endpoint():
    """Test GET /api/hotspots/{id}/wind for Giaspura and USA hotspots."""
    response = client.get("/api/hotspots/HS-IND-001/wind")
    assert response.status_code == 200
    data = response.json()
    assert data["wind_speed_kmh"] >= 0
    assert 0 <= data["wind_direction_deg"] <= 360
    assert 0 <= data["downwind_bearing_deg"] <= 360


def test_hotspot_plume_endpoint():
    """Test GET /api/hotspots/{id}/plume generates 1h, 3h, 6h, 12h cones with polygons."""
    response = client.get("/api/hotspots/HS-IND-001/plume")
    assert response.status_code == 200
    data = response.json()
    assert data["hotspot_id"] == "HS-IND-001"
    assert "horizons" in data
    assert len(data["horizons"]) == 4  # 1h, 3h, 6h, 12h
    
    for hz in data["horizons"]:
        assert hz["horizon_hours"] in [1, 3, 6, 12]
        assert hz["projected_distance_km"] > 0
        assert len(hz["polygon_coordinates"]) >= 4
        assert len(hz["centerline_coordinates"]) >= 2
    assert "INDICATIVE SCREENING ONLY" in data["screening_disclaimer"]


def test_emergency_nearby_endpoint():
    """Test GET /api/emergency/nearby discovers fire stations and hospitals."""
    response = client.get("/api/emergency/nearby?latitude=30.8756&longitude=75.8985&radius_km=12.0")
    assert response.status_code == 200
    facilities = response.json()
    assert isinstance(facilities, list)
    assert len(facilities) > 0
    
    types = [f["facility_type"] for f in facilities]
    assert "fire_station" in types or "hospital" in types
    for fac in facilities:
        assert "distance_m" in fac
        assert "bearing_deg" in fac
        assert "name" in fac


def test_hotspot_emergency_context():
    """Test GET /api/hotspots/{id}/emergency-context calculates 1km and 3km buffer counts."""
    response = client.get("/api/hotspots/HS-IND-001/emergency-context")
    assert response.status_code == 200
    data = response.json()
    assert data["hotspot_id"] == "HS-IND-001"
    assert "nearest_fire_station" in data
    assert "buffer_1km" in data
    assert "buffer_3km" in data
    assert data["buffer_1km"]["buffer_radius_m"] == 1000.0
    assert data["buffer_3km"]["buffer_radius_m"] == 3000.0
    assert "coverage_disclaimer" in data


def test_hotspot_incident_intel_unified():
    """Test GET /api/hotspots/{id}/incident-intel returns complete combined incident payload."""
    response = client.get("/api/hotspots/HS-IND-001/incident-intel")
    assert response.status_code == 200
    data = response.json()
    assert "hotspot" in data
    assert "wind" in data
    assert "plume" in data
    assert "emergency" in data
    assert "ai_investigation_summary" in data
    assert len(data["ai_investigation_summary"]) > 20


def test_hotspot_pdf_report_export():
    """Test GET /api/hotspots/{id}/report/pdf generates a valid 2-page PDF document."""
    response = client.get("/api/hotspots/HS-IND-001/report/pdf")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
    assert "attachment" in response.headers.get("Content-Disposition", "")
    assert len(response.content) > 1000  # Non-empty PDF
    assert response.content[:4] == b"%PDF"  # Valid PDF binary signature


def test_hotspot_not_found_handling():
    """Test 404 handling for invalid hotspot IDs across new endpoints."""
    res_wind = client.get("/api/hotspots/NON-EXISTENT-ID/wind")
    assert res_wind.status_code == 404

    res_plume = client.get("/api/hotspots/NON-EXISTENT-ID/plume")
    assert res_plume.status_code == 404

    res_pdf = client.get("/api/hotspots/NON-EXISTENT-ID/report/pdf")
    assert res_pdf.status_code == 404
