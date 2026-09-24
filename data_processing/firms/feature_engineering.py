"""Event-level feature engineering from clustered FIRMS observations."""

import os
from typing import Optional
import numpy as np
import pandas as pd
from scipy.spatial import KDTree

from data_processing.temporal.persistence import classify_persistence


def generate_event_features(
    clustered_df: pd.DataFrame,
    output_features_csv: Optional[str] = None
) -> pd.DataFrame:
    """Generate event-level thermal, temporal, and satellite features from clustered FIRMS data.

    Returns:
        DataFrame where each row represents one distinct thermal event cluster.
    """
    if clustered_df is None or len(clustered_df) == 0:
        cols = [
            "cluster_id", "latitude", "longitude", "utm_x", "utm_y",
            "first_seen", "last_seen", "event_duration_hours", "observation_count",
            "unique_detection_days", "mean_frp", "max_frp", "min_frp", "std_frp",
            "mean_brightness", "max_brightness", "mean_bright_t31", "mean_ti4_ti5_diff",
            "detections_7d", "detections_30d", "detections_90d", "detections_365d", "detections_730d",
            "month", "hour", "dominant_daynight", "satellite_count", "dominant_satellite",
            "mean_confidence_score", "dominant_confidence", "persistence"
        ]
        empty_res = pd.DataFrame(columns=cols)
        if output_features_csv:
            os.makedirs(os.path.dirname(output_features_csv), exist_ok=True)
            empty_res.to_csv(output_features_csv, index=False)
        return empty_res

    # Ensure timestamps and dates are proper
    df = clustered_df.copy()
    df["ts"] = pd.to_datetime(df["timestamp"])
    df["t_sec"] = df["ts"].astype("int64") // 10**9
    df["date"] = pd.to_datetime(df["acq_date"]).dt.date

    # Pre-build KDTree on all raw observations for temporal recurrence queries within 500m
    all_coords = np.column_stack([df["utm_x"].values, df["utm_y"].values])
    all_tree = KDTree(all_coords)
    all_t_sec = df["t_sec"].values

    event_records = []
    grouped = df.groupby("cluster_id", sort=False)

    for cluster_id, grp in grouped:
        obs_count = len(grp)
        mean_lat = float(grp["latitude"].mean())
        mean_lon = float(grp["longitude"].mean())
        mean_x = float(grp["utm_x"].mean())
        mean_y = float(grp["utm_y"].mean())

        t_min = grp["ts"].min()
        t_max = grp["ts"].max()
        duration_hours = max(0.0, (t_max - t_min).total_seconds() / 3600.0)

        unique_days = int(grp["date"].nunique())

        # Thermal metrics
        frp_s = grp["frp"].dropna()
        mean_frp = float(frp_s.mean()) if len(frp_s) > 0 else 0.0
        max_frp = float(frp_s.max()) if len(frp_s) > 0 else 0.0
        min_frp = float(frp_s.min()) if len(frp_s) > 0 else 0.0
        std_frp = float(frp_s.std(ddof=0)) if len(frp_s) > 1 else 0.0

        b_s = grp["brightness"].dropna()
        mean_b = float(b_s.mean()) if len(b_s) > 0 else 0.0
        max_b = float(b_s.max()) if len(b_s) > 0 else 0.0

        b31_s = grp["bright_t31"].dropna()
        mean_b31 = float(b31_s.mean()) if len(b31_s) > 0 else 0.0

        diff_s = grp["ti4_ti5_diff"].dropna()
        mean_diff = float(diff_s.mean()) if len(diff_s) > 0 else (mean_b - mean_b31 if mean_b and mean_b31 else 0.0)

        # Time features
        rep_month = int(t_min.month)
        rep_hour = int(t_min.hour)
        dominant_dn = grp["daynight"].mode().iloc[0] if "daynight" in grp else "UNKNOWN"

        # Satellite & Confidence
        sat_count = int(grp["satellite"].nunique())
        dominant_sat = grp["satellite"].mode().iloc[0] if "satellite" in grp else "UNKNOWN"

        conf_score_s = grp["confidence_score"].dropna()
        mean_conf_score = float(conf_score_s.mean()) if len(conf_score_s) > 0 else 0.7
        dominant_conf = grp["confidence_level"].mode().iloc[0] if "confidence_level" in grp else "nominal"

        # Persistence category
        persistence_cat = classify_persistence(unique_days, has_sufficient_context=True)

        # Historical recurrence in spatial neighborhood (500m) preceding/inclusive of this event
        t_start_sec = int(t_min.timestamp())
        neighbor_indices = all_tree.query_ball_point([mean_x, mean_y], r=500.0)
        t_diffs = t_start_sec - all_t_sec[neighbor_indices]

        # Prior detections within historical windows
        det_7d = int(np.sum((t_diffs >= 0) & (t_diffs <= 7 * 86400)))
        det_30d = int(np.sum((t_diffs >= 0) & (t_diffs <= 30 * 86400)))
        det_90d = int(np.sum((t_diffs >= 0) & (t_diffs <= 90 * 86400)))
        det_365d = int(np.sum((t_diffs >= 0) & (t_diffs <= 365 * 86400)))
        det_730d = int(np.sum((t_diffs >= 0) & (t_diffs <= 730 * 86400)))

        event_records.append({
            "cluster_id": cluster_id,
            "latitude": round(mean_lat, 6),
            "longitude": round(mean_lon, 6),
            "utm_x": round(mean_x, 2),
            "utm_y": round(mean_y, 2),
            "first_seen": t_min.isoformat(),
            "last_seen": t_max.isoformat(),
            "event_duration_hours": round(duration_hours, 2),
            "observation_count": obs_count,
            "unique_detection_days": unique_days,
            "mean_frp": round(mean_frp, 2),
            "max_frp": round(max_frp, 2),
            "min_frp": round(min_frp, 2),
            "std_frp": round(std_frp, 2),
            "mean_brightness": round(mean_b, 2),
            "max_brightness": round(max_b, 2),
            "mean_bright_t31": round(mean_b31, 2),
            "mean_ti4_ti5_diff": round(mean_diff, 2),
            "detections_7d": det_7d,
            "detections_30d": det_30d,
            "detections_90d": det_90d,
            "detections_365d": det_365d,
            "detections_730d": det_730d,
            "month": rep_month,
            "hour": rep_hour,
            "dominant_daynight": dominant_dn,
            "satellite_count": sat_count,
            "dominant_satellite": dominant_sat,
            "mean_confidence_score": round(mean_conf_score, 3),
            "dominant_confidence": dominant_conf,
            "persistence": persistence_cat
        })

    events_df = pd.DataFrame(event_records)
    events_df = events_df.sort_values(by="first_seen").reset_index(drop=True)

    if output_features_csv:
        os.makedirs(os.path.dirname(output_features_csv), exist_ok=True)
        events_df.to_csv(output_features_csv, index=False)

    return events_df
