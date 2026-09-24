"""
Temporal Intelligence & Persistence Analysis for FieryVision AI.
Calculates 7-day/30-day temporal features, unique detection days, and assigns
approved prototype persistence classifications (Transient, Recurring, Persistent, Unknown).
"""

from datetime import datetime, timedelta
from typing import List, Optional, Union
import numpy as np
import pandas as pd

from data_processing.config import PERSISTENCE_CONFIG, PersistenceConfig
from data_processing.firms.schemas import ClusteredEvent
from data_processing.geo.filter import calculate_distance_m
from data_processing.temporal.clustering import parse_detection_datetime


def classify_persistence(
    unique_detection_days: int,
    config: Optional[PersistenceConfig] = None,
) -> str:
    """
    Classify thermal persistence category from the count of unique detection days.
    
    Categories:
      - 'Transient': 1 unique detection day (typical single fire or transient burn).
      - 'Recurring': 2–4 unique detection days (intermittent or repeat thermal activity).
      - 'Persistent': >= 5 unique detection days (stationary industrial kiln, boiler, flare, or prolonged hotspot).
      - 'Unknown': 0 unique days or missing context.
    """
    cfg = config or PERSISTENCE_CONFIG

    if unique_detection_days <= 0:
        return "Unknown"
    elif unique_detection_days <= cfg.TRANSIENT_MAX_DAYS:
        return "Transient"
    elif cfg.RECURRING_MIN_DAYS <= unique_detection_days <= cfg.RECURRING_MAX_DAYS:
        return "Recurring"
    elif unique_detection_days >= cfg.PERSISTENT_MIN_DAYS:
        return "Persistent"
    else:
        return "Unknown"


def compute_event_temporal_features(
    event: ClusteredEvent,
    historical_df: Optional[pd.DataFrame] = None,
    spatial_radius_m: float = 375.0,
    config: Optional[PersistenceConfig] = None,
) -> ClusteredEvent:
    """
    Calculate 7-day and 30-day temporal metrics and persistence classification
    for a clustered event against historical FIRMS observations.
    
    If `historical_df` is provided, queries all historical observations within
    `spatial_radius_m` of the event's centroid during the 30-day lookback window.
    Otherwise, uses the cluster's internal detections.
    """
    cfg = config or PERSISTENCE_CONFIG

    # Reference timestamp is the latest observation date/time of the event
    try:
        ref_dt = datetime.strptime(event.last_seen, "%Y-%m-%d %H:%M")
    except Exception:
        try:
            ref_dt = datetime.strptime(event.last_seen[:10], "%Y-%m-%d")
        except Exception:
            ref_dt = datetime.now()

    window_30d_start = ref_dt - timedelta(days=cfg.ANALYSIS_WINDOW_DAYS)
    window_7d_start = ref_dt - timedelta(days=cfg.SHORT_WINDOW_DAYS)

    if historical_df is not None and not historical_df.empty:
        # Filter historical records within spatial radius of event centroid
        # Fast bounding box pre-filter (~500m)
        lat_delta = (spatial_radius_m / 111132.0) * 1.2
        lon_delta = (spatial_radius_m / (111132.0 * max(0.1, np.cos(np.radians(event.latitude))))) * 1.2

        mask_box = (
            (historical_df["latitude"] >= event.latitude - lat_delta)
            & (historical_df["latitude"] <= event.latitude + lat_delta)
            & (historical_df["longitude"] >= event.longitude - lon_delta)
            & (historical_df["longitude"] <= event.longitude + lon_delta)
        )
        candidates = historical_df[mask_box].copy()

        # Exact metric distance filter
        if not candidates.empty:
            dists = [
                calculate_distance_m(event.latitude, event.longitude, r["latitude"], r["longitude"])
                for _, r in candidates.iterrows()
            ]
            candidates["dist_to_event_m"] = dists
            nearby = candidates[candidates["dist_to_event_m"] <= spatial_radius_m]
        else:
            nearby = pd.DataFrame()

        if not nearby.empty:
            # Parse timestamps
            dts = [
                parse_detection_datetime(r["acq_date"], r["acq_time"])
                for _, r in nearby.iterrows()
            ]
            nearby = nearby.assign(dt=dts)

            # Filter to 30-day lookback window up to event last_seen
            obs_30d = nearby[(nearby["dt"] >= window_30d_start) & (nearby["dt"] <= ref_dt)]
            obs_7d = nearby[(nearby["dt"] >= window_7d_start) & (nearby["dt"] <= ref_dt)]

            detections_30d = len(obs_30d)
            detections_7d = len(obs_7d)
            unique_days = int(obs_30d["acq_date"].nunique()) if not obs_30d.empty else 0

            # Compute FRP metrics over the 30d window if available, or fall back to event's own
            if not obs_30d.empty:
                avg_frp = round(float(obs_30d["frp"].astype(float).mean()), 2)
                max_frp = round(float(obs_30d["frp"].astype(float).max()), 2)
                earliest_seen = min(obs_30d["dt"]).strftime("%Y-%m-%d %H:%M")
            else:
                avg_frp = event.average_frp
                max_frp = event.maximum_frp
                earliest_seen = event.first_seen

            persistence = classify_persistence(unique_days, cfg)

            # Update event attributes
            event.detections_7d = max(detections_7d, event.detections_7d)
            event.detections_30d = max(detections_30d, event.detections_30d)
            event.unique_detection_days = max(unique_days, event.unique_detection_days)
            event.average_frp = avg_frp
            event.maximum_frp = max_frp
            event.first_seen = min(earliest_seen, event.first_seen)
            event.persistence = persistence
            return event

    # If no separate historical DataFrame, classify from event's own constituent observations
    persistence = classify_persistence(event.unique_detection_days, cfg)
    event.persistence = persistence
    return event


def analyze_events_persistence(
    events: List[ClusteredEvent],
    historical_df: Optional[pd.DataFrame] = None,
    spatial_radius_m: float = 375.0,
    config: Optional[PersistenceConfig] = None,
) -> List[ClusteredEvent]:
    """
    Enrich a list of clustered events with 7-day/30-day temporal features
    and persistence classifications.
    """
    return [
        compute_event_temporal_features(
            event=evt,
            historical_df=historical_df,
            spatial_radius_m=spatial_radius_m,
            config=config,
        )
        for evt in events
    ]
