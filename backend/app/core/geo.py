import math
from typing import Tuple, Optional
from app.core.config import settings

# UTM Zone 43N constants for WGS84 (Central Meridian 75.0° E)
UTM_43N_CM_RAD = math.radians(75.0)

def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth in meters.
    """
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def latlon_to_utm43n(lat: float, lon: float) -> Tuple[float, float]:
    """
    Approximate conversion from WGS84 (lat, lon) to EPSG:32643 (UTM Zone 43N) coordinates in meters.
    """
    a = 6378137.0
    f = 1 / 298.257223563
    k0 = 0.9996

    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)

    e2 = f * (2 - f)
    e_prime2 = e2 / (1 - e2)

    N = a / math.sqrt(1 - e2 * math.sin(lat_rad)**2)
    T = math.tan(lat_rad)**2
    C = e_prime2 * math.cos(lat_rad)**2
    A = (lon_rad - UTM_43N_CM_RAD) * math.cos(lat_rad)

    M = a * ((1 - e2/4 - 3*e2**2/64 - 5*e2**3/256) * lat_rad
             - (3*e2/8 + 3*e2**2/32 + 45*e2**3/1024) * math.sin(2*lat_rad)
             + (15*e2**2/256 + 45*e2**3/1024) * math.sin(4*lat_rad)
             - (35*e2**3/3072) * math.sin(6*lat_rad))

    easting = k0 * N * (A + (1 - T + C) * A**3 / 6.0 + (5 - 18 * T + T**2 + 72 * C - 58 * e_prime2) * A**5 / 120.0) + 500000.0
    northing = k0 * (M + N * math.tan(lat_rad) * (A**2 / 2.0 + (5 - T + 9 * C + 4 * C**2) * A**4 / 24.0 + (61 - 58 * T + T**2 + 600 * C - 330 * e_prime2) * A**6 / 720.0))
    return (round(easting, 2), round(northing, 2))

def is_within_giaspura_area(lat: float, lon: float, max_radius_km: Optional[float] = None) -> bool:
    """
    Check if a coordinate falls within the Giaspura monitoring zone.
    """
    radius_km = max_radius_km if max_radius_km is not None else settings.GIASPURA_RADIUS_KM
    dist_m = haversine_distance_m(lat, lon, settings.GIASPURA_LAT, settings.GIASPURA_LON)
    return dist_m <= (radius_km * 1000.0)

def validate_coordinates(lat: float, lon: float) -> Tuple[bool, str]:
    """
    Validate latitude and longitude values.
    """
    if not (-90.0 <= lat <= 90.0):
        return False, f"Invalid latitude: {lat}. Must be between -90 and 90."
    if not (-180.0 <= lon <= 180.0):
        return False, f"Invalid longitude: {lon}. Must be between -180 and 180."
    return True, "Valid coordinates"
