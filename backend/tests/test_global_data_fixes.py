import math
import asyncio
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from main import app
from app.services.emergency_service import (
    emergency_service,
    calculate_bearing_deg,
    bearing_to_cardinal,
    EXPANDING_RADII_KM
)
from app.services.industrial_service import (
    get_worldcover_tile_info,
    get_landcover_context,
    query_esri_landcover,
    SENTINEL2_LANDCOVER_CLASSES,
    ESA_WORLDCOVER_CLASSES,
    _LANDCOVER_CACHE
)
from app.services.hotspot_service import hotspot_engine

client = TestClient(app)


# =====================================================================
# ISSUE 1: EMERGENCY FACILITIES EXPANDING RADIUS & GROUNDED CHAT
# =====================================================================

def test_bearing_to_cardinal():
    """Verify compass bearing to 16-point cardinal conversion."""
    assert bearing_to_cardinal(0.0) == "N"
    assert bearing_to_cardinal(45.0) == "NE"
    assert bearing_to_cardinal(90.0) == "E"
    assert bearing_to_cardinal(180.0) == "S"
    assert bearing_to_cardinal(225.0) == "SW"
    assert bearing_to_cardinal(270.0) == "W"
    assert bearing_to_cardinal(315.0) == "NW"


def test_emergency_expanding_radius_search():
    """Test expanding radius emergency search returns nearest facilities with early exit."""
    # Test near Oroville, CA where curated facilities exist
    lat, lon = 39.518, -121.545
    result = asyncio.run(emergency_service.find_nearest_emergency_facilities(lat, lon))

    assert "nearest_fire_station" in result
    assert "nearest_hospital" in result
    assert "search_radius_reached_km" in result

    # In Oroville, both fire station and hospital are within 10km, so early exit triggers
    assert result["nearest_fire_station"] is not None
    assert result["nearest_hospital"] is not None
    assert result["search_radius_reached_km"] <= 25.0
    assert result["fire_station_within_25km"] is True
    assert result["hospital_within_25km"] is True

    fs = result["nearest_fire_station"]
    assert fs.facility_type == "fire_station"
    assert fs.distance_m >= 0.0
    assert fs.bearing_deg >= 0.0
    assert fs.cardinal_direction is not None


def test_analyse_location_emergency_context_integration():
    """Test POST /api/analyse-location includes emergency facilities in response schema."""
    res = client.post("/api/analyse-location", json={"latitude": 39.518, "longitude": -121.545})
    assert res.status_code == 200
    data = res.json()

    assert "nearest_fire_station" in data
    assert "nearest_hospital" in data
    assert "emergency_facilities" in data
    assert "emergency_search_radius_km" in data
    assert data["nearest_fire_station"] is not None
    assert "CAL FIRE" in data["nearest_fire_station"]["name"]


def test_emergency_grounded_chat_answers():
    """Test /api/chat answers emergency facility questions with exact distance, bearing, and zone."""
    context = {
        "latitude": 39.518,
        "longitude": -121.545,
        "nearest_fire_station": {
            "name": "CAL FIRE Butte County Station 64",
            "distance_m": 1200.0,
            "bearing_deg": 45.0,
            "cardinal_direction": "NE"
        },
        "nearest_hospital": {
            "name": "Oroville Hospital Emergency Department",
            "distance_m": 2500.0,
            "bearing_deg": 180.0,
            "cardinal_direction": "S",
            "specialty_verified": True
        }
    }

    # Ask about fire stations
    res_fs = client.post("/api/chat", json={
        "question": "Are there any fire stations nearby?",
        "context": context
    })
    assert res_fs.status_code == 200
    ans_fs = res_fs.json()["response"]
    assert "CAL FIRE Butte County Station 64" in ans_fs
    assert "1.2 km away" in ans_fs
    assert "Within 25 km" in ans_fs

    # Ask about hospitals
    res_hosp = client.post("/api/chat", json={
        "question": "Where is the nearest hospital and trauma center?",
        "context": context
    })
    assert res_hosp.status_code == 200
    ans_hosp = res_hosp.json()["response"]
    assert "Oroville Hospital Emergency Department" in ans_hosp
    assert "2.5 km away" in ans_hosp
    assert "Burn/Trauma" in ans_hosp


# =====================================================================
# ISSUE 2: GLOBAL LAND COVER (SENTINEL-2 10M VIA ESRI)
# =====================================================================

def test_worldcover_dynamic_tile_id_calculation():
    """Verify backward compatibility ESA WorldCover tile ID calculation helper."""
    tile, url, ox, oy = get_worldcover_tile_info(30.88, 75.85)
    assert tile == "ESA_WorldCover_10m_2021_v200_N30E075_Map.tif"
    assert "esa-worldcover.s3.amazonaws.com" in url
    assert ox == 75.0
    assert oy == 33.0

    tile_br, url_br, ox_br, oy_br = get_worldcover_tile_info(-8.35, -44.16)
    assert tile_br == "ESA_WorldCover_10m_2021_v200_S09W045_Map.tif"
    assert ox_br == -45.0
    assert oy_br == -6.0


