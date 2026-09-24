"""Spatial-temporal event clustering for FIRMS observations."""

from typing import Tuple
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import KDTree
from scipy.sparse import csgraph, csr_matrix

from .constants import (
    SPATIAL_CLUSTER_RADIUS_M,
    TEMPORAL_CLUSTER_WINDOW_HOURS,
    EPSG_WGS84,
    EPSG_METRIC_UTM43N
)


def cluster_thermal_observations(
    df: pd.DataFrame,
    spatial_radius_m: float = SPATIAL_CLUSTER_RADIUS_M,
    temporal_window_hours: float = TEMPORAL_CLUSTER_WINDOW_HOURS
) -> pd.DataFrame:
    """Cluster raw FIRMS observations into thermal event clusters using spatial-temporal proximity.

    Criteria:
    - Spatial distance <= spatial_radius_m (default 375m in EPSG:32643 UTM metric)
    - Temporal separation <= temporal_window_hours (default 24h)

    Returns:
        DataFrame with added 'cluster_id', 'utm_x', 'utm_y'.
    """
    if df is None or len(df) == 0:
        empty_df = pd.DataFrame() if df is None else df.copy()
        empty_df["cluster_id"] = []
        empty_df["utm_x"] = []
        empty_df["utm_y"] = []
        return empty_df

    df_out = df.copy()

    # Project to EPSG:32643 for metric distances
    transformer = Transformer.from_crs(EPSG_WGS84, EPSG_METRIC_UTM43N, always_xy=True)
    xs, ys = transformer.transform(df_out["longitude"].values, df_out["latitude"].values)
    df_out["utm_x"] = xs
    df_out["utm_y"] = ys

    ts = pd.to_datetime(df_out["timestamp"])
    t_seconds = ts.astype("int64") // 10**9
    df_out["t_sec"] = t_seconds

    n = len(df_out)
    coords = np.column_stack([xs, ys])
    tree = KDTree(coords)

    # Find spatial candidate pairs within radius
    pairs = list(tree.query_pairs(r=spatial_radius_m))

    temporal_threshold_sec = int(temporal_window_hours * 3600)
    valid_pairs = []
    t_arr = t_seconds.values

    for i, j in pairs:
        if abs(t_arr[i] - t_arr[j]) <= temporal_threshold_sec:
            valid_pairs.append((i, j))

    if valid_pairs:
        rows, cols = zip(*valid_pairs)
        data = np.ones(len(rows), dtype=bool)
        adj = csr_matrix((data, (rows, cols)), shape=(n, n))
        n_components, labels = csgraph.connected_components(adj, directed=False)
    else:
        labels = np.arange(n)
        n_components = n

    # Format cluster_id as cluster_00001, cluster_00002, etc.
    cluster_ids = [f"cluster_{int(lbl) + 1:05d}" for lbl in labels]
    df_out["cluster_id"] = cluster_ids

    return df_out
