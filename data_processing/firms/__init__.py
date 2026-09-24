"""FIRMS data processing package."""

from .constants import (
    GIASPURA_LAT,
    GIASPURA_LON,
    DEFAULT_REGION_RADIUS_KM,
    SPATIAL_CLUSTER_RADIUS_M,
    TEMPORAL_CLUSTER_WINDOW_HOURS,
    EPSG_WGS84,
    EPSG_METRIC_UTM43N
)
from .loader import inspect_raw_firms, load_and_clean_firms
from .clustering import cluster_thermal_observations
from .feature_engineering import generate_event_features

__all__ = [
    "GIASPURA_LAT",
    "GIASPURA_LON",
    "DEFAULT_REGION_RADIUS_KM",
    "SPATIAL_CLUSTER_RADIUS_M",
    "TEMPORAL_CLUSTER_WINDOW_HOURS",
    "EPSG_WGS84",
    "EPSG_METRIC_UTM43N",
    "inspect_raw_firms",
    "load_and_clean_firms",
    "cluster_thermal_observations",
    "generate_event_features",
]
