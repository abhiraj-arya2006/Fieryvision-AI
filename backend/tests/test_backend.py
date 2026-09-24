import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.geo import is_within_giaspura_area, validate_coordinates, haversine_distance_m
from app.schemas.event import CanonicalEventSchema, LocationAnalysisRequest

client = TestClient(app)

def test_health_endpoint():
    """Test GET /api/health."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "FieryVision API"
    assert "firms_available" in data
    assert data["classification_mode"] == "evidence_based"

def test_active_events_endpoint():
    """Test GET /api/active-events response structure and Giaspura normalization."""
    response = client.get("/api/active-events")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert "data_mode" in data
    assert data["radius_km"] == 15.0

    if data["events"]:
        event = data["events"][0]
        # Validate canonical event schema fields
        assert "event_id" in event
        assert "latitude" in event
        assert "longitude" in event
        assert "classification_method" in event
        assert event["classification_method"] in ["evidence_based", "supervised_ml", "cached", "active", "unclassified"]

def test_giaspura_geo_filtering():
    """Test Giaspura regional coordinate boundary check."""
    # Giaspura center point (30.875625, 75.898481)
    assert is_within_giaspura_area(30.8756, 75.8984) is True
    # Outside point (Delhi coordinates)
    assert is_within_giaspura_area(28.6139, 77.2090) is False

def test_coordinate_validation():
    """Test latitude/longitude bounds validator."""
    valid, msg = validate_coordinates(30.8756, 75.8984)
    assert valid is True
    
    invalid, msg = validate_coordinates(95.0, 75.8984)
    assert invalid is False
    assert "Invalid latitude" in msg

def test_analyse_location_success():
    """Test POST /api/analyse-location with valid coordinates inside Giaspura."""
    payload = {"latitude": 30.8756, "longitude": 75.8984}
    response = client.post("/api/analyse-location", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["in_giaspura_zone"] is True
    assert "risk_score" in data
    assert "evidence" in data
    assert data["classification_method"] == "evidence_based"

def test_analyse_location_invalid_coords():
    """Test POST /api/analyse-location with out-of-bounds coordinates."""
    payload = {"latitude": 120.0, "longitude": 75.8984}
    response = client.post("/api/analyse-location", json=payload)
    assert response.status_code == 422  # Pydantic validation error

def test_event_details_not_found():
    """Test GET /api/events/{non_existent_id} returns 404."""
    response = client.get("/api/events/NON-EXISTENT-ID-999")
    assert response.status_code == 404

def test_facilities_endpoint():
    """Test GET /api/facilities."""
    response = client.get("/api/facilities")
    assert response.status_code == 200
    data = response.json()
    assert "facilities" in data
    assert len(data["facilities"]) > 0

def test_statistics_endpoint():
    """Test GET /api/statistics."""
    response = client.get("/api/statistics")
    assert response.status_code == 200
    data = response.json()
    assert "total_events" in data
    assert "classified_events" in data
    assert "unclassified_events" in data
    assert data["classification_mode"] == "evidence_based"

def test_chat_endpoint():
    """Test POST /api/chat handles grounded question with fallback or Qwen."""
    payload = {
        "question": "Why is this location high priority?",
        "context": {
            "latitude": 30.8756,
            "longitude": 75.8984,
            "classification": "industrial_heat_source",
            "risk_score": 75.0,
            "priority": "high",
            "nearest_facility_name": "Testing Mill",
            "evidence": ["Repeated thermal detections"]
        }
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "llm_available" in data
    # Ensure response is bullet points or formatted
    assert len(data["response"]) > 0

def test_chat_empty_question():
    """Test POST /api/chat with blank question rejected."""
    payload = {"question": "   ", "context": {}}
    response = client.post("/api/chat", json=payload)
    assert response.status_code in [400, 422]

