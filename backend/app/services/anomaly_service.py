"""Machine learning anomaly detection service using Isolation Forest pipeline."""

import os
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("fieryvision.anomaly")

# Path to the pre-trained Isolation Forest pipeline
MODEL_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "ml",
        "models",
        "isolation_forest_pipeline.joblib"
    )
)

_DETECTOR = None
_MODEL_LOAD_FAILED = False


def _load_detector():
    """Lazily load the ThermalAnomalyDetector or joblib pipeline."""
    global _DETECTOR, _MODEL_LOAD_FAILED
    if _DETECTOR is not None or _MODEL_LOAD_FAILED:
        return _DETECTOR

    if not os.path.exists(MODEL_PATH):
        logger.warning("Isolation Forest model file not found at %s. Falling back to heuristic.", MODEL_PATH)
        _MODEL_LOAD_FAILED = True
        return None

    try:
        from ml.models.anomaly_detector import ThermalAnomalyDetector
        _DETECTOR = ThermalAnomalyDetector.load(MODEL_PATH)
        logger.info("Successfully loaded ThermalAnomalyDetector from %s", MODEL_PATH)
        return _DETECTOR
    except Exception as exc:
        logger.warning("Failed to load ThermalAnomalyDetector: %s. Falling back to heuristic.", exc)
        _MODEL_LOAD_FAILED = True
        return None


def _confidence_to_numeric(conf: Any) -> float:
    """Convert FIRMS confidence representation to a 0.0 - 1.0 float."""
    if conf is None:
        return 0.6
    if isinstance(conf, (int, float)):
        return max(0.0, min(1.0, float(conf) / 100.0 if float(conf) > 1.0 else float(conf)))
    
    conf_str = str(conf).strip().lower()
    if conf_str in ("h", "high"):
        return 0.9
    elif conf_str in ("n", "nominal", "medium", "moderate"):
        return 0.6
    elif conf_str in ("l", "low"):
        return 0.3
    try:
        val = float(conf_str)
        return max(0.0, min(1.0, val / 100.0 if val > 1.0 else val))
    except ValueError:
        return 0.6


def extract_event_features(
    event: Dict[str, Any],
    temporal: Optional[Dict[str, Any]] = None
) -> Dict[str, float]:
    """Extract standard numerical features expected by the Isolation Forest model."""
    temporal = temporal or {}
    
    frp = float(event.get("frp") or 0.0)
    avg_frp = float(temporal.get("average_frp") or frp or 0.0)
    max_frp = float(temporal.get("maximum_frp") or frp or 0.0)
    
    brightness = float(event.get("brightness") or 310.0)
    bright_t31 = float(event.get("bright_t31") or (brightness - 15.0))
    ti4_ti5_diff = float(event.get("ti4_ti5_diff") or max(0.0, brightness - bright_t31))
    
    det_7d = int(temporal.get("detections_7d") or 0)
    det_30d = int(temporal.get("detections_30d") or 1)
    det_90d = int(temporal.get("detections_90d") or (det_30d * 2))
    unique_days = int(temporal.get("unique_detection_days") or 1)
    duration_hours = float(temporal.get("event_duration_hours") or 0.0)
    obs_count = max(1, det_30d)
    
    conf_score = _confidence_to_numeric(event.get("confidence"))

    return {
        "mean_frp": avg_frp,
        "max_frp": max_frp,
        "mean_brightness": brightness,
        "max_brightness": brightness,
        "mean_ti4_ti5_diff": ti4_ti5_diff,
        "observation_count": float(obs_count),
        "unique_detection_days": float(unique_days),
        "event_duration_hours": duration_hours,
        "detections_7d": float(det_7d),
        "detections_30d": float(det_30d),
        "detections_90d": float(det_90d),
        "mean_confidence_score": conf_score
    }


def detect_thermal_anomaly(
    event: Dict[str, Any],
    temporal: Optional[Dict[str, Any]] = None
) -> Tuple[bool, float]:
    """
    Run Isolation Forest inference to detect statistical thermal anomalies.
    
    Returns:
        Tuple of (is_anomaly: bool, anomaly_score: float in [0.0, 1.0])
    """
    features = extract_event_features(event, temporal)
    detector = _load_detector()
    
    if detector is not None and detector.is_fitted:
        try:
            flag_arr, score_arr = detector.predict(features)
            is_anomaly = bool(flag_arr[0])
            anomaly_score = float(score_arr[0])
            return is_anomaly, round(anomaly_score, 3)
        except Exception as err:
            logger.warning("Detector inference error: %s. Using heuristic fallback.", err)

    # Heuristic fallback if model pipeline is not yet loaded
    frp_val = features["max_frp"]
    bright_val = features["mean_brightness"]
    det_30 = features["detections_30d"]

    norm_frp = min(1.0, frp_val / 50.0)
    norm_bright = min(1.0, max(0.0, (bright_val - 300.0) / 70.0))
    norm_pers = min(1.0, det_30 / 10.0)
    
    raw_score = (norm_frp * 0.45) + (norm_bright * 0.35) + (norm_pers * 0.20)
    score = round(min(1.0, max(0.0, raw_score)), 3)
    is_anomaly = (score >= 0.65 or frp_val >= 25.0)

    return is_anomaly, score
