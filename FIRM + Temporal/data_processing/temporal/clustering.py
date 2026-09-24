"""
Spatio-Temporal Clustering for NASA FIRMS Hotspots.
Groups nearby satellite detections into coherent fire events using ST-DBSCAN.
Initial parameters: ~375 m spatial resolution, ~24 h temporal window.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Union
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from data_processing.config import CLUSTERING_CONFIG, GEO_CONFIG
from data_processing.geo.filter import calculate_distance_m
from data_processing.firms.schemas import ClusteredEvent


def parse_detection_datetime(acq_date: str, acq_time: str) -> datetime:
    """Parse FIRMS acq_date (YYYY-MM-DD) and acq_time (HHMM) into a timezone-naive UTC datetime."""
    time_clean = str(acq_time).strip().zfill(4)[:4]
    try:
        hour = int(time_clean[:2])
        minute = int(time_clean[2:])
        # Clamp bounds
        hour = min(23, max(0, hour))
        minute = min(59, max(0, minute))
        dt = datetime.strptime(acq_date, "%Y-%m-%d")
        return dt.replace(hour=hour, minute=minute)
    except Exception:
        # Fallback to date only
        try:
            return datetime.strptime(acq_date, "%Y-%m-%d")
        except Exception:
            return datetime(1970, 1, 1)


def cluster_firms_detections(
    df: pd.DataFrame,
    spatial_eps_meters: float = CLUSTERING_CONFIG.SPATIAL_EPS_METERS,
    temporal_window_hours: float = CLUSTERING_CONFIG.TEMPORAL_WINDOW_HOURS,
    min_samples: int = CLUSTERING_CONFIG.MIN_SAMPLES,
) -> pd.DataFrame:
    """
    Perform Spatio-Temporal DBSCAN clustering on FIRMS observations.
    
    Assigns a 'cluster_id' column to each observation.
    Observations within `spatial_eps_meters` and `temporal_window_hours` are grouped
    into the same cluster.
    
    Parameters:
        df: Normalized FIRMS DataFrame containing latitude, longitude, acq_date, acq_time.
        spatial_eps_meters: Spatial proximity threshold in meters (default: 375m).
        temporal_window_hours: Temporal proximity threshold in hours (default: 24h).
        min_samples: Minimum cluster size for core points (default: 1).
        
    Returns:
        DataFrame copy with an added 'cluster_id' column.
    """
    if df.empty:
        df_out = df.copy()
        df_out["cluster_id"] = pd.Series(dtype=str)
        return df_out

    df_work = df.copy().reset_index(drop=True)
    n_points = len(df_work)

    # Parse timestamps to POSIX timestamps in seconds
    timestamps = [
        parse_detection_datetime(row["acq_date"], row["acq_time"]).timestamp()
        for _, row in df_work.iterrows()
    ]
    timestamps_arr = np.array(timestamps, dtype=np.float64)

    # Convert coordinates to local metric offsets (meters) around centroid of points
    latitudes = df_work["latitude"].values.astype(np.float64)
    longitudes = df_work["longitude"].values.astype(np.float64)
    
    lat0 = float(np.mean(latitudes))
    lon0 = float(np.mean(longitudes))
    
    # Local equirectangular metric projection (accurate to centimeters within regional scale)
    meters_per_deg_lat = 111132.954
    meters_per_deg_lon = 111132.954 * np.cos(np.radians(lat0))
    
    x_coords = (longitudes - lon0) * meters_per_deg_lon
    y_coords = (latitudes - lat0) * meters_per_deg_lat
    
    coords_metric = np.column_stack([x_coords, y_coords])

    # ST-DBSCAN distance computation
    # Two points i and j are spatio-temporal neighbors iff:
    # spatial_dist(i, j) <= spatial_eps_meters AND |time_i - time_j| <= temporal_window_seconds
    temporal_eps_seconds = temporal_window_hours * 3600.0

    # For typical regional datasets (N up to several thousands), vectorised pairwise distance is fast and exact
    if n_points <= 5000:
        # Spatial euclidean distance in meters
        dx = coords_metric[:, 0, np.newaxis] - coords_metric[:, 0]
        dy = coords_metric[:, 1, np.newaxis] - coords_metric[:, 1]
        spatial_dist = np.sqrt(dx * dx + dy * dy)
        
        # Temporal distance in seconds
        dt = np.abs(timestamps_arr[:, np.newaxis] - timestamps_arr)
        
        # Spatio-temporal adjacency matrix
        st_neighbors = (spatial_dist <= spatial_eps_meters) & (dt <= temporal_eps_seconds)
        
        # Convert adjacency to distance metric for DBSCAN (0 if neighbor, 2 if not)
        # Using precomputed distance with metric threshold 0.5
        dist_matrix = np.where(st_neighbors, 0.0, 2.0)
        
        db = DBSCAN(metric="precomputed", eps=0.5, min_samples=min_samples)
        labels = db.fit_predict(dist_matrix)
    else:
        # For larger datasets, scale dimensions so a standard Euclidean DBSCAN on (x, y, scaled_t) applies
        time_scaled = timestamps_arr * (spatial_eps_meters / max(1.0, temporal_eps_seconds))
        features_3d = np.column_stack([coords_metric, time_scaled])
        
        db = DBSCAN(eps=spatial_eps_meters, min_samples=min_samples)
        labels = db.fit_predict(features_3d)

    # Format human-readable cluster IDs
    cluster_id_col = []
    for idx, label in enumerate(labels):
        if label == -1:
            cluster_id_col.append(f"UNCLUSTERED_{idx + 1:04d}")
        else:
            # Sort label cleanly
            cluster_id_col.append(f"EVENT_{label + 1:04d}")

    df_work["cluster_id"] = cluster_id_col
    return df_work


def aggregate_clusters_to_events(
    df_clustered: pd.DataFrame,
    center_lat: float = GEO_CONFIG.GIASPURA_LATITUDE,
    center_lon: float = GEO_CONFIG.GIASPURA_LONGITUDE,
) -> List[ClusteredEvent]:
    """
    Aggregate grouped hotspot observations into event-level objects.
    Computes centroid, detection count, duration, FRP metrics, and primary satellite.
    """
    if df_clustered.empty or "cluster_id" not in df_clustered.columns:
        return []

    events: List[ClusteredEvent] = []

    for cluster_id, group in df_clustered.groupby("cluster_id"):
        # Centroid
        centroid_lat = round(float(group["latitude"].mean()), 6)
        centroid_lon = round(float(group["longitude"].mean()), 6)

        # Timestamps
        dts = [
            parse_detection_datetime(row["acq_date"], row["acq_time"])
            for _, row in group.iterrows()
        ]
        earliest_dt = min(dts)
        latest_dt = max(dts)

        duration_hours = round((latest_dt - earliest_dt).total_seconds() / 3600.0, 2)
        first_seen = earliest_dt.strftime("%Y-%m-%d %H:%M")
        last_seen = latest_dt.strftime("%Y-%m-%d %H:%M")

        # FRP metrics
        frp_vals = group["frp"].astype(float)
        avg_frp = round(float(frp_vals.mean()), 2)
        max_frp = round(float(frp_vals.max()), 2)

        # Brightness
        bright_vals = group["brightness"].astype(float)
        avg_bright = round(float(bright_vals.mean()), 2)

        # Primary satellite
        primary_sat = str(group["satellite"].mode()[0]) if not group["satellite"].empty else "VIIRS"

        # Aggregated confidence: high > nominal > low
        conf_set = set(group["confidence"].str.lower())
        if "high" in conf_set:
            agg_conf = "high"
        elif "nominal" in conf_set:
            agg_conf = "nominal"
        else:
            agg_conf = "low"

        # Unique calendar days within this group
        unique_days = int(group["acq_date"].nunique())
        count = len(group)

        # Distance to center
        dist_km = round(calculate_distance_m(centroid_lat, centroid_lon, center_lat, center_lon) / 1000.0, 3)

        # Detection IDs
        detection_ids = group["event_id"].tolist() if "event_id" in group.columns else []

        event = ClusteredEvent(
            cluster_id=str(cluster_id),
            latitude=centroid_lat,
            longitude=centroid_lon,
            first_seen=first_seen,
            last_seen=last_seen,
            duration_hours=duration_hours,
            detection_count=count,
            average_frp=avg_frp,
            maximum_frp=max_frp,
            average_brightness=avg_bright,
            detections_7d=count,
            detections_30d=count,
            unique_detection_days=unique_days,
            persistence="Transient" if unique_days == 1 else "Recurring",
            confidence=agg_conf,
            primary_satellite=primary_sat,
            distance_to_center_km=dist_km,
            detection_ids=detection_ids,
        )
        events.append(event)

    return events