def test_esri_sentinel2_global_landcover_all_continents():
    """
    Verify global Sentinel-2 10m land cover lookup across continents:
    Australia, South America (Brazil), Europe (Paris), North America (California), Asia (India).
    """
    # 1. Western Australia (-23.56135, 124.77069) -> Rangeland (code 11)
    lc_aus = get_landcover_context(-23.56135, 124.77069)
    assert lc_aus == "Rangeland (Sentinel-2 10m)"

    # 2. Brazil (-8.35073, -44.16361) -> Trees (code 2)
    lc_br = get_landcover_context(-8.35073, -44.16361)
    assert lc_br == "Trees / Forest (Sentinel-2 10m)"

    # 3. Paris, Europe (48.8566, 2.3522) -> Built Area (code 7)
    lc_eu = get_landcover_context(48.8566, 2.3522)
    assert "Built Area" in lc_eu
    assert "Sentinel-2 10m" in lc_eu

    # 4. California, North America (39.518, -121.545) -> Built Area (code 7)
    lc_us = get_landcover_context(39.518, -121.545)
    assert "Built Area" in lc_us
    assert "Sentinel-2 10m" in lc_us

    # 5. Punjab, India (30.8756, 75.8984) -> Built Area (code 7)
    lc_in = get_landcover_context(30.8756, 75.8984)
    assert "Built Area" in lc_in
    assert "Sentinel-2 10m" in lc_in


def test_esri_landcover_built_area_industrial_vs_urban():
    """Verify Built Area distinction between Industrial (<= 1200m) and Urban (> 1200m)."""
    # Force mock coordinates with code 7 (Built Area)
    lat, lon = 48.8566, 2.3522
    lc_ind = get_landcover_context(lat, lon, distance_to_facility=500.0)
    assert lc_ind == "Built Area / Industrial (Sentinel-2 10m)"

    lc_urb = get_landcover_context(lat, lon, distance_to_facility=2500.0)
    assert lc_urb == "Built Area / Urban (Sentinel-2 10m)"


def test_esri_landcover_honest_unknown_and_mocked_network_failure():
    """Verify deep ocean or network failure gracefully returns 'Unknown / unavailable' without guessing."""
    # Deep ocean point outside coverage
    lc_ocean = get_landcover_context(0.0, -140.0)
    assert lc_ocean == "Unknown / unavailable"

    # Simulate network failure or timeout
    with patch("httpx.Client.get", side_effect=Exception("Connection timed out")):
        # Use uncached coordinate
        uncached_lat, uncached_lon = 88.0, 1.234
        res = query_esri_landcover(uncached_lat, uncached_lon)
        assert res is None

        ctx = get_landcover_context(uncached_lat, uncached_lon)
        assert ctx == "Unknown / unavailable"


# =====================================================================
# ISSUE 3: RECONCILE EVENT RISK SCORE AND LOCALIZED RISK SCORE
# =====================================================================

def test_risk_score_reconciliation_constraint():
    """
    Test that Localized Risk Score is strictly bounded to ±8 points of the Event Risk Score
    when matched to an existing active hotspot: abs(localized - event) <= 8.0.
    """
    active_hotspots = hotspot_engine.list_hotspots(page_size=10).items
    assert len(active_hotspots) > 0, "Database must have active hotspots"

    # Test top active hotspots
    for hs in active_hotspots[:5]:
        res = client.post("/api/analyse-location", json={
            "latitude": hs.centroid_lat,
            "longitude": hs.centroid_lon
        })
        assert res.status_code == 200
        data = res.json()

        assert data["event_risk_score"] is not None
        assert data["localized_risk_score"] is not None
        assert data["matched_hotspot_id"] is not None

        event_risk = data["event_risk_score"]
        localized_risk = data["localized_risk_score"]
        risk_diff = data["risk_difference"]

        # 1. Event risk equals the matched hotspot risk score
        assert round(event_risk, 1) == round(hs.risk_score, 1)

        # 2. Strict bounding: |localized - event| <= 8.0
        assert abs(localized_risk - event_risk) <= 8.0, f"Violation: localized={localized_risk}, event={event_risk}"

        # 3. Difference check
        assert risk_diff == round(localized_risk - event_risk, 1)

        # 4. Range check [0.0, 100.0]
        assert 0.0 <= localized_risk <= 100.0
        assert 0.0 <= event_risk <= 100.0


def test_risk_score_reconciliation_no_activity():
    """Test baseline coordinates with no thermal activity return 0.0 for both scores."""
    # London baseline coordinate (51.5074, -0.1278) with no thermal fires
    res = client.post("/api/analyse-location", json={"latitude": 51.5074, "longitude": -0.1278})
    assert res.status_code == 200
    data = res.json()

    assert data["event_risk_score"] == 0.0
    assert data["localized_risk_score"] == 0.0
    assert data["risk_difference"] == 0.0
    assert data["thermal_activity_detected"] is False
