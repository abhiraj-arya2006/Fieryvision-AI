"""Land-cover context service using authoritative ESA WorldCover classification."""

import os
from typing import Optional, Dict
import rasterio

from .validators import validate_coordinates

DEFAULT_RASTER_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "landcover", "giaspura_landcover_esa.tif"
)

# Standard ESA WorldCover 10m class map conforming to required categories
ESA_WORLDCOVER_CLASSES: Dict[int, str] = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Water",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}


class LandCoverService:
    """Service to look up land-cover classifications from authoritative ESA WorldCover raster data."""

    def __init__(self, raster_path: Optional[str] = None):
        self.raster_path = raster_path or DEFAULT_RASTER_PATH

    def get_landcover_class(self, latitude: float, longitude: float) -> str:
        """Query the land-cover class at the specified latitude and longitude (WGS84).

        Returns:
            The land-cover category name (e.g., 'Built-up', 'Cropland', 'Tree cover', 'Water').
        """
        lat, lon = validate_coordinates(latitude, longitude)

        if not os.path.exists(self.raster_path):
            raise FileNotFoundError(
                f"Land-cover raster not found at {self.raster_path}. "
                f"Run scripts/acquire_landcover.py to extract ESA WorldCover data."
            )

        with rasterio.open(self.raster_path) as src:
            bounds = src.bounds
            # Check if point falls within raster bounds
            if not (bounds.left <= lon <= bounds.right and bounds.bottom <= lat <= bounds.top):
                return "Unknown (Out of Bounds)"

            # Sample expects coordinates as (x, y) = (lon, lat) for EPSG:4326
            sampled = list(src.sample([(lon, lat)]))
            if not sampled or len(sampled[0]) == 0:
                return "Unknown"

            pixel_val = int(sampled[0][0])
            return ESA_WORLDCOVER_CLASSES.get(pixel_val, "Unknown")


_DEFAULT_LANDCOVER_SERVICE: Optional[LandCoverService] = None


def get_default_landcover_service() -> LandCoverService:
    global _DEFAULT_LANDCOVER_SERVICE
    if _DEFAULT_LANDCOVER_SERVICE is None:
        _DEFAULT_LANDCOVER_SERVICE = LandCoverService()
    return _DEFAULT_LANDCOVER_SERVICE


def lookup_landcover(latitude: float, longitude: float, service: Optional[LandCoverService] = None) -> str:
    svc = service or get_default_landcover_service()
    return svc.get_landcover_class(latitude, longitude)
