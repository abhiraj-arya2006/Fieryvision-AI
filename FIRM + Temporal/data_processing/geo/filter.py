"""
Geospatial filtering and metric distance calculations for FieryVision AI.
Calculates metric distances and filters observations to the Giaspura monitoring area.
"""

import math
from typing import List, Dict, Any, Tuple, Union
import pandas as pd

from data_processing.config import GEO_CONFIG


def calculate_distance_km(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calculate great-circle distance between two points in kilometers using Haversine formula.
    Accurate metric calculation without planar degree distortion.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    # Clip for float precision edge cases
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return GEO_CONFIG.EARTH_RADIUS_KM * c


def calculate_distance_m(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculate distance between two coordinates in meters."""
    return calculate_distance_km(lat1, lon1, lat2, lon2) * 1000.0


def is_within_monitoring_area(
    lat: float,
    lon: float,
    center_lat: float = GEO_CONFIG.GIASPURA_LATITUDE,
    center_lon: float = GEO_CONFIG.GIASPURA_LONGITUDE,
    radius_km: float = GEO_CONFIG.DEFAULT_MONITORING_RADIUS_KM,
) -> bool:
    """Check whether a coordinate point lies within the regional monitoring radius."""
    dist_km = calculate_distance_km(lat, lon, center_lat, center_lon)
    return dist_km <= radius_km


def get_bounding_box_for_radius(
    center_lat: float = GEO_CONFIG.GIASPURA_LATITUDE,
    center_lon: float = GEO_CONFIG.GIASPURA_LONGITUDE,
    radius_km: float = GEO_CONFIG.DEFAULT_MONITORING_RADIUS_KM,
) -> Tuple[float, float, float, float]:
    """
    Compute conservative bounding box (min_lat, min_lon, max_lat, max_lon)
    encompassing the circular radius. Useful for NASA API queries.
    """
    # 1 deg latitude is approximately 110.574 km
    lat_delta = (radius_km / 110.574) * 1.05  # 5% safety margin
    
    # 1 deg longitude varies with latitude
    cos_lat = math.cos(math.radians(center_lat))
    lon_scale = 111.320 * max(0.01, cos_lat)
    lon_delta = (radius_km / lon_scale) * 1.05

    min_lat = max(-90.0, center_lat - lat_delta)
    max_lat = min(90.0, center_lat + lat_delta)
    min_lon = max(-180.0, center_lon - lon_delta)
    max_lon = min(180.0, center_lon + lon_delta)

    return (min_lat, min_lon, max_lat, max_lon)


def filter_to_monitoring_area(
    data: Union[pd.DataFrame, List[Dict[str, Any]]],
    center_lat: float = GEO_CONFIG.GIASPURA_LATITUDE,
    center_lon: float = GEO_CONFIG.GIASPURA_LONGITUDE,
    radius_km: float = GEO_CONFIG.DEFAULT_MONITORING_RADIUS_KM,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    dist_col: str = "distance_to_center_km",
) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Filter observations to those strictly within `radius_km` of the target center.
    Annotates each record with `distance_to_center_km`.
    Supports both pandas DataFrames and lists of dictionaries.
    """
    if isinstance(data, pd.DataFrame):
        if data.empty:
            df = data.copy()
            df[dist_col] = pd.Series(dtype=float)
            return df
        
        df = data.copy()
        distances = [
            calculate_distance_km(lat, lon, center_lat, center_lon)
            for lat, lon in zip(df[lat_col], df[lon_col])
        ]
        df[dist_col] = distances
        filtered_df = df[df[dist_col] <= radius_km].copy()
        return filtered_df.reset_index(drop=True)

    elif isinstance(data, list):
        if not data:
            return []
        
        filtered_records = []
        for record in data:
            lat = float(record.get(lat_col, 0.0))
            lon = float(record.get(lon_col, 0.0))
            dist = calculate_distance_km(lat, lon, center_lat, center_lon)
            if dist <= radius_km:
                rec_copy = dict(record)
                rec_copy[dist_col] = round(dist, 4)
                filtered_records.append(rec_copy)
        return filtered_records

    else:
        raise TypeError(f"Unsupported data type for filtering: {type(data)}")
