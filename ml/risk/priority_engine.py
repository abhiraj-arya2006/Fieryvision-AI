"""Transparent priority and attention scoring engine based on thermal and temporal evidence."""

from typing import Dict, List, Optional, Any
from data_processing.firms.constants import (
    PRIORITY_CRITICAL_MIN,
    PRIORITY_HIGH_MIN,
    PRIORITY_MODERATE_MIN
)


class PriorityScoringEngine:
    """Configurable priority score engine assessing operational attention requirement.

    NOTE: This is a Priority Score for operational triage, NOT a probability of disaster or accident.
    """

    def __init__(
        self,
        critical_threshold: int = PRIORITY_CRITICAL_MIN,
        high_threshold: int = PRIORITY_HIGH_MIN,
        moderate_threshold: int = PRIORITY_MODERATE_MIN
    ):
        self.critical_threshold = critical_threshold
        self.high_threshold = high_threshold
        self.moderate_threshold = moderate_threshold

    def calculate_priority(
        self,
        event: Dict[str, Any],
        industrial_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate Priority Score and triage level from available thermal/temporal evidence."""
        risk_factors: List[str] = []

        max_frp = float(event.get("max_frp", 0.0) or 0.0)
        anomaly_score = float(event.get("anomaly_score", 0.0) or 0.0)
        anomaly_flag = bool(event.get("anomaly_flag", False))
        persistence = str(event.get("persistence", "Transient"))
        conf_score = float(event.get("mean_confidence_score", 0.7) or 0.7)

        # 1. Thermal Intensity (Max 35 points)
        # Scaled up to 60 MW for typical regional agricultural/industrial fires
        thermal_pts = min(1.0, max_frp / 60.0) * 35.0
        if max_frp >= 40.0:
            risk_factors.append(f"High thermal intensity (max FRP: {max_frp:.1f} MW)")
        elif max_frp >= 20.0:
            risk_factors.append(f"Moderate thermal intensity (max FRP: {max_frp:.1f} MW)")

        # 2. Anomaly Score (Max 30 points)
        anomaly_pts = anomaly_score * 30.0
        if anomaly_flag:
            risk_factors.append(f"Unusual thermal behavior pattern (anomaly score: {anomaly_score:.2f})")

        # 3. Persistence (Max 25 points)
        if persistence == "Persistent":
            persistence_pts = 25.0
            risk_factors.append("Sustained temporal persistence (>=5 detection days)")
        elif persistence == "Recurring":
            persistence_pts = 15.0
            risk_factors.append("Recurring thermal detections (2–4 detection days)")
        elif persistence == "Transient":
            persistence_pts = 5.0
        else:
            persistence_pts = 0.0

        # 4. Satellite Confidence (Max 10 points)
        conf_pts = min(1.0, max(0.0, conf_score)) * 10.0

        # Optional Infrastructure Context Adjustment
        infra_pts = 0.0
        if industrial_context is not None:
            method = "thermal_temporal_geospatial"
            if industrial_context.get("inside_industrial_zone"):
                infra_pts = 15.0
                risk_factors.append("Co-located within recorded industrial zone")
            elif (
                industrial_context.get("distance_to_facility_m") is not None
                and industrial_context["distance_to_facility_m"] <= 500.0
            ):
                infra_pts = 10.0
                risk_factors.append("In close proximity to recorded industrial facility (<=500m)")
        else:
            method = "thermal_temporal_evidence_only"
            risk_factors.append("Score evaluated using thermal/temporal evidence only (infrastructure context absent)")

        raw_score = thermal_pts + anomaly_pts + persistence_pts + conf_pts + infra_pts
        final_score = int(round(min(100.0, max(0.0, raw_score))))

        # Priority category determination
        if final_score >= self.critical_threshold:
            priority_level = "CRITICAL"
        elif final_score >= self.high_threshold:
            priority_level = "HIGH"
        elif final_score >= self.moderate_threshold:
            priority_level = "MODERATE"
        else:
            priority_level = "LOW"

        return {
            "risk_score": final_score,
            "priority": priority_level,
            "risk_factors": risk_factors,
            "risk_method": method
        }


_DEFAULT_PRIORITY_ENGINE: Optional[PriorityScoringEngine] = None


def get_default_priority_engine() -> PriorityScoringEngine:
    global _DEFAULT_PRIORITY_ENGINE
    if _DEFAULT_ENGINE is None if "_DEFAULT_ENGINE" in globals() else _DEFAULT_PRIORITY_ENGINE is None:
        _DEFAULT_PRIORITY_ENGINE = PriorityScoringEngine()
    return _DEFAULT_PRIORITY_ENGINE


def compute_priority_score(
    event: Dict[str, Any],
    industrial_context: Optional[Dict[str, Any]] = None,
    engine: Optional[PriorityScoringEngine] = None
) -> Dict[str, Any]:
    eng = engine or get_default_priority_engine()
    return eng.calculate_priority(event, industrial_context=industrial_context)
