"""Persistence engine for evaluating temporal fire recurrence and duration."""

from typing import Dict, Any, Union
import pandas as pd
from data_processing.firms.constants import (
    PERSISTENCE_TRANSIENT_DAYS,
    PERSISTENCE_RECURRING_MIN_DAYS,
    PERSISTENCE_RECURRING_MAX_DAYS,
    PERSISTENCE_PERSISTENT_DAYS,
)


def classify_persistence(
    unique_detection_days: int,
    has_sufficient_context: bool = True
) -> str:
    """Classify temporal persistence based on distinct detection days.

    Thresholds (prototype):
    - 1 unique day: 'Transient'
    - 2–4 unique days: 'Recurring'
    - >=5 unique days: 'Persistent'
    - Insufficient historical context: 'Unknown'
    """
    if not has_sufficient_context or unique_detection_days is None or unique_detection_days <= 0:
        return "Unknown"

    if unique_detection_days == PERSISTENCE_TRANSIENT_DAYS:
        return "Transient"
    elif PERSISTENCE_RECURRING_MIN_DAYS <= unique_detection_days <= PERSISTENCE_RECURRING_MAX_DAYS:
        return "Recurring"
    elif unique_detection_days >= PERSISTENCE_PERSISTENT_DAYS:
        return "Persistent"
    else:
        return "Unknown"


def compute_temporal_metrics(observations: pd.DataFrame) -> Dict[str, Any]:
    """Calculate temporal metrics from a collection of FIRMS observations.

    Returns:
        Dict with first_seen, last_seen, event_duration_hours,
        unique_detection_days, persistence, average_frp, maximum_frp.
    """
    if observations is None or len(observations) == 0:
        return {
            "first_seen": None,
            "last_seen": None,
            "event_duration_hours": 0.0,
            "unique_detection_days": 0,
            "persistence": "Unknown",
            "average_frp": 0.0,
            "maximum_frp": 0.0
        }

    ts = pd.to_datetime(observations["timestamp"])
    first_seen = ts.min()
    last_seen = ts.max()
    duration_hours = max(0.0, (last_seen - first_seen).total_seconds() / 3600.0)

    dates = pd.to_datetime(observations["acq_date"]).dt.date
    unique_days = int(dates.nunique())

    frp_vals = pd.to_numeric(observations.get("frp", pd.Series([0.0])), errors="coerce").fillna(0.0)
    avg_frp = float(frp_vals.mean()) if len(frp_vals) > 0 else 0.0
    max_frp = float(frp_vals.max()) if len(frp_vals) > 0 else 0.0

    persistence_cat = classify_persistence(unique_days, has_sufficient_context=True)

    return {
        "first_seen": first_seen.isoformat() if pd.notnull(first_seen) else None,
        "last_seen": last_seen.isoformat() if pd.notnull(last_seen) else None,
        "event_duration_hours": round(duration_hours, 2),
        "unique_detection_days": unique_days,
        "persistence": persistence_cat,
        "average_frp": round(avg_frp, 2),
        "maximum_frp": round(max_frp, 2)
    }
