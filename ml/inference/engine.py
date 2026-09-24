"""Inference API functions for thermal event analysis and coordinate-based queries."""

import os
from typing import Dict, List, Optional, Any, Union, Tuple
import numpy as np
import pandas as pd

from data_processing.firms.constants import GIASPURA_LAT, GIASPURA_LON
from data_processing.firms.loader import haversine_distance_km
from ml.models.anomaly_detector import ThermalAnomalyDetector
from ml.evidence.evidence_engine import EvidenceAssessmentEngine, get_default_evidence_engine
from ml.risk.priority_engine import PriorityScoringEngine, get_default_priority_engine

DEFAULT_MASTER_CSV = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "processed", "master_features.csv"
)
DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "models", "isolation_forest_pipeline.joblib"
)

_CACHED_MASTER_DF: Optional[pd.DataFrame] = None
_CACHED_DETECTOR: Optional[ThermalAnomalyDetector] = None


def get_cached_master_df(csv_path: str = DEFAULT_MASTER_CSV) -> pd.DataFrame:
    global _CACHED_MASTER_DF
    if _CACHED_MASTER_DF is None:
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Master features dataset not found at {csv_path}")
        _CACHED_MASTER_DF = pd.read_csv(csv_path)
    return _CACHED_MASTER_DF


def get_cached_detector(model_path: str = DEFAULT_MODEL_PATH) -> ThermalAnomalyDetector:
    global _CACHED_DETECTOR
    if _CACHED_DETECTOR is None:
        _CACHED_DETECTOR = ThermalAnomalyDetector.load(model_path)
    return _CACHED_DETECTOR


def validate_coords(lat: float, lon: float) -> Tuple[float, float]:
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError) as err:
        raise TypeError(f"Invalid coordinate format: lat={lat}, lon={lon}") from err

    if abs(lat) > 90.0:
        raise ValueError(f"Latitude {lat} exceeds [-90, 90]. Check for coordinate inversion.")
    if abs(lon) > 180.0:
        raise ValueError(f"Longitude {lon} exceeds [-180, 180].")

    if 60.0 <= lat <= 90.0 and 10.0 <= lon <= 40.0:
        raise ValueError(f"Latitude ({lat}) and longitude ({lon}) appear swapped for the regional area.")

    return lat, lon


def analyze_event(
    event_record: Dict[str, Any],
    detector: Optional[ThermalAnomalyDetector] = None,
    evidence_eng: Optional[EvidenceAssessmentEngine] = None,
    priority_eng: Optional[PriorityScoringEngine] = None,
    industrial_context: Optional[Dict[str, Any]] = None,
    landcover_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Analyze a thermal event record and format the output per standard intelligence schema.

    Schema:
    {
      "event_id": str,
      "thermal_activity": "Detected",
      "anomaly": {"flag": bool, "score": float},
      "persistence": str,
      "assessment": {"type": str, "method": str, "strength": str},
      "priority": {"score": int, "level": str, "method": str},
      "evidence": list[str],
      "limitations": list[str]
    }
    """
    event = dict(event_record)
    event_id = str(event.get("cluster_id") or event.get("event_id") or "UNKNOWN_EVENT")

    # Compute anomaly if not present
    if "anomaly_flag" not in event or "anomaly_score" not in event:
        det = detector or get_cached_detector()
        flag_arr, score_arr = det.predict(event)
        event["anomaly_flag"] = bool(flag_arr[0])
        event["anomaly_score"] = float(score_arr[0])

    ev_eng = evidence_eng or get_default_evidence_engine()
    pr_eng = priority_eng or get_default_priority_engine()

    ev_res = ev_eng.evaluate_event(
        event,
        industrial_context=industrial_context,
        landcover_context=landcover_context
    )
    pr_res = pr_eng.calculate_priority(
        event,
        industrial_context=industrial_context
    )

    persistence_cat = str(event.get("persistence", "Transient"))

    return {
        "event_id": event_id,
        "thermal_activity": "Detected",
        "anomaly": {
            "flag": bool(event["anomaly_flag"]),
            "score": round(float(event["anomaly_score"]), 3)
        },
        "persistence": persistence_cat,
        "assessment": {
            "type": ev_res["assessment"],
            "method": "evidence_based",
            "strength": ev_res["evidence_strength"]
        },
        "priority": {
            "score": pr_res["risk_score"],
            "level": pr_res["priority"],
            "method": pr_res["risk_method"]
        },
        "evidence": ev_res["evidence"],
        "limitations": ev_res["assessment_limitations"]
    }


def analyze_coordinates(
    latitude: float,
    longitude: float,
    search_radius_km: float = 2.0,
    master_df: Optional[pd.DataFrame] = None,
    detector: Optional[ThermalAnomalyDetector] = None,
    evidence_eng: Optional[EvidenceAssessmentEngine] = None,
    priority_eng: Optional[PriorityScoringEngine] = None,
    industrial_context: Optional[Dict[str, Any]] = None,
    landcover_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Query nearby thermal events around input coordinates and produce intelligence output."""
    lat, lon = validate_coords(latitude, longitude)

    df = master_df if master_df is not None else get_cached_master_df()

    if df.empty:
        return {
            "query_coordinates": {"latitude": lat, "longitude": lon},
            "thermal_activity": "None",
            "nearby_events_count": 0,
            "nearest_distance_km": None,
            "message": "No thermal events recorded in dataset."
        }

    # Vectorized Haversine distance
    dists = haversine_distance_km(
        df["latitude"].values,
        df["longitude"].values,
        lat,
        lon
    )

    within_mask = dists <= search_radius_km
    match_count = int(np.sum(within_mask))

    if match_count == 0:
        min_dist = round(float(np.min(dists)), 2) if len(dists) > 0 else None
        return {
            "query_coordinates": {"latitude": lat, "longitude": lon},
            "thermal_activity": "None",
            "nearby_events_count": 0,
            "nearest_distance_km": min_dist,
            "search_radius_km": search_radius_km,
            "message": f"No thermal activity detected within {search_radius_km} km of input coordinates."
        }

    # Select the closest event
    within_indices = np.where(within_mask)[0]
    closest_sub_idx = np.argmin(dists[within_indices])
    best_row_idx = within_indices[closest_sub_idx]
    best_row = df.iloc[best_row_idx].to_dict()
    nearest_dist = round(float(dists[best_row_idx]), 3)

    event_result = analyze_event(
        best_row,
        detector=detector,
        evidence_eng=evidence_eng,
        priority_eng=priority_eng,
        industrial_context=industrial_context,
        landcover_context=landcover_context
    )

    event_result["query_coordinates"] = {"latitude": lat, "longitude": lon}
    event_result["distance_to_query_km"] = nearest_dist
    event_result["nearby_events_count"] = match_count
    event_result["search_radius_km"] = search_radius_km

    return event_result
