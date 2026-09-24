"""Geospatial coordinate and geometry validation utilities."""

from typing import Tuple, Union
from shapely.geometry.base import BaseGeometry


def validate_coordinates(
    latitude: Union[float, int],
    longitude: Union[float, int]
) -> Tuple[float, float]:
    """Validate latitude and longitude values.

    Enforces:
    - Type verification (numeric).
    - Valid WGS84 range: -90 <= latitude <= 90 and -180 <= longitude <= 180.
    - Explicit detection of swapped coordinates.
    - No silent swapping of latitude and longitude.

    Returns:
        Tuple of (float(latitude), float(longitude))
    """
    if latitude is None or longitude is None:
        raise ValueError("Latitude and longitude must not be None.")

    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError) as err:
        raise TypeError(f"Latitude and longitude must be numbers: lat={latitude}, lon={longitude}") from err

    # Check for swapped coordinates before standard bounds
    # In Giaspura/Punjab: lat ~ 30.8, lon ~ 75.9.
    # If someone passes lat ~ 75 and lon ~ 30, it must be rejected without swapping!
    if abs(lat) > 90.0:
        raise ValueError(
            f"Invalid latitude {lat}. Latitude must be between -90 and 90 degrees. "
            f"Possible latitude/longitude swap detected (longitude was passed as latitude)."
        )

    if abs(lon) > 180.0:
        raise ValueError(
            f"Invalid longitude {lon}. Longitude must be between -180 and 180 degrees."
        )

    # Heuristic warning for swapped regional coordinates:
    # If lat is in [70, 85] and lon is in [20, 35], this strongly indicates an accidental swap of Punjab coords.
    if 60.0 <= lat <= 90.0 and 10.0 <= lon <= 40.0:
        raise ValueError(
            f"Latitude ({lat}) and longitude ({lon}) appear to be reversed for the study area. "
            f"Strict validation rejects inverted coordinates."
        )

    return lat, lon


def validate_geometry(geom: BaseGeometry) -> bool:
    """Validate that a Shapely geometry is non-null, non-empty, and valid."""
    if geom is None:
        return False
    if geom.is_empty:
        return False
    if not geom.is_valid:
        return False
    return True
