"""Acquire authoritative OpenStreetMap industrial and infrastructure data for Giaspura, Ludhiana."""

import json
import os
import time
import requests
from shapely.geometry import Point, Polygon, LineString, mapping, shape

GIASPURA_LAT = 30.875625
GIASPURA_LON = 75.898481
SEARCH_RADIUS_M = 10000

OVERPASS_ENDPOINTS = [
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "industrial")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "industrial_sites.geojson")


def build_overpass_query(lat: float, lon: float, radius: int) -> str:
    return f"""[out:json][timeout:90];
(
  node["landuse"="industrial"](around:{radius},{lat},{lon});
  way["landuse"="industrial"](around:{radius},{lat},{lon});
  relation["landuse"="industrial"](around:{radius},{lat},{lon});

  node["industrial"](around:{radius},{lat},{lon});
  way["industrial"](around:{radius},{lat},{lon});
  relation["industrial"](around:{radius},{lat},{lon});

  node["building"="industrial"](around:{radius},{lat},{lon});
  way["building"="industrial"](around:{radius},{lat},{lon});

  node["man_made"="works"](around:{radius},{lat},{lon});
  way["man_made"="works"](around:{radius},{lat},{lon});

  node["power"="plant"](around:{radius},{lat},{lon});
  way["power"="plant"](around:{radius},{lat},{lon});

  node["power"="substation"](around:{radius},{lat},{lon});
  way["power"="substation"](around:{radius},{lat},{lon});

  node["amenity"="fuel"](around:{radius},{lat},{lon});
  way["amenity"="fuel"](around:{radius},{lat},{lon});

  node["storage"](around:{radius},{lat},{lon});
  way["storage"](around:{radius},{lat},{lon});
);
out body geom;
"""


def determine_facility_type(tags: dict) -> str:
    if tags.get("landuse") == "industrial":
        return "industrial_zone"
    if "industrial" in tags:
        val = tags["industrial"]
        return f"industrial_{val}" if val != "yes" else "industrial"
    if tags.get("building") == "industrial":
        return "industrial_building"
    if tags.get("power") in ("substation", "plant"):
        return f"power_{tags['power']}"
    if tags.get("amenity") == "fuel":
        return "fuel_station"
    if tags.get("man_made") == "works":
        return "industrial_works"
    if "storage" in tags:
        return f"storage_{tags['storage']}"
    return "industrial_site"


def parse_element_to_feature(el: dict):
    tags = el.get("tags", {})
    facility_type = determine_facility_type(tags)
    name = tags.get("name")
    if not name or not name.strip():
        # Handle missing name safely with descriptive fallback
        name = f"Unnamed {facility_type.replace('_', ' ').title()}"

    el_type = el.get("type")
    osm_id = el.get("id")

    geom = None
    if el_type == "node":
        lat = el.get("lat")
        lon = el.get("lon")
        if lat is not None and lon is not None:
            geom = Point(lon, lat)
    elif el_type in ("way", "relation"):
        geom_coords = el.get("geometry", [])
        if len(geom_coords) >= 3:
            coords = [[pt["lon"], pt["lat"]] for pt in geom_coords if "lon" in pt and "lat" in pt]
            if len(coords) >= 3:
                # If first and last match (or it is a closed loop), form Polygon
                if coords[0] == coords[-1] and len(coords) >= 4:
                    poly = Polygon(coords)
                    if poly.is_valid:
                        geom = poly
                    else:
                        geom = poly.buffer(0)
                elif len(coords) >= 3 and (coords[0][0] == coords[-1][0] and coords[0][1] == coords[-1][1]):
                    poly = Polygon(coords)
                    geom = poly if poly.is_valid else poly.buffer(0)
                else:
                    geom = LineString(coords)
        elif "center" in el:
            geom = Point(el["center"]["lon"], el["center"]["lat"])

    if geom is None or geom.is_empty:
        return None

    # Calculate centroid coordinates (WGS84 lat/lon)
    centroid = geom.centroid
    rep_lat = round(float(centroid.y), 6)
    rep_lon = round(float(centroid.x), 6)

    # Validate coordinate range
    if not (-90.0 <= rep_lat <= 90.0) or not (-180.0 <= rep_lon <= 180.0):
        return None

    feature = {
        "type": "Feature",
        "geometry": mapping(geom),
        "properties": {
            "osm_id": osm_id,
            "osm_type": el_type,
            "name": name,
            "facility_type": facility_type,
            "latitude": rep_lat,
            "longitude": rep_lon,
            "source": "OpenStreetMap",
            "raw_tags": tags
        }
    }
    return feature


def fetch_and_save_industrial_sites(output_path: str = OUTPUT_FILE):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    query = build_overpass_query(GIASPURA_LAT, GIASPURA_LON, SEARCH_RADIUS_M)

    headers = {
        "User-Agent": "FieryVisionAI/1.0 (authoritative Giaspura industrial context)",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    raw_data = None
    last_error = None

    for endpoint in OVERPASS_ENDPOINTS:
        try:
            print(f"Querying Overpass endpoint: {endpoint}")
            resp = requests.post(endpoint, data=query.encode("utf-8"), headers=headers, timeout=60)
            if resp.status_code == 200:
                raw_data = resp.json()
                print(f"Successfully received data from {endpoint}")
                break
            else:
                print(f"Endpoint {endpoint} returned status {resp.status_code}")
        except Exception as err:
            print(f"Error querying {endpoint}: {err}")
            last_error = err
            time.sleep(1)

    if not raw_data or "elements" not in raw_data:
        raise RuntimeError(f"Failed to acquire industrial data from Overpass. Last error: {last_error}")

    elements = raw_data["elements"]
    print(f"Total raw elements received: {len(elements)}")

    features = []
    seen_ids = set()

    for el in elements:
        uid = (el.get("type"), el.get("id"))
        if uid in seen_ids:
            continue
        seen_ids.add(uid)

        feat = parse_element_to_feature(el)
        if feat:
            features.append(feat)

    geojson_doc = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
            }
        },
        "features": features
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson_doc, f, indent=2)

    print(f"Saved {len(features)} validated features to: {output_path}")
    return output_path


if __name__ == "__main__":
    fetch_and_save_industrial_sites()
