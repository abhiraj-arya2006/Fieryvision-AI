"""Focused unit tests for FIRMS processing, clustering, anomaly detection, evidence, and risk engines."""

import os
import tempfile
import numpy as np
import pandas as pd
import pytest

from data_processing.firms.constants import GIASPURA_LAT, GIASPURA_LON
from data_processing.firms.loader import (
    load_and_clean_firms,
    inspect_raw_firms,
    haversine_distance_km
)
from data_processing.firms.clustering import cluster_thermal_observations
from data_processing.firms.feature_engineering import generate_event_features
from data_processing.temporal.persistence import classify_persistence, compute_temporal_metrics
from ml.models.anomaly_detector import ThermalAnomalyDetector
from ml.evidence.evidence_engine import EvidenceAssessmentEngine
from ml.risk.priority_engine import PriorityScoringEngine
from ml.inference.engine import analyze_event, analyze_coordinates, validate_coords


@pytest.fixture
def sample_firms_csv():
    """Create a temporary CSV mimicking FIRMS raw schema for unit-test mechanics."""
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
        f.write(
            "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight\n"
            "30.875625,75.898481,325.4,1.1,1.0,2025-05-10,0730,N20,VIIRS,n,2.0NRT,295.2,14.5,D\n"
            "30.876000,75.899000,340.2,1.2,1.1,2025-05-10,0730,N20,VIIRS,h,2.0NRT,300.1,25.0,D\n"
            "30.875625,75.898481,325.4,1.1,1.0,2025-05-10,0730,N20,VIIRS,n,2.0NRT,295.2,14.5,D\n"  # Exact duplicate
            "30.877000,75.900000,310.0,1.0,1.0,2025-05-12,1945,N21,VIIRS,l,2.0NRT,290.0,5.2,N\n"
            "28.000000,77.000000,330.0,1.0,1.0,2025-05-10,0730,N20,VIIRS,n,2.0NRT,295.0,10.0,D\n"  # Outside 50km
            "120.00000,75.000000,330.0,1.0,1.0,2025-05-10,0730,N20,VIIRS,n,2.0NRT,295.0,10.0,D\n"  # Invalid lat
        )
        fpath = f.name
    yield fpath
    if os.path.exists(fpath):
        os.remove(fpath)


# ==========================================
# 1. FIRMS loading test
# ==========================================
def test_firms_loading(sample_firms_csv):
    raw_dir = os.path.dirname(sample_firms_csv)
    report = inspect_raw_firms(raw_dir)
    assert report["summary"]["files_inspected"] >= 1
    assert report["summary"]["total_raw_rows"] > 0


# ==========================================
# 2. Schema normalization test
# ==========================================
def test_schema_normalization(sample_firms_csv):
    raw_dir = os.path.dirname(sample_firms_csv)
    # Temporary test loading
    df = load_and_clean_firms(raw_dir, filter_radius_km=500.0)
    expected_cols = ["latitude", "longitude", "timestamp", "brightness", "bright_t31", "frp", "confidence_level", "satellite"]
    for col in expected_cols:
        assert col in df.columns
    assert "ti4_ti5_diff" in df.columns
    # N20 normalized to NOAA-20
    assert "NOAA-20" in df["satellite"].values


# ==========================================
# 3. Duplicate handling test
# ==========================================
def test_duplicate_handling(sample_firms_csv):
    raw_dir = os.path.dirname(sample_firms_csv)
    df = load_and_clean_firms(raw_dir, filter_radius_km=500.0)
    # Duplicate row at (30.875625, 75.898481, 2025-05-10 07:30, N20) must be dropped
    subset_dups = df.duplicated(subset=["latitude", "longitude", "timestamp", "satellite"])
    assert not subset_dups.any()


# ==========================================
# 4. Coordinate validation test
# ==========================================
def test_coordinate_validation():
    # Valid
    lat, lon = validate_coords(30.875625, 75.898481)
    assert lat == 30.875625 and lon == 75.898481

    # Inverted / Swapped
    with pytest.raises(ValueError, match="Check for coordinate inversion|appear swapped"):
        validate_coords(75.898481, 30.875625)

    with pytest.raises(ValueError, match="exceeds"):
        validate_coords(95.0, 75.89)

    with pytest.raises(TypeError):
        validate_coords("not_a_number", 75.89)


