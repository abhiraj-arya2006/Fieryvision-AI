"""Comprehensive tests for ML Anomaly Detection, ESA WorldCover raster integration, and Critical priority scoring."""

import pytest
import os
from fastapi.testclient import TestClient

from app.services.anomaly_service import (
    extract_event_features,
    detect_thermal_anomaly,
    _confidence_to_numeric
)
from app.services.industrial_service import (
    get_esa_raster_landcover,
    get_landcover_context,
    ESA_RASTER_PATH
)
from app.services.evidence_service import evaluate_evidence
from main import app

client = TestClient(app)


# =====================================================================
# 1. ML-Based Anomaly Detection Tests (Isolation Forest Model)
# =====================================================================

def test_feature_extraction_and_confidence_conversion():
    conf_num_h = _confidence_to_numeric("h")
    assert conf_num_h == 0.9

    conf_num_n = _confidence_to_numeric("n")
    assert conf_num_n == 0.6

    conf_num_l = _confidence_to_numeric("l")
    assert conf_num_l == 0.3

    event = {
        "frp": 35.5,
        "brightness": 340.2,
        "confidence": "h",
        "ti4_ti5_diff": 22.0
    }
    temporal = {
        "average_frp": 30.0,
        "maximum_frp": 45.0,
        "detections_7d": 4,
        "detections_30d": 12,
        "unique_detection_days": 6,
        "event_duration_hours": 72.0
    }
    features = extract_event_features(event, temporal)
    assert features["mean_frp"] == 30.0
    assert features["max_frp"] == 45.0
    assert features["mean_brightness"] == 340.2
    assert features["detections_30d"] == 12.0
    assert features["unique_detection_days"] == 6.0
    assert features["mean_confidence_score"] == 0.9


def test_detect_thermal_anomaly_execution():
    event = {
        "frp": 55.0,
        "brightness": 365.0,
        "confidence": "h"
    }
    temporal = {
        "average_frp": 40.0,
        "maximum_frp": 60.0,
        "detections_7d": 10,
        "detections_30d": 25,
        "unique_detection_days": 15
    }
    is_anomaly, score = detect_thermal_anomaly(event, temporal)
    assert isinstance(is_anomaly, bool)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


# =====================================================================
# 2. Real ESA WorldCover Satellite Raster Integration Tests
# =====================================================================

def test_esa_worldcover_raster_exists_and_samples():
    assert os.path.exists(ESA_RASTER_PATH), f"ESA raster file missing at {ESA_RASTER_PATH}"
    
    # Giaspura study area coordinates (Lat: 30.8756, Lon: 75.8985)
    giaspura_lat, giaspura_lon = 30.875625, 75.898481
    esa_class = get_esa_raster_landcover(giaspura_lat, giaspura_lon)
    assert esa_class is not None
    assert esa_class in [
        "Built-up", "Cropland", "Tree cover", "Grassland",
        "Bare / sparse vegetation", "Water", "Shrubland"
    ]

    context_str = get_landcover_context(giaspura_lat, giaspura_lon)
    assert "ESA WorldCover 10m" in context_str


def test_esa_worldcover_fallback_on_out_of_bounds():
    # Coordinate outside Punjab GeoTIFF bounding box
    out_lat, out_lon = 10.0, 10.0
    esa_class = get_esa_raster_landcover(out_lat, out_lon)
    assert esa_class is None

    fallback_str = get_landcover_context(out_lat, out_lon)
    assert "Buffer Zone" in fallback_str or "Industrial" in fallback_str or "Zone" in fallback_str


# =====================================================================
# 3. Critical Priority Level & Risk Scoring Tests
# =====================================================================

def test_critical_priority_scoring_thresholds():
    # Test High-risk / Critical scenario
    critical_eval = evaluate_evidence(
        lat=30.8762,
        lon=75.8991,
        nearest_facility={"name": "Giaspura Auto Cluster", "site_type": "Forging"},
        distance_to_facility_m=120.0,
        inside_industrial_zone=True,
        landcover="Built-up / Industrial (ESA WorldCover 10m)",
        temporal_summary={"persistence": "high_persistence", "detections_30d": 14},
        frp=42.0,
        daynight="N",
        anomaly_score=0.88,
        anomaly_flag=True
    )
    assert critical_eval["risk_score"] >= 85.0
    assert critical_eval["priority"] == "critical"
    assert any("ML Anomaly" in claim for claim in critical_eval["evidence"])
    assert any("ESA WorldCover 10m" in claim for claim in critical_eval["evidence"])

    # Test Low-risk scenario
    low_eval = evaluate_evidence(
        lat=30.8000,
        lon=75.8000,
        nearest_facility=None,
        distance_to_facility_m=5000.0,
        inside_industrial_zone=False,
        landcover="Cropland / Agricultural (ESA WorldCover 10m)",
        temporal_summary={"persistence": "single_observation", "detections_30d": 1},
        frp=3.5,
        daynight="D",
        anomaly_score=0.1,
        anomaly_flag=False
    )
    assert low_eval["risk_score"] < 40.0
    assert low_eval["priority"] == "low"


# =====================================================================
# 4. FastAPI Endpoints Schema Integration Tests
# =====================================================================

def test_active_events_api_returns_anomaly_and_priority():
    response = client.get("/api/active-events")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert len(data["events"]) > 0

    first_event = data["events"][0]
    assert "anomaly_score" in first_event
    assert "is_anomaly" in first_event
    assert "anomaly_flag" in first_event
    assert isinstance(first_event["anomaly_score"], (int, float))
    assert isinstance(first_event["is_anomaly"], bool)
    assert "landcover" in first_event
    assert first_event["priority"] in ["critical", "high", "moderate", "medium", "low"]


def test_statistics_api_returns_critical_priority_counts():
    response = client.get("/api/statistics")
    assert response.status_code == 200
    stats = response.json()
    assert "critical_priority_events" in stats
    assert "high_priority_events" in stats
    assert "moderate_priority_events" in stats
    assert "low_priority_events" in stats
    assert stats["total_events"] >= 0


def test_location_analysis_api_includes_anomaly_and_esa_landcover():
    payload = {
        "latitude": 30.875625,
        "longitude": 75.898481
    }
    response = client.post("/api/analyse-location", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert "anomaly_score" in res
    assert "is_anomaly" in res
    assert "landcover" in res
    assert "ESA WorldCover 10m" in res["landcover"]
    assert "priority" in res
    assert res["priority"] in ["critical", "high", "moderate", "medium", "low"]
