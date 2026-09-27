"""Global Geospatial Facility & Landcover Intelligence Service.

Provides:
- Real-time OpenStreetMap Overpass facility query with spatial-grid caching and rate-limiting
- Honest global landcover classification via public Esri Sentinel-2 10m Land Cover ImageServer
- Batch prefetching via esriGeometryMultipoint for ultra-fast bulk resolution
- Zero hardcoded Giaspura facilities or synthetic fallback classifications.
"""

import os
import json
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
# HONEST GLOBAL LANDCOVER CLASSIFICATION (SENTINEL-2 10M VIA ESRI)
# =====================================================================

ESRI_SENTINEL2_LANDCOVER_URL = "https://ic.imagery1.arcgis.com/arcgis/rest/services/Sentinel2_10m_LandCover/ImageServer/getSamples"

SENTINEL2_LANDCOVER_CLASSES: Dict[int, str] = {
    0: "No Data",
    1: "Water",
    2: "Trees",
    4: "Flooded Vegetation",
    5: "Crops",
    7: "Built Area",
    8: "Bare Ground",
    9: "Snow/Ice",
    10: "Clouds",
    11: "Rangeland",
}

# Backward compatibility mapping for ESA WorldCover
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

_LANDCOVER_CACHE: Dict[str, Tuple[float, Optional[Dict[str, Any]]]] = {}
_LANDCOVER_CACHE_TTL_SECONDS: float = 86400.0  # 24 hours
_LANDCOVER_NEGATIVE_CACHE_TTL_SECONDS: float = 300.0  # 5 minutes for errors/out-of-bounds


def _landcover_cache_key(lat: float, lon: float) -> str:
    """Quantize coordinates to 3 decimal places (~110m) for landcover caching."""
    return f"{round(lat, 3):.3f}_{round(lon, 3):.3f}"