# ==========================================
# 5. Giaspura regional filtering test
# ==========================================
def test_giaspura_filtering(sample_firms_csv):
    raw_dir = os.path.dirname(sample_firms_csv)
    df = load_and_clean_firms(raw_dir, filter_radius_km=50.0)
    # Point at (28.0, 77.0) is >300km away and must be excluded
    assert not ((df["latitude"] == 28.0) & (df["longitude"] == 77.0)).any()
    assert (df["dist_to_giaspura_km"] <= 50.0).all()


# ==========================================
# 6. Spatial-temporal clustering test
# ==========================================
def test_spatial_temporal_clustering(sample_firms_csv):
    raw_dir = os.path.dirname(sample_firms_csv)
    df = load_and_clean_firms(raw_dir, filter_radius_km=50.0)
    clustered = cluster_thermal_observations(df, spatial_radius_m=375.0, temporal_window_hours=24.0)
    assert "cluster_id" in clustered.columns
    # Observations within ~70m and same timestamp should share cluster_id
    assert clustered["cluster_id"].nunique() >= 1


# ==========================================
# 7. Temporal feature generation test
# ==========================================
def test_temporal_feature_generation(sample_firms_csv):
    raw_dir = os.path.dirname(sample_firms_csv)
    df = load_and_clean_firms(raw_dir, filter_radius_km=50.0)
    clustered = cluster_thermal_observations(df)
    events = generate_event_features(clustered)
    required_features = [
        "cluster_id", "first_seen", "last_seen", "event_duration_hours",
        "unique_detection_days", "mean_frp", "max_frp", "mean_brightness",
        "detections_7d", "detections_30d", "persistence"
    ]
    for feat in required_features:
        assert feat in events.columns


# ==========================================
# 8. Persistence classification test
# ==========================================
def test_persistence_classification():
    assert classify_persistence(1) == "Transient"
    assert classify_persistence(2) == "Recurring"
    assert classify_persistence(4) == "Recurring"
    assert classify_persistence(5) == "Persistent"
    assert classify_persistence(10) == "Persistent"
    assert classify_persistence(0) == "Unknown"
    assert classify_persistence(None) == "Unknown"


# ==========================================
# 9. Isolation Forest fitting and inference test
# ==========================================
def test_isolation_forest():
    # Build tiny synthetic events dataframe
    rng = np.random.RandomState(42)
    n_samples = 30
    synthetic_events = pd.DataFrame({
        "mean_frp": rng.uniform(5, 30, n_samples),
        "max_frp": rng.uniform(10, 50, n_samples),
        "mean_brightness": rng.uniform(300, 360, n_samples),
        "max_brightness": rng.uniform(320, 380, n_samples),
        "mean_ti4_ti5_diff": rng.uniform(10, 50, n_samples),
        "observation_count": rng.randint(1, 5, n_samples),
        "unique_detection_days": rng.randint(1, 3, n_samples),
        "event_duration_hours": rng.uniform(0, 10, n_samples),
        "detections_7d": rng.randint(1, 5, n_samples),
        "detections_30d": rng.randint(1, 10, n_samples),
        "detections_90d": rng.randint(1, 15, n_samples),
        "mean_confidence_score": rng.uniform(0.5, 1.0, n_samples)
    })

    detector = ThermalAnomalyDetector(contamination=0.1, random_state=42)
    detector.fit(synthetic_events)
    flags, scores = detector.predict(synthetic_events)

    assert len(flags) == n_samples
    assert len(scores) == n_samples
    assert all(0.0 <= s <= 1.0 for s in scores)
    assert isinstance(flags[0], (bool, np.bool_))


