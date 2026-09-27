"""Global Geospatial Facility & Landcover Intelligence Service.

Provides:
- Real-time OpenStreetMap Overpass facility query with spatial-grid caching and rate-limiting
- Honest global landcover classification (ESA WorldCover 10m where available, 'Unknown / unavailable' otherwise)
- Zero hardcoded Giaspura facilities or synthetic fallback classifications.
"""

import os
import time
import math
import logging
from typing import List, Dict, Any, Optional, Tuple
import httpx

from app.core.geo import haversine_distance_m
from app.core.config import settings

logger = logging.getLogger("fieryvision.geospatial")

# Overpass API endpoints with failover
OVERPASS_ENDPOINTS = [
    settings.OVERPASS_API_URL,
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter"
]

# Grid-based facility cache: key -> (timestamp, list of facilities)
_FACILITY_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_CACHE_TTL_SECONDS = settings.OVERPASS_CACHE_TTL_HOURS * 3600
_NEGATIVE_CACHE_TTL_SECONDS = 300  # 5 min cooldown on empty/failed queries


def _grid_key(lat: float, lon: float) -> str:
    """Quantize coordinates to ~5.5km grid cell (0.05 degree) for spatial caching."""
    return f"{round(lat * 20) / 20:.2f}_{round(lon * 20) / 20:.2f}"


