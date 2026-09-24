"""Industrial infrastructure context service using EPSG:32643 metric projections."""

import json
import os
from typing import Dict, List, Optional, Any, Tuple
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform
from shapely.geometry.base import BaseGeometry

from .validators import validate_coordinates, validate_geometry

DEFAULT_GEOJSON_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "industrial", "industrial_sites.geojson"
)

TARGET_CRS = "EPSG:32643"  # UTM Zone 43N (appropriate for Punjab, India)
SOURCE_CRS = "EPSG:4326"


class IndustrialSiteRecord:
    def __init__(
        self,
        geom_utm: BaseGeometry,
        properties: Dict[str, Any],
        is_zone: bool
    ):
        self.geom_utm = geom_utm
        self.properties = properties
        self.is_zone = is_zone
        self.name = properties.get("name")
        self.facility_type = properties.get("facility_type", "industrial")


class IndustrialContextService:
    """Service to compute proximity and spatial density relative to industrial infrastructure."""

    def __init__(self, geojson_path: Optional[str] = None, feature_collection: Optional[dict] = None):
        self.transformer = Transformer.from_crs(SOURCE_CRS, TARGET_CRS, always_xy=True)
        self.records: List[IndustrialSiteRecord] = []
        self._load_features(geojson_path, feature_collection)

    def _load_features(self, geojson_path: Optional[str], feature_collection: Optional[dict]):
        data = None
        if feature_collection is not None:
            data = feature_collection
        else:
            path = geojson_path or DEFAULT_GEOJSON_PATH
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

        if not data or "features" not in data:
            self.records = []
            return

        for feat in data.get("features", []):
            raw_geom = feat.get("geometry")
            if not raw_geom:
                continue

            try:
                geom_4326 = shape(raw_geom)
            except Exception:
                continue

            if not validate_geometry(geom_4326):
                continue

            # Project EPSG:4326 (lon, lat) to EPSG:32643 (UTM 43N meters)
            geom_utm = transform(self.transformer.transform, geom_4326)
            props = feat.get("properties", {})
            f_type = props.get("facility_type", "")
            raw_tags = props.get("raw_tags", {})

            is_zone = (
                f_type == "industrial_zone"
                or raw_tags.get("landuse") == "industrial"
            )

            self.records.append(IndustrialSiteRecord(geom_utm, props, is_zone))

    @property
    def facility_count(self) -> int:
        return len(self.records)

    def get_industrial_context(
        self,
        latitude: float,
        longitude: float
    ) -> Dict[str, Any]:
        """Determine industrial context for a given WGS84 coordinate.

        Returns:
            Dict containing:
            - nearest_facility_name
            - nearest_facility_type
            - distance_to_facility_m
            - inside_industrial_zone
            - distance_to_nearest_industrial_zone
            - industrial_density_5km
            - proximity_context (language reflecting correlation, not causation)
        """
        lat, lon = validate_coordinates(latitude, longitude)

        # Empty facility handling
        if not self.records:
            return {
                "nearest_facility_name": None,
                "nearest_facility_type": None,
                "distance_to_facility_m": None,
                "inside_industrial_zone": False,
                "distance_to_nearest_industrial_zone": None,
                "industrial_density_5km": 0,
                "proximity_context": "No recorded industrial infrastructure within database"
            }

        point_4326 = Point(lon, lat)
        point_utm = transform(self.transformer.transform, point_4326)

        nearest_facility = None
        min_facility_dist = float("inf")

        nearest_zone = None
        min_zone_dist = float("inf")
        inside_zone = False

        density_count_5km = 0
        search_radius_5km = 5000.0

        for rec in self.records:
            dist = rec.geom_utm.distance(point_utm)

            if dist < min_facility_dist:
                min_facility_dist = dist
                nearest_facility = rec

            if rec.is_zone:
                # Check point containment or intersection with polygon
                if rec.geom_utm.intersects(point_utm) or rec.geom_utm.contains(point_utm):
                    inside_zone = True
                    min_zone_dist = 0.0
                elif dist < min_zone_dist:
                    min_zone_dist = dist
                    nearest_zone = rec

            if dist <= search_radius_5km:
                density_count_5km += 1

        nearest_facility_name = nearest_facility.name if nearest_facility else None
        nearest_facility_type = nearest_facility.facility_type if nearest_facility else None
        facility_dist_rounded = round(min_facility_dist, 2) if min_facility_dist != float("inf") else None

        if inside_zone:
            zone_dist_rounded = 0.0
        elif min_zone_dist != float("inf"):
            zone_dist_rounded = round(min_zone_dist, 2)
        else:
            zone_dist_rounded = None

        # Careful non-causal language adhering to project guidelines
        if inside_zone:
            proximity_context = "Located inside designated industrial zone"
        elif facility_dist_rounded is not None and facility_dist_rounded <= 500.0:
            proximity_context = f"Near industrial infrastructure ({nearest_facility_name or nearest_facility_type}, ~{int(facility_dist_rounded)}m)"
        elif facility_dist_rounded is not None and facility_dist_rounded <= 2000.0:
            proximity_context = f"In vicinity of industrial infrastructure (~{int(facility_dist_rounded)}m)"
        else:
            proximity_context = "Outside immediate proximity of recorded industrial infrastructure"

        return {
            "nearest_facility_name": nearest_facility_name,
            "nearest_facility_type": nearest_facility_type,
            "distance_to_facility_m": facility_dist_rounded,
            "inside_industrial_zone": inside_zone,
            "distance_to_nearest_industrial_zone": zone_dist_rounded,
            "industrial_density_5km": density_count_5km,
            "proximity_context": proximity_context
        }


# Convenience module-level singleton and functions
_DEFAULT_SERVICE: Optional[IndustrialContextService] = None


def get_default_industrial_service() -> IndustrialContextService:
    global _DEFAULT_SERVICE
    if _DEFAULT_SERVICE is None:
        _DEFAULT_SERVICE = IndustrialContextService()
    return _DEFAULT_SERVICE


def calculate_industrial_context(latitude: float, longitude: float, service: Optional[IndustrialContextService] = None) -> Dict[str, Any]:
    svc = service or get_default_industrial_service()
    return svc.get_industrial_context(latitude, longitude)