def prefetch_landcover_batch(coords: List[Tuple[float, float]], timeout_sec: float = 8.0) -> None:
    """
    Prefetch landcover classifications in batch for multiple coordinates using
    Esri ImageServer multipoint querying.
    Populates _LANDCOVER_CACHE for fast subsequent lookups.
    """
    now = time.time()
    uncached: List[Tuple[int, float, float]] = []
    for idx, (lat, lon) in enumerate(coords):
        key = _landcover_cache_key(lat, lon)
        if key in _LANDCOVER_CACHE:
            ts, data = _LANDCOVER_CACHE[key]
            ttl = _LANDCOVER_CACHE_TTL_SECONDS if data is not None else _LANDCOVER_NEGATIVE_CACHE_TTL_SECONDS
            if now - ts < ttl:
                continue
        uncached.append((idx, lat, lon))

    if not uncached:
        return

    # Process in chunks of 100 coordinates
    chunk_size = 100
    headers = {"User-Agent": "FieryVisionAI/2.0 (Global Sentinel-2 Landcover)"}

    for i in range(0, len(uncached), chunk_size):
        chunk = uncached[i:i + chunk_size]
        pts = [[lon, lat] for _, lat, lon in chunk]
        params = {
            "geometry": json.dumps({"points": pts, "spatialReference": {"wkid": 4326}}),
            "geometryType": "esriGeometryMultipoint",
            "f": "json"
        }
        try:
            with httpx.Client(timeout=timeout_sec) as client:
                resp = client.get(ESRI_SENTINEL2_LANDCOVER_URL, params=params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    samples = data.get("samples", [])
                    matched_indices = set()
                    for s in samples:
                        loc_id = s.get("locationId")
                        if loc_id is not None and 0 <= loc_id < len(chunk):
                            matched_indices.add(loc_id)
                            _, c_lat, c_lon = chunk[loc_id]
                            ckey = _landcover_cache_key(c_lat, c_lon)
                            val_str = s.get("value")
                            if val_str is not None and str(val_str).strip() != "":
                                try:
                                    code = int(val_str)
                                    if code in SENTINEL2_LANDCOVER_CLASSES and code != 0:
                                        _LANDCOVER_CACHE[ckey] = (now, {
                                            "code": code,
                                            "class_name": SENTINEL2_LANDCOVER_CLASSES[code],
                                            "source": "Esri Sentinel-2 10m Land Cover",
                                            "latitude": c_lat,
                                            "longitude": c_lon
                                        })
                                        continue
                                except (ValueError, TypeError):
                                    pass
                            _LANDCOVER_CACHE[ckey] = (now, None)
                    # For points that were omitted (e.g. ocean), record negative cache
                    for loc_id in range(len(chunk)):
                        if loc_id not in matched_indices:
                            _, c_lat, c_lon = chunk[loc_id]
                            ckey = _landcover_cache_key(c_lat, c_lon)
                            _LANDCOVER_CACHE[ckey] = (now, None)
        except Exception as exc:
            logger.debug("Prefetch landcover chunk failed: %s", exc)


def query_esri_landcover(
    lat: float,
    lon: float,
    timeout_sec: float = 8.0,
    only_cached: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Query the public Esri Sentinel-2 10m Land Cover ImageServer /getSamples endpoint.
    Returns land cover classification dict with code, class_name, and source, or None if unavailable.
    Cached for 24 hours per coordinate key (rounded to 3 decimal places).
    If only_cached=True, checks cache without issuing an external network call.
    Never invents, hallucinates, or defaults to hardcoded regional values.
    """
    cache_key = _landcover_cache_key(lat, lon)
    now = time.time()

    if cache_key in _LANDCOVER_CACHE:
        ts, cached_data = _LANDCOVER_CACHE[cache_key]
        ttl = _LANDCOVER_CACHE_TTL_SECONDS if cached_data is not None else _LANDCOVER_NEGATIVE_CACHE_TTL_SECONDS
        if now - ts < ttl:
            return cached_data

    if only_cached:
        return None

    params = {
        "geometry": json.dumps({"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}),
        "geometryType": "esriGeometryPoint",
        "f": "json"
    }
    headers = {"User-Agent": "FieryVisionAI/2.0 (Global Sentinel-2 Landcover)"}

    try:
        with httpx.Client(timeout=timeout_sec) as client:
            resp = client.get(ESRI_SENTINEL2_LANDCOVER_URL, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if "error" not in data and "samples" in data:
                    samples = data.get("samples", [])
                    if samples:
                        val_str = samples[0].get("value")
                        if val_str is not None and str(val_str).strip() != "":
                            code = int(val_str)
                            if code in SENTINEL2_LANDCOVER_CLASSES and code != 0:
                                class_name = SENTINEL2_LANDCOVER_CLASSES[code]
                                result = {
                                    "code": code,
                                    "class_name": class_name,
                                    "source": "Esri Sentinel-2 10m Land Cover",
                                    "latitude": lat,
                                    "longitude": lon
                                }
                                _LANDCOVER_CACHE[cache_key] = (now, result)
                                return result
    except Exception as exc:
        logger.debug("Esri landcover query failed for (%.4f, %.4f): %s", lat, lon, exc)

    _LANDCOVER_CACHE[cache_key] = (now, None)
    return None


def get_landcover_context(
    lat: float,
    lon: float,
    distance_to_facility: Optional[float] = None,
    only_cached: bool = False
) -> str:
    """
    Determine landcover classification honestly using global Esri Sentinel-2 10m:
    - If coordinate returns a valid Sentinel-2 class, format human-readable context.
    - If Built Area, distinguish Industrial vs Urban using distance_to_facility (<= 1200m).
    - If lookup fails or times out, returns 'Unknown / unavailable'.
    - NEVER defaults to Giaspura landcover or fabricates classes.
    """
    res = query_esri_landcover(lat, lon, only_cached=only_cached)
    if not res:
        return "Unknown / unavailable"

    class_name = res.get("class_name", "")
    if class_name == "Built Area":
        dist = distance_to_facility if distance_to_facility is not None else find_nearest_facility(lat, lon)[1]
        if dist <= 1200.0:
            return "Built Area / Industrial (Sentinel-2 10m)"
        return "Built Area / Urban (Sentinel-2 10m)"
    elif class_name == "Crops":
        return "Crops / Agricultural (Sentinel-2 10m)"
    elif class_name == "Trees":
        return "Trees / Forest (Sentinel-2 10m)"
    elif class_name == "Rangeland":
        return "Rangeland (Sentinel-2 10m)"
    elif class_name == "Bare Ground":
        return "Bare Ground (Sentinel-2 10m)"
    elif class_name == "Water":
        return "Water (Sentinel-2 10m)"
    elif class_name == "Flooded Vegetation":
        return "Flooded Vegetation (Sentinel-2 10m)"
    elif class_name == "Snow/Ice":
        return "Snow/Ice (Sentinel-2 10m)"
    elif class_name == "Clouds":
        return "Clouds / Unclassified (Sentinel-2 10m)"
    elif class_name:
        return f"{class_name} (Sentinel-2 10m)"

    return "Unknown / unavailable"


def get_esa_raster_landcover(lat: float, lon: float) -> Optional[str]:
    """
    Backward-compatibility wrapper for query_esri_landcover.
    Returns the class name string or None.
    """
    res = query_esri_landcover(lat, lon)
    return res["class_name"] if res else None


def get_worldcover_tile_info(lat: float, lon: float) -> Tuple[str, str, float, float]:
    """
    Backward-compatibility helper for ESA WorldCover 2021 v200 3x3 degree tile identifier.
    """
    tile_lat = int(math.floor(lat / 3.0) * 3)
    tile_lon = int(math.floor(lon / 3.0) * 3)

    lat_str = f"N{tile_lat:02d}" if tile_lat >= 0 else f"S{abs(tile_lat):02d}"
    lon_str = f"E{tile_lon:03d}" if tile_lon >= 0 else f"W{abs(tile_lon):03d}"
    tile_name = f"ESA_WorldCover_10m_2021_v200_{lat_str}{lon_str}_Map.tif"
    tile_url = f"https://esa-worldcover.s3.amazonaws.com/v200/2021/map/{tile_name}"

    origin_x = float(tile_lon)
    origin_y = float(tile_lat + 3)
    return tile_name, tile_url, origin_x, origin_y