def query_osm_facilities_sync(lat: float, lon: float, radius_m: int = 5000) -> List[Dict[str, Any]]:
    """
    Query OpenStreetMap Overpass API for real mapped industrial facilities around (lat, lon).
    Cached per spatial grid cell to prevent duplicate requests.
    """
    key = _grid_key(lat, lon)
    now = time.time()

    if key in _FACILITY_CACHE:
        ts, data = _FACILITY_CACHE[key]
        ttl = _CACHE_TTL_SECONDS if data else _NEGATIVE_CACHE_TTL_SECONDS
        if now - ts < ttl:
            return data

    overpass_query = f"""[out:json][timeout:6];
(
  node["landuse"="industrial"](around:{radius_m},{lat},{lon});
  way["landuse"="industrial"](around:{radius_m},{lat},{lon});
  node["industrial"](around:{radius_m},{lat},{lon});
  way["industrial"](around:{radius_m},{lat},{lon});
  node["man_made"="works"](around:{radius_m},{lat},{lon});
  way["man_made"="works"](around:{radius_m},{lat},{lon});
  node["power"="plant"](around:{radius_m},{lat},{lon});
  way["power"="plant"](around:{radius_m},{lat},{lon});
  node["building"="industrial"](around:{radius_m},{lat},{lon});
  way["building"="industrial"](around:{radius_m},{lat},{lon});
);
out center 5;
"""
    facilities: List[Dict[str, Any]] = []
    headers = {"User-Agent": "FieryVisionAI/2.0 (Global Industrial Context)"}

    for endpoint in OVERPASS_ENDPOINTS:
        try:
            with httpx.Client(timeout=6.0) as client:
                res = client.post(endpoint, data={"data": overpass_query}, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    elements = data.get("elements", [])
                    for el in elements:
                        tags = el.get("tags", {})
                        # Determine coordinates from node or center of way/relation
                        f_lat = el.get("lat") or (el.get("center", {}).get("lat"))
                        f_lon = el.get("lon") or (el.get("center", {}).get("lon"))
                        if f_lat is None or f_lon is None:
                            continue

                        name = tags.get("name")
                        site_type = (
                            tags.get("industrial")
                            or tags.get("landuse")
                            or tags.get("man_made")
                            or tags.get("power")
                            or "industrial_facility"
                        )
                        if not name:
                            name = f"Mapped {site_type.replace('_', ' ').title()}"

                        facilities.append({
                            "id": f"OSM-{el.get('type')}-{el.get('id')}",
                            "name": name,
                            "site_type": site_type.replace("_", " ").title(),
                            "latitude": float(f_lat),
                            "longitude": float(f_lon),
                            "address": tags.get("addr:street") or tags.get("addr:city") or "OpenStreetMap Context",
                            "operating_status": "active",
                            "source": "OpenStreetMap Overpass API"
                        })
                    _FACILITY_CACHE[key] = (now, facilities)
                    return facilities
        except Exception as exc:
            logger.debug("Overpass query to %s skipped: %s", endpoint, exc)
            continue

    # Record empty cache with negative TTL on network failure
    _FACILITY_CACHE[key] = (now, [])
    return []


def find_nearest_facility(
    lat: float,
    lon: float,
    max_search_radius_m: float = 5000.0,
    only_cached: bool = False
) -> Tuple[Optional[Dict[str, Any]], float]:
    """
    Find the nearest real mapped industrial facility to given coordinates.
    Returns (facility_dict, distance_in_meters).
    If only_cached=True, checks spatial cache without issuing external network requests.
    If no mapped facility exists within radius, returns (None, float('inf')).
    Never invents or defaults to a distant facility.
    """
    if only_cached:
        key = _grid_key(lat, lon)
        if key in _FACILITY_CACHE:
            nearby = _FACILITY_CACHE[key][1]
        else:
            return None, float("inf")
    else:
        nearby = query_osm_facilities_sync(lat, lon, radius_m=int(max_search_radius_m))

    if not nearby:
        return None, float("inf")

    nearest_facility = None
    min_distance = float("inf")

    for fac in nearby:
        dist = haversine_distance_m(lat, lon, fac["latitude"], fac["longitude"])
        if dist < min_distance:
            min_distance = dist
            nearest_facility = fac

    if min_distance <= max_search_radius_m:
        return nearest_facility, min_distance
    return None, float("inf")


def is_inside_industrial_zone(lat: float, lon: float, threshold_m: float = 800.0) -> bool:
    """Check if coordinates fall within threshold distance of a real verified industrial site."""
    _, dist = find_nearest_facility(lat, lon, max_search_radius_m=threshold_m)
    return dist <= threshold_m


def get_all_facilities(db: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Return all active global hotspots and cached industrial facilities across the world."""
    facilities: List[Dict[str, Any]] = []

    try:
        from app.services.hotspot_service import hotspot_engine
        resp = hotspot_engine.list_hotspots(page_size=100)
        for hs in resp.items:
            facilities.append({
                "id": hs.id,
                "name": hs.name,
                "site_type": hs.classification.replace("_", " ").title(),
                "latitude": hs.centroid_lat,
                "longitude": hs.centroid_lon,
                "address": f"{hs.region}, {hs.country}",
                "operating_status": hs.status,
                "country": hs.country,
                "continent": hs.continent,
                "classification": hs.classification,
                "risk_tier": hs.risk_tier,
                "hotspot_id": hs.id
            })
    except Exception as e:
        logger.warning("Could not load hotspot_engine for facilities: %s", e)

    return facilities


# =====================================================================
# HONEST GLOBAL LANDCOVER CLASSIFICATION
# =====================================================================

ESA_RASTER_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "data",
        "landcover",
        "giaspura_landcover_esa.tif"
    )
)

ESA_WORLDCOVER_CLASSES = {
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


def get_esa_raster_landcover(lat: float, lon: float) -> Optional[str]:
    """Sample land-cover class from local ESA WorldCover 10m GeoTIFF raster if coordinate is inside bounds."""
    if not os.path.exists(ESA_RASTER_PATH):
        return None
    try:
        import rasterio
        with rasterio.open(ESA_RASTER_PATH) as src:
            bounds = src.bounds
            if not (bounds.left <= lon <= bounds.right and bounds.bottom <= lat <= bounds.top):
                return None
            sampled = list(src.sample([(lon, lat)]))
            if sampled and len(sampled[0]) > 0:
                pixel_val = int(sampled[0][0])
                return ESA_WORLDCOVER_CLASSES.get(pixel_val)
    except Exception as exc:
        logger.debug("Rasterio ESA WorldCover sampling skipped: %s", exc)
    return None


def get_landcover_context(lat: float, lon: float, distance_to_facility: Optional[float] = None) -> str:
    """
    Determine landcover classification honestly:
    - If coordinate falls within available ESA WorldCover 10m raster, return true satellite classification.
    - Otherwise return 'Unknown / unavailable'.
    - NEVER defaults to Giaspura landcover or fabricates classes.
    """
    esa_class = get_esa_raster_landcover(lat, lon)
    if esa_class:
        dist = distance_to_facility if distance_to_facility is not None else find_nearest_facility(lat, lon)[1]
        if esa_class == "Built-up":
            if dist <= 1200.0:
                return "Built-up / Industrial (ESA WorldCover 10m)"
            return "Built-up / Urban (ESA WorldCover 10m)"
        elif esa_class == "Cropland":
            return "Cropland / Agricultural (ESA WorldCover 10m)"
        elif esa_class == "Tree cover":
            return "Tree cover / Forest (ESA WorldCover 10m)"
        elif esa_class == "Grassland":
            return "Grassland (ESA WorldCover 10m)"
        elif esa_class == "Bare / sparse vegetation":
            return "Bare Land / Sparse Vegetation (ESA WorldCover 10m)"
        elif esa_class == "Water":
            return "Water Body (ESA WorldCover 10m)"
        return f"{esa_class} (ESA WorldCover 10m)"

    return "Unknown / unavailable"