# ==========================================
# 10. Empty-data behaviour test
# ==========================================
def test_empty_data_behaviour():
    empty_df = pd.DataFrame()
    clustered = cluster_thermal_observations(empty_df)
    assert len(clustered) == 0

    events = generate_event_features(empty_df)
    assert len(events) == 0

    temp_metrics = compute_temporal_metrics(empty_df)
    assert temp_metrics["persistence"] == "Unknown"


# ==========================================
# 11. Evidence engine test
# ==========================================
def test_evidence_engine():
    engine = EvidenceAssessmentEngine(high_frp_threshold=40.0)

    # High persistence event
    persistent_event = {
        "max_frp": 55.0,
        "persistence": "Persistent",
        "unique_detection_days": 6,
        "observation_count": 8,
        "anomaly_flag": False,
        "anomaly_score": 0.4
    }
    res = engine.evaluate_event(persistent_event)
    assert res["assessment"] == "Persistent Thermal Activity"
    assert res["evidence_strength"] == "HIGH"
    assert any("persistence" in e.lower() for e in res["evidence"])
    assert any("not available" in l.lower() for l in res["assessment_limitations"])

    # Anomaly event
    anomaly_event = {
        "max_frp": 45.0,
        "persistence": "Transient",
        "observation_count": 1,
        "anomaly_flag": True,
        "anomaly_score": 0.8
    }
    res_anom = engine.evaluate_event(anomaly_event)
    assert res_anom["assessment"] == "Unusual Thermal Behaviour"


# ==========================================
# 12. Risk engine test
# ==========================================
def test_risk_engine():
    engine = PriorityScoringEngine()

    high_event = {
        "max_frp": 65.0,
        "anomaly_score": 0.9,
        "anomaly_flag": True,
        "persistence": "Persistent",
        "mean_confidence_score": 1.0
    }
    res_high = engine.calculate_priority(high_event)
    assert res_high["risk_score"] >= 80
    assert res_high["priority"] in ("HIGH", "CRITICAL")
    assert res_high["risk_method"] == "thermal_temporal_evidence_only"

    low_event = {
        "max_frp": 5.0,
        "anomaly_score": 0.1,
        "anomaly_flag": False,
        "persistence": "Transient",
        "mean_confidence_score": 0.3
    }
    res_low = engine.calculate_priority(low_event)
    assert res_low["risk_score"] < 40
    assert res_low["priority"] == "LOW"


# ==========================================
# 13. Final event analysis test
# ==========================================
def test_analyze_event():
    event_dict = {
        "cluster_id": "test_cluster_99",
        "max_frp": 25.0,
        "mean_frp": 15.0,
        "observation_count": 2,
        "unique_detection_days": 2,
        "persistence": "Recurring",
        "anomaly_flag": False,
        "anomaly_score": 0.35,
        "dominant_confidence": "nominal"
    }
    res = analyze_event(event_dict)
    assert res["event_id"] == "test_cluster_99"
    assert res["thermal_activity"] == "Detected"
    assert res["persistence"] == "Recurring"
    assert "score" in res["priority"]
    assert "level" in res["priority"]
    assert "type" in res["assessment"]


# ==========================================
# 14. Coordinate analysis test
# ==========================================
def test_analyze_coordinates():
    # Synthetic master DataFrame
    master = pd.DataFrame([{
        "cluster_id": "cluster_test_1",
        "latitude": 30.875625,
        "longitude": 75.898481,
        "max_frp": 30.0,
        "mean_frp": 20.0,
        "observation_count": 3,
        "unique_detection_days": 2,
        "persistence": "Recurring",
        "anomaly_flag": False,
        "anomaly_score": 0.4,
        "dominant_confidence": "nominal"
    }])

    # Match within 1km
    res_match = analyze_coordinates(30.875625, 75.898481, search_radius_km=1.0, master_df=master)
    assert res_match["thermal_activity"] == "Detected"
    assert res_match["nearby_events_count"] == 1
    assert res_match["distance_to_query_km"] == 0.0

    # No match far away
    res_no_match = analyze_coordinates(30.0, 75.0, search_radius_km=1.0, master_df=master)
    assert res_no_match["thermal_activity"] == "None"
    assert res_no_match["nearby_events_count"] == 0
