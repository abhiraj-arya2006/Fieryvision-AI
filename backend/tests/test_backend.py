import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.geo import validate_coordinates, haversine_distance_m
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

def test_firms_status_endpoint():
    """Test GET /api/firms/status connectivity check and schema."""
    response = client.get("/api/firms/status")
    assert response.status_code == 200
    data = response.json()
    assert "api_reachable" in data
    assert "api_success" in data
    assert "live_event_count" in data
    assert "cached_event_count" in data
    assert "data_mode" in data
    assert data["coverage"] == "WORLD"
    assert "NASA" in data["source"]

def test_active_events_endpoint():
    """Test GET /api/active-events response structure, counts, and provenance."""
    response = client.get("/api/active-events")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert "data_mode" in data
    assert data["data_mode"] in ["live", "cached", "unavailable"]
    assert "live_event_count" in data
    assert "cached_event_count" in data
    assert data["total"] == len(data["events"])
    assert data["total"] == data["live_event_count"] + data["cached_event_count"]

    if data["events"]:
        event = data["events"][0]
        # Validate canonical event schema fields and provenance
        assert "event_id" in event
        assert "latitude" in event
        assert "longitude" in event
        assert "source" in event
        assert "ml_status" in event
        assert "classification_method" in event
        assert event["classification_method"] in ["evidence_based", "supervised_ml", "cached", "active", "unclassified"]


def test_coordinate_validation():
    """Test latitude/longitude bounds validator."""
    valid, msg = validate_coordinates(30.8756, 75.8984)
    assert valid is True
    
    invalid, msg = validate_coordinates(95.0, 75.8984)
    assert invalid is False
    assert "Invalid latitude" in msg

def test_analyse_location_success():
    """Test POST /api/analyse-location with valid coordinates."""
    payload = {"latitude": 30.8756, "longitude": 75.8984}
    response = client.post("/api/analyse-location", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "thermal_activity_detected" in data
    assert "risk_score" in data
    assert "evidence" in data
    assert "ml_status" in data
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
    assert "total" in data
    assert isinstance(data["facilities"], list)

def test_firms_simulate_outage_cache_path():
    """Test outage simulation and cache failure path per Section 32."""
    res_outage = client.post("/api/firms/simulate-outage?enabled=true")
    assert res_outage.status_code == 200
    outage_data = res_outage.json()
    assert outage_data["simulated_outage"] is True

    res_ev = client.get("/api/active-events")
    assert res_ev.status_code == 200
    ev_data = res_ev.json()
    assert ev_data["data_mode"] in ["cached", "unavailable"]

    res_restore = client.post("/api/firms/simulate-outage?enabled=false")
    assert res_restore.status_code == 200
    restore_data = res_restore.json()
    assert restore_data["simulated_outage"] is False

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

