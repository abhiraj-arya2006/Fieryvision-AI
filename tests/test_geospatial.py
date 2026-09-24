"""Tests for geospatial context layer: industrial infrastructure, land cover, and proximity."""

import os
import tempfile
import pytest
import rasterio
from rasterio.transform import from_origin
import numpy as np

from data_processing.geospatial.validators import validate_coordinates, validate_geometry
from data_processing.geospatial.industrial_service import (
    IndustrialContextService,
    IndustrialSiteRecord,
    calculate_industrial_context,
)
from data_processing.geospatial.landcover_service import (
    LandCoverService,
    ESA_WORLDCOVER_CLASSES,
    lookup_landcover,
)
from data_processing.geospatial.enrichment import enrich_thermal_event
from shapely.geometry import Point, Polygon


@pytest.fixture
def small_geojson_fixture():
    """Small fixture in Giaspura, Ludhiana (EPSG:4326)."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [75.898481, 30.875625]
                },
                "properties": {
                    "osm_id": 101,
                    "osm_type": "node",
                    "name": "Substation Giaspura",
                    "facility_type": "power_substation",
                    "latitude": 30.875625,
                    "longitude": 75.898481,
                    "source": "OpenStreetMap",
                    "raw_tags": {"power": "substation"}
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [75.910000, 30.875625]
                },
                "properties": {
                    "osm_id": 102,
                    "osm_type": "node",
                    "name": "East Fuel Depot",
                    "facility_type": "fuel_station",
                    "latitude": 30.875625,
                    "longitude": 75.910000,
                    "source": "OpenStreetMap",
                    "raw_tags": {"amenity": "fuel"}
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [75.890000, 30.870000],
                        [75.895000, 30.870000],
                        [75.895000, 30.875000],
                        [75.890000, 30.875000],
                        [75.890000, 30.870000]
                    ]]
                },
                "properties": {
                    "osm_id": 201,
                    "osm_type": "way",
                    "name": "Giaspura Industrial Area Phase II",
                    "facility_type": "industrial_zone",
                    "latitude": 30.872500,
                    "longitude": 75.892500,
                    "source": "OpenStreetMap",
                    "raw_tags": {"landuse": "industrial"}
                }
            }
        ]
    }


@pytest.fixture
def temp_landcover_raster():
    """Create a temporary 10x10 GeoTIFF with known ESA WorldCover classes."""
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as f:
        path = f.name

    # Transform covering lon 75.80 to 75.90, lat 30.80 to 30.90
    transform = from_origin(75.80, 30.90, 0.01, 0.01)
    data = np.zeros((10, 10), dtype=np.uint8)
    # Assign specific cells:
    data[0, 0] = 50  # Built-up
    data[1, 1] = 40  # Cropland
    data[2, 2] = 10  # Tree cover
    data[3, 3] = 80  # Water
    data[4, 4] = 30  # Grassland
    data[5, 5] = 20  # Shrubland
    data[6, 6] = 60  # Bare / sparse vegetation

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype=data.dtype,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data, 1)

    yield path
    if os.path.exists(path):
        os.remove(path)


# ==========================================
# 1. GeoJSON loading tests
# ==========================================
def test_geojson_loading(small_geojson_fixture):
    service = IndustrialContextService(feature_collection=small_geojson_fixture)
    assert service.facility_count == 3


def test_corrupted_features_handling():
    corrupted_data = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": None, "properties": {"name": "No Geom"}},
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": []}, "properties": {"name": "Empty Geom"}},
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [75.898, 30.875]}, "properties": {"name": "Valid Point"}}
        ]
    }
    service = IndustrialContextService(feature_collection=corrupted_data)
    assert service.facility_count == 1


# ==========================================
# 2. Nearest facility calculation tests
# ==========================================
def test_nearest_facility_calculation(small_geojson_fixture):
    service = IndustrialContextService(feature_collection=small_geojson_fixture)
    # Query very close to Substation Giaspura (75.898481, 30.875625)
    ctx = service.get_industrial_context(30.875630, 75.898481)
    assert ctx["nearest_facility_name"] == "Substation Giaspura"
    assert ctx["nearest_facility_type"] == "power_substation"
    assert ctx["distance_to_facility_m"] < 5.0
    assert "near industrial infrastructure" in ctx["proximity_context"].lower()


# ==========================================
# 3. Distance calculations tests (EPSG:32643)
# ==========================================
def test_metric_distance_calculation(small_geojson_fixture):
    service = IndustrialContextService(feature_collection=small_geojson_fixture)
    # Query point at Substation (75.898481, 30.875625)
    # Distance to East Fuel Depot (75.910000, 30.875625):
    # dx is ~0.011519 degrees lon at lat 30.875 ~ 1100 meters
    ctx = service.get_industrial_context(30.875625, 75.910000)
    assert ctx["nearest_facility_name"] == "East Fuel Depot"
    assert ctx["distance_to_facility_m"] == 0.0


# ==========================================
# 4. Industrial-zone membership tests
# ==========================================
def test_industrial_zone_membership(small_geojson_fixture):
    service = IndustrialContextService(feature_collection=small_geojson_fixture)
    # Inside the polygon [75.890, 30.870] to [75.895, 30.875]
    inside_lat, inside_lon = 30.872500, 75.892500
    ctx_inside = service.get_industrial_context(inside_lat, inside_lon)
    assert ctx_inside["inside_industrial_zone"] is True
    assert ctx_inside["distance_to_nearest_industrial_zone"] == 0.0
    assert "inside designated industrial zone" in ctx_inside["proximity_context"].lower()

    # Point outside the polygon
    outside_lat, outside_lon = 30.878000, 75.892500
    ctx_outside = service.get_industrial_context(outside_lat, outside_lon)
    assert ctx_outside["inside_industrial_zone"] is False
    assert ctx_outside["distance_to_nearest_industrial_zone"] > 0.0


# ==========================================
# 5. Empty facility handling tests
# ==========================================
def test_empty_facility_handling():
    empty_service = IndustrialContextService(feature_collection={"type": "FeatureCollection", "features": []})
    assert empty_service.facility_count == 0

    ctx = empty_service.get_industrial_context(30.875625, 75.898481)
    assert ctx["nearest_facility_name"] is None
    assert ctx["nearest_facility_type"] is None
    assert ctx["distance_to_facility_m"] is None
    assert ctx["inside_industrial_zone"] is False
    assert ctx["distance_to_nearest_industrial_zone"] is None
    assert ctx["industrial_density_5km"] == 0


# ==========================================
# 6. Land-cover lookup tests
# ==========================================
def test_landcover_lookup(temp_landcover_raster):
    lc_service = LandCoverService(raster_path=temp_landcover_raster)
    # Sample cell 0,0: origin is (75.80, 30.90), cell 0,0 center is (75.805, 30.895) -> 50: Built-up
    cls = lc_service.get_landcover_class(30.895, 75.805)
    assert cls == "Built-up"

    # Sample cell 1,1: (75.815, 30.885) -> 40: Cropland
    cls_crop = lc_service.get_landcover_class(30.885, 75.815)
    assert cls_crop == "Cropland"

    # Sample cell 3,3: (75.835, 30.865) -> 80: Water
    cls_water = lc_service.get_landcover_class(30.865, 75.835)
    assert cls_water == "Water"

    # Out of bounds coordinate
    cls_oob = lc_service.get_landcover_class(35.0, 70.0)
    assert "Out of Bounds" in cls_oob


# ==========================================
# 7. Coordinate validation tests
# ==========================================
def test_coordinate_validation():
    # Valid coordinates
    lat, lon = validate_coordinates(30.875625, 75.898481)
    assert lat == 30.875625
    assert lon == 75.898481

    # Invalid latitude > 90
    with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
        validate_coordinates(95.0, 75.89)

    # Inverted coordinates: passing lat=75.898481 and lon=30.875625
    with pytest.raises(ValueError, match="reversed for the study area|Possible latitude/longitude swap"):
        validate_coordinates(75.898481, 30.875625)

    # None coordinates
    with pytest.raises(ValueError, match="must not be None"):
        validate_coordinates(None, 75.89)

    # Non-numeric
    with pytest.raises(TypeError):
        validate_coordinates("invalid", 75.89)


# ==========================================
# 8. Event enrichment integration test
# ==========================================
def test_enrich_thermal_event(small_geojson_fixture, temp_landcover_raster):
    ind_service = IndustrialContextService(feature_collection=small_geojson_fixture)
    lc_service = LandCoverService(raster_path=temp_landcover_raster)

    raw_event = {
        "event_id": "EV-001",
        "latitude": 30.875625,
        "longitude": 75.898481,
        "frp": 15.2
    }

    enriched = enrich_thermal_event(raw_event, industrial_svc=ind_service, landcover_svc=lc_service)

    assert enriched["event_id"] == "EV-001"
    assert enriched["frp"] == 15.2
    assert enriched["nearest_facility_name"] == "Substation Giaspura"
    assert enriched["nearest_facility_type"] == "power_substation"
    assert isinstance(enriched["distance_to_facility_m"], float)
    assert isinstance(enriched["inside_industrial_zone"], bool)
    assert "landcover" in enriched
    assert enriched["industrial_density_5km"] >= 1


# ==========================================
# 9. Real Giaspura dataset integration test
# ==========================================
def test_real_giaspura_dataset():
    """Verify integration against the real Giaspura OSM and ESA WorldCover files."""
    from data_processing.geospatial import calculate_industrial_context, lookup_landcover, enrich_thermal_event

    giaspura_lat = 30.875625
    giaspura_lon = 75.898481

    ctx = calculate_industrial_context(giaspura_lat, giaspura_lon)
    assert ctx["nearest_facility_name"] is not None
    assert ctx["distance_to_facility_m"] is not None
    assert ctx["distance_to_facility_m"] >= 0.0
    assert ctx["industrial_density_5km"] > 0
    assert "industrial" in ctx["proximity_context"].lower()

    lc = lookup_landcover(giaspura_lat, giaspura_lon)
    assert lc == "Built-up"

    event = {"latitude": giaspura_lat, "longitude": giaspura_lon, "event_id": "REAL-GIASPURA-1"}
    enriched = enrich_thermal_event(event)
    assert enriched["event_id"] == "REAL-GIASPURA-1"
    assert enriched["nearest_facility_name"] is not None
    assert enriched["landcover"] == "Built-up"

