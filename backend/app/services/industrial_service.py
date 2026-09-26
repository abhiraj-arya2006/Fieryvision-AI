from typing import List, Dict, Any, Optional, Tuple
from app.core.geo import haversine_distance_m
from app.core.config import settings

# Pre-populated Giaspura Industrial Facilities (Ludhiana, Punjab)
GIASPURA_FACILITIES: List[Dict[str, Any]] = [
    {
        "id": "IND-GIAS-01",
        "name": "Giaspura Industrial Focal Point Cluster A",
        "site_type": "Auto Components & Forging",
        "latitude": 30.876210,
        "longitude": 75.899120,
        "address": "Focal Point Phase VI, Giaspura, Ludhiana",
        "operating_status": "active"
    },
    {
        "id": "IND-GIAS-02",
        "name": "Ludhiana Textile Dyeing & Processing Plant",
        "site_type": "Textile Dyeing & Boiler Unit",
        "latitude": 30.874100,
        "longitude": 75.897250,
        "address": "Giaspura Road near Sua Road, Ludhiana",
        "operating_status": "active"
    },
    {
        "id": "IND-GIAS-03",
        "name": "Punjab Cycle Heavy Stamping & Electroplating",
        "site_type": "Electroplating & Metal Finishing",
        "latitude": 30.878500,
        "longitude": 75.901500,
        "address": "Opposite Dhandari Kalan Railway Colony, Giaspura",
        "operating_status": "active"
    },
    {
        "id": "IND-GIAS-04",
        "name": "Giaspura Boiler & Casting Works",
        "site_type": "Industrial Boiler Plant",
        "latitude": 30.872800,
        "longitude": 75.895100,
        "address": "Giaspura Canal Road, Ludhiana",
        "operating_status": "active"
    },
    {
        "id": "IND-GIAS-05",
        "name": "Dhandari Kalan Freight & Warehousing Hub",
        "site_type": "Logistics & Material Storage",
        "latitude": 30.881000,
        "longitude": 75.905000,
        "address": "Dhandari Kalan Industrial Zone, Ludhiana",
        "operating_status": "active"
    },
    {
        "id": "IND-GIAS-06",
        "name": "Giaspura Metal Heat Treatment Facility",
        "site_type": "Furnace & Heat Treatment",
        "latitude": 30.876900,
        "longitude": 75.896800,
        "address": "Street No. 4, Giaspura Industrial Belt",
        "operating_status": "active"
    }
]

def get_all_facilities(db: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Return all industrial facilities and active global hotspots across the world."""
    facilities: List[Dict[str, Any]] = []

    # 1. Base Giaspura industrial facilities
    for fac in GIASPURA_FACILITIES:
        facilities.append({
            "id": fac["id"],
            "name": fac["name"],
            "site_type": fac["site_type"],
            "latitude": fac["latitude"],
            "longitude": fac["longitude"],
            "address": fac.get("address", "Giaspura, Ludhiana, Punjab"),
            "operating_status": fac.get("operating_status", "active"),
            "country": "India",
            "continent": "Asia",
            "classification": "industrial_facility",
            "risk_tier": "low",
            "hotspot_id": None
        })

    # 2. Add all active hotspots across the globe using Hotspot Intelligence Engine
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
        logger.warning(f"Could not load hotspot_engine for facilities: {e}")
        try:
            from app.services.hotspot_service import GLOBAL_HOTSPOT_SEEDS
            for seed in GLOBAL_HOTSPOT_SEEDS:
                if seed.get("status") == "active":
                    facilities.append({
                        "id": seed["id"],
                        "name": seed["name"],
                        "site_type": seed.get("classification", "Active Hotspot").replace("_", " ").title(),
                        "latitude": seed["centroid_lat"],
                        "longitude": seed["centroid_lon"],
                        "address": f"{seed.get('region', '')}, {seed.get('country', '')}",
                        "operating_status": seed.get("status", "active"),
                        "country": seed.get("country", "Global"),
                        "continent": seed.get("continent", "Global"),
                        "classification": seed.get("classification", "active_hotspot"),
                        "risk_tier": seed.get("risk_tier", "moderate"),
                        "hotspot_id": seed["id"]
                    })
        except Exception:
            pass

    return facilities

def find_nearest_facility(lat: float, lon: float) -> Tuple[Optional[Dict[str, Any]], float]:
    """
    Find the nearest industrial facility to given coordinates.
    Returns (facility_dict, distance_in_meters).
    """
    if not GIASPURA_FACILITIES:
        return None, float("inf")

    nearest_facility = None
    min_distance = float("inf")

    for fac in GIASPURA_FACILITIES:
        dist = haversine_distance_m(lat, lon, fac["latitude"], fac["longitude"])
        if dist < min_distance:
            min_distance = dist
            nearest_facility = fac

    return nearest_facility, min_distance

def is_inside_industrial_zone(lat: float, lon: float, threshold_m: float = 800.0) -> bool:
    """
    Check if coordinates fall within 800 meters of a known Giaspura industrial facility.
    """
    _, dist = find_nearest_facility(lat, lon)
    return dist <= threshold_m

import os
import logging

logger = logging.getLogger("fieryvision.landcover")

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

# Standard ESA WorldCover 10m class map
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
    """Sample land-cover class from local ESA WorldCover 10m GeoTIFF raster."""
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

def get_landcover_context(lat: float, lon: float) -> str:
    """
    Determine landcover classification using authoritative ESA WorldCover satellite raster
    with distance-to-facility heuristic fallback.
    """
    esa_class = get_esa_raster_landcover(lat, lon)
    fac, dist = find_nearest_facility(lat, lon)
    
    if esa_class:
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

    # Fallback heuristic if raster is absent or point is outside bounds
    if dist <= 1200.0:
        return "Industrial & Built-up Land (Giaspura Industrial Area)"
    elif dist <= 3000.0:
        return "Mixed Urban / Light Industrial Zone"
    else:
        return "Agricultural / Semi-Urban Buffer Zone"
