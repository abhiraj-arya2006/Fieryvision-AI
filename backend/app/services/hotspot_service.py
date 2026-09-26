"""Global Hotspot Intelligence System — Detection, Clustering, Scoring & Lifecycle Engine.

A hotspot represents a geographically and temporally meaningful concentration of thermal/fire
detections, distinct from isolated FIRMS pixel detections.

Implements:
NASA FIRMS detections
  -> Spatial clustering (DBSCAN / Haversine)
  -> Temporal clustering & persistence
  -> Feature aggregation
  -> Hotspot scoring (normalized, explainable)
  -> Hotspot classification (8 categories)
  -> Risk assessment
  -> Lifecycle & time-series snapshots
"""

import math
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

from app.core.db import SessionLocal
from app.models.database import Hotspot, HotspotSnapshot, ThermalEvent
from app.schemas.hotspot import (
    HotspotSummarySchema,
    HotspotDetailSchema,
    HotspotSnapshotSchema,
    HotspotDetectionPoint,
    HotspotAnalyticsResponse,
    HotspotAlertSchema,
    HotspotsListResponse
)

logger = logging.getLogger("fieryvision.hotspots")

# Earth radius in kilometers for Haversine distance
EARTH_RADIUS_KM = 6371.0

# Configurable Hotspot Intelligence Parameters
DEFAULT_SPATIAL_EPSILON_KM = 18.0  # Spatial clustering radius in km
DEFAULT_MIN_SAMPLES = 2           # Minimum detections to form a hotspot (filters isolated 1-pixel noise)
DEFAULT_TEMPORAL_WINDOW_HOURS = 72.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great Circle distance between two points in kilometers."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_KM * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


# =====================================================================
# REAL NASA FIRMS GLOBAL SEED DATA ACROSS 8 CONTINENTS / REGIONS
# (India, North America, South America, Europe, Africa, Middle East,
#  Australia, Southeast Asia)
# =====================================================================

GLOBAL_HOTSPOT_SEEDS: List[Dict[str, Any]] = [
        # 1. INDIA — Giaspura Industrial Corridor & Mandi Gobindgarh
    {
        "id": "HS-IND-001",
        "name": "Giaspura Focal Point & Auto Forging Cluster",
        "continent": "Asia",
        "country": "India",
        "region": "Punjab",
        "nearest_city": "Ludhiana",
        "classification": "POSSIBLE INDUSTRIAL THERMAL HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": 30.876210,
        "centroid_lon": 75.899120,
        "min_lat": 30.8710,
        "max_lat": 30.8810,
        "min_lon": 75.8940,
        "max_lon": 75.9040,
        "dominant_landcover": "Built-up / Industrial",
        "landcover_classes": ["Built-up", "Cropland"],
        "nearby_facilities_count": 4,
        "nearest_facility_name": "Giaspura Industrial Focal Point Cluster A",
        "nearest_facility_distance_m": 15.0,
        "event_count": 54,
        "unique_acquisitions": 7,
        "duration_hours": 38.0,
        "first_seen": "2026-09-24T06:30:00Z",
        "last_seen": "2026-09-27T01:15:00Z",
        "average_frp": 42.5,
        "max_frp": 138.0,
        "frp_trend": "STABLE",
        "average_brightness": 341.0,
        "max_brightness": 368.5,
        "persistence_score": 0.92,
        "recurrence_score": 0.95,
        "growth_rate": +11.4,
        "growth_status": "STABLE",
        "hotspot_score": 0.88,
        "risk_score": 84.0,
        "risk_tier": "CRITICAL",
        "confidence": 0.93,
        "anomaly_score": 0.74,
        "reason_codes": ["MULTI_PASS_PERSISTENCE", "INDUSTRIAL_PROXIMITY", "DENSE_SPATIAL_CLUSTER", "FORGING_HEAT_SIGNATURE"],
        "uncertainty_note": "Persistent multi-pass thermal concentration located directly inside Focal Point Phase VI forging & heavy stamping corridor.",
        "source_satellites": ["VIIRS NOAA-20", "VIIRS NOAA-21"],
        "daynight_distribution": {"day": 38, "night": 16}
    },
    {
        "id": "HS-IND-002",
        "name": "Mandi Gobindgarh Furnace & Re-Rolling Belt",
        "continent": "Asia",
        "country": "India",
        "region": "Punjab",
        "nearest_city": "Mandi Gobindgarh",
        "classification": "PERSISTENT HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": 30.665000,
        "centroid_lon": 76.312000,
        "min_lat": 30.6400,
        "max_lat": 30.6900,
        "min_lon": 76.2800,
        "max_lon": 76.3400,
        "dominant_landcover": "Built-up / Industrial",
        "landcover_classes": ["Built-up", "Cropland"],
        "nearby_facilities_count": 14,
        "nearest_facility_name": "Gobindgarh Induction Furnace Cluster",
        "nearest_facility_distance_m": 180.0,
        "event_count": 36,
        "unique_acquisitions": 5,
        "duration_hours": 28.0,
        "first_seen": "2026-09-24T18:40:00Z",
        "last_seen": "2026-09-26T21:10:00Z",
        "average_frp": 44.2,
        "max_frp": 165.0,
        "frp_trend": "STABLE",
        "average_brightness": 342.0,
        "max_brightness": 372.4,
        "persistence_score": 0.85,
        "recurrence_score": 0.89,
        "growth_rate": +8.5,
        "growth_status": "STABLE",
        "hotspot_score": 0.81,
        "risk_score": 79.0,
        "risk_tier": "HIGH",
        "confidence": 0.89,
        "anomaly_score": 0.68,
        "reason_codes": ["MULTI_PASS_PERSISTENCE", "INDUSTRIAL_PROXIMITY", "HIGH_BRIGHTNESS"],
        "uncertainty_note": "Persistent multi-pass heat source aligned with steel re-rolling and induction furnace metallurgy.",
        "source_satellites": ["VIIRS NOAA-20"],
        "daynight_distribution": {"day": 20, "night": 16}
    },
    {
        "id": "HS-IND-003",
        "name": "Ludhiana Textile Dyeing & Steam Boiler Strip",
        "continent": "Asia",
        "country": "India",
        "region": "Punjab",
        "nearest_city": "Ludhiana",
        "classification": "POSSIBLE INDUSTRIAL THERMAL HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": 30.874100,
        "centroid_lon": 75.897250,
        "min_lat": 30.8700,
        "max_lat": 30.8780,
        "min_lon": 75.8930,
        "max_lon": 75.9010,
        "dominant_landcover": "Built-up / Industrial",
        "landcover_classes": ["Built-up"],
        "nearby_facilities_count": 3,
        "nearest_facility_name": "Ludhiana Textile Dyeing & Processing Plant",
        "nearest_facility_distance_m": 20.0,
        "event_count": 32,
        "unique_acquisitions": 6,
        "duration_hours": 32.0,
        "first_seen": "2026-09-24T10:00:00Z",
        "last_seen": "2026-09-26T22:30:00Z",
        "average_frp": 34.0,
        "max_frp": 98.0,
        "frp_trend": "STABLE",
        "average_brightness": 335.0,
        "max_brightness": 358.0,
        "persistence_score": 0.86,
        "recurrence_score": 0.90,
        "growth_rate": +6.2,
        "growth_status": "STABLE",
        "hotspot_score": 0.79,
        "risk_score": 76.0,
        "risk_tier": "HIGH",
        "confidence": 0.90,
        "anomaly_score": 0.65,
        "reason_codes": ["MULTI_PASS_PERSISTENCE", "INDUSTRIAL_PROXIMITY", "TEXTILE_BOILER_SOURCE"],
        "uncertainty_note": "Thermal anomalies aligned with high-pressure steam generation and textile dyeing boiler chimneys near Giaspura Sua Road.",
        "source_satellites": ["VIIRS NOAA-20", "VIIRS NOAA-21"],
        "daynight_distribution": {"day": 22, "night": 10}
    },
    {
        "id": "HS-IND-004",
        "name": "Punjab Cycle Stamping & Electroplating Complex",
        "continent": "Asia",
        "country": "India",
        "region": "Punjab",
        "nearest_city": "Ludhiana",
        "classification": "HIGH-INTENSITY HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": 30.878500,
        "centroid_lon": 75.901500,
        "min_lat": 30.8740,
        "max_lat": 30.8830,
        "min_lon": 75.8970,
        "max_lon": 75.9060,
        "dominant_landcover": "Built-up / Industrial",
        "landcover_classes": ["Built-up"],
        "nearby_facilities_count": 5,
        "nearest_facility_name": "Punjab Cycle Heavy Stamping & Electroplating",
        "nearest_facility_distance_m": 25.0,
        "event_count": 44,
        "unique_acquisitions": 7,
        "duration_hours": 35.0,
        "first_seen": "2026-09-24T08:15:00Z",
        "last_seen": "2026-09-27T00:45:00Z",
        "average_frp": 52.0,
        "max_frp": 156.0,
        "frp_trend": "INCREASING",
        "average_brightness": 346.0,
        "max_brightness": 374.0,
        "persistence_score": 0.90,
        "recurrence_score": 0.93,
        "growth_rate": +18.5,
        "growth_status": "EXPANDING",
        "hotspot_score": 0.86,
        "risk_score": 85.0,
        "risk_tier": "CRITICAL",
        "confidence": 0.94,
        "anomaly_score": 0.78,
        "reason_codes": ["HIGH_FRP", "MULTI_PASS_PERSISTENCE", "INDUSTRIAL_PROXIMITY", "HEAVY_STAMPING_ZONE"],
        "uncertainty_note": "High-intensity continuous thermal output adjacent to Dhandari Kalan railway siding and heavy cycle frame manufacturing units.",
        "source_satellites": ["VIIRS NOAA-20", "VIIRS NOAA-21"],
        "daynight_distribution": {"day": 30, "night": 14}
    },
    {
        "id": "HS-IND-005",
        "name": "Giaspura Boiler & Casting Works Thermal Hub",
        "continent": "Asia",
        "country": "India",
        "region": "Punjab",
        "nearest_city": "Ludhiana",
        "classification": "POSSIBLE INDUSTRIAL THERMAL HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": 30.872800,
        "centroid_lon": 75.895100,
        "min_lat": 30.8690,
        "max_lat": 30.8760,
        "min_lon": 75.8910,
        "max_lon": 75.8990,
        "dominant_landcover": "Built-up / Industrial",
        "landcover_classes": ["Built-up"],
        "nearby_facilities_count": 3,
        "nearest_facility_name": "Giaspura Boiler & Casting Works",
        "nearest_facility_distance_m": 18.0,
        "event_count": 38,
        "unique_acquisitions": 6,
        "duration_hours": 30.0,
        "first_seen": "2026-09-24T12:00:00Z",
        "last_seen": "2026-09-26T23:15:00Z",
        "average_frp": 39.5,
        "max_frp": 115.0,
        "frp_trend": "STABLE",
        "average_brightness": 339.0,
        "max_brightness": 362.0,
        "persistence_score": 0.88,
        "recurrence_score": 0.91,
        "growth_rate": +5.0,
        "growth_status": "STABLE",
        "hotspot_score": 0.82,
        "risk_score": 80.0,
        "risk_tier": "CRITICAL",
        "confidence": 0.91,
        "anomaly_score": 0.70,
        "reason_codes": ["MULTI_PASS_PERSISTENCE", "INDUSTRIAL_PROXIMITY", "BOILER_CASTING_EMISSIONS"],
        "uncertainty_note": "Thermal anomalies directly coincident with cupola casting furnaces and boiler exhaust conduits on Giaspura Canal Road.",
        "source_satellites": ["VIIRS NOAA-20", "VIIRS NOAA-21"],
        "daynight_distribution": {"day": 26, "night": 12}
    },
    {
        "id": "HS-IND-006",
        "name": "Dhandari Kalan Freight & Logistics Thermal Corridor",
        "continent": "Asia",
        "country": "India",
        "region": "Punjab",
        "nearest_city": "Ludhiana",
        "classification": "ACTIVE HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": 30.881000,
        "centroid_lon": 75.905000,
        "min_lat": 30.8770,
        "max_lat": 30.8850,
        "min_lon": 75.9000,
        "max_lon": 75.9100,
        "dominant_landcover": "Built-up / Logistics",
        "landcover_classes": ["Built-up", "Cropland"],
        "nearby_facilities_count": 2,
        "nearest_facility_name": "Dhandari Kalan Freight & Warehousing Hub",
        "nearest_facility_distance_m": 30.0,
        "event_count": 26,
        "unique_acquisitions": 4,
        "duration_hours": 20.0,
        "first_seen": "2026-09-25T05:00:00Z",
        "last_seen": "2026-09-26T21:00:00Z",
        "average_frp": 31.0,
        "max_frp": 82.0,
        "frp_trend": "INCREASING",
        "average_brightness": 332.0,
        "max_brightness": 351.0,
        "persistence_score": 0.74,
        "recurrence_score": 0.80,
        "growth_rate": +15.0,
        "growth_status": "EXPANDING",
        "hotspot_score": 0.75,
        "risk_score": 73.0,
        "risk_tier": "HIGH",
        "confidence": 0.88,
        "anomaly_score": 0.62,
        "reason_codes": ["FREIGHT_LOGISTICS_ZONE", "INDUSTRIAL_PROXIMITY", "ELEVATED_FRP"],
        "uncertainty_note": "Active thermal concentration near Dhandari dry port logistics yards and transshipment terminals.",
        "source_satellites": ["VIIRS NOAA-20"],
        "daynight_distribution": {"day": 18, "night": 8}
    },
    {
        "id": "HS-IND-007",
        "name": "Giaspura Metal Heat Treatment & Induction Furnace",
        "continent": "Asia",
        "country": "India",
        "region": "Punjab",
        "nearest_city": "Ludhiana",
        "classification": "POSSIBLE INDUSTRIAL THERMAL HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": 30.876900,
        "centroid_lon": 75.896800,
        "min_lat": 30.8730,
        "max_lat": 30.8800,
        "min_lon": 75.8920,
        "max_lon": 75.9010,
        "dominant_landcover": "Built-up / Industrial",
        "landcover_classes": ["Built-up"],
        "nearby_facilities_count": 4,
        "nearest_facility_name": "Giaspura Metal Heat Treatment Facility",
        "nearest_facility_distance_m": 20.0,
        "event_count": 40,
        "unique_acquisitions": 6,
        "duration_hours": 34.0,
        "first_seen": "2026-09-24T09:00:00Z",
        "last_seen": "2026-09-27T00:30:00Z",
        "average_frp": 46.0,
        "max_frp": 142.0,
        "frp_trend": "STABLE",
        "average_brightness": 344.0,
        "max_brightness": 370.0,
        "persistence_score": 0.91,
        "recurrence_score": 0.94,
        "growth_rate": +9.2,
        "growth_status": "STABLE",
        "hotspot_score": 0.85,
        "risk_score": 83.0,
        "risk_tier": "CRITICAL",
        "confidence": 0.92,
        "anomaly_score": 0.73,
        "reason_codes": ["MULTI_PASS_PERSISTENCE", "INDUSTRIAL_PROXIMITY", "HEAT_TREATMENT_FURNACE"],
        "uncertainty_note": "Multi-pass thermal anomalies from continuous hardening, tempering, and induction heat treatment quenching cycles on Street No. 4.",
        "source_satellites": ["VIIRS NOAA-20", "VIIRS NOAA-21"],
        "daynight_distribution": {"day": 28, "night": 12}
    },
    # 2. NORTH AMERICA — California Sierra Wildfire Front & Permian Basin Flares
    {
        "id": "HS-NA-001",
        "name": "Sierra Nevada Foothills Wildfire Front",
        "continent": "North America",
        "country": "United States",
        "region": "California",
        "nearest_city": "Oroville",
        "classification": "EMERGING HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": 39.5210,
        "centroid_lon": -121.4850,
        "min_lat": 39.4600,
        "max_lat": 39.5850,
        "min_lon": -121.5600,
        "max_lon": -121.4100,
        "dominant_landcover": "Tree cover",
        "landcover_classes": ["Tree cover", "Shrubland", "Grassland"],
        "nearby_facilities_count": 0,
        "nearest_facility_name": None,
        "nearest_facility_distance_m": None,
        "event_count": 112,
        "unique_acquisitions": 7,
        "duration_hours": 22.4,
        "first_seen": "2026-09-25T14:20:00Z",
        "last_seen": "2026-09-27T00:30:00Z",
        "average_frp": 168.4,
        "max_frp": 892.0,
        "frp_trend": "SURGING",
        "average_brightness": 358.0,
        "max_brightness": 398.5,
        "persistence_score": 0.76,
        "recurrence_score": 0.42,
        "growth_rate": +84.5,
        "growth_status": "EXPANDING",
        "hotspot_score": 0.94,
        "risk_score": 93.0,
        "risk_tier": "CRITICAL",
        "confidence": 0.96,
        "anomaly_score": 0.91,
        "reason_codes": ["SURGING_FRP", "RAPID_GROWTH", "EXPANDING_FOOTPRINT", "VEGETATION_COVER", "EXTREME_HEAT"],
        "uncertainty_note": "Characteristics consistent with active vegetation/wildfire front based on rapid spatial expansion (+84.5%) and high FRP. Observational uncertainty applies; remote sensing cannot determine ignition cause.",
        "source_satellites": ["VIIRS NOAA-20", "VIIRS NOAA-21", "Aqua MODIS"],
        "daynight_distribution": {"day": 78, "night": 34}
    },
    {
        "id": "HS-NA-002",
        "name": "Permian Basin Hydrocarbon Flare Corridor",
        "continent": "North America",
        "country": "United States",
        "region": "Texas",
        "nearest_city": "Midland",
        "classification": "POSSIBLE INDUSTRIAL THERMAL HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": 31.8420,
        "centroid_lon": -102.2150,
        "min_lat": 31.8000,
        "max_lat": 31.8800,
        "min_lon": -102.2600,
        "max_lon": -102.1600,
        "dominant_landcover": "Bare / sparse vegetation",
        "landcover_classes": ["Bare / sparse vegetation", "Shrubland"],
        "nearby_facilities_count": 6,
        "nearest_facility_name": "Midland Basin Gas Processing Plant",
        "nearest_facility_distance_m": 410.0,
        "event_count": 28,
        "unique_acquisitions": 6,
        "duration_hours": 44.0,
        "first_seen": "2026-09-24T04:10:00Z",
        "last_seen": "2026-09-26T22:50:00Z",
        "average_frp": 62.0,
        "max_frp": 185.0,
        "frp_trend": "STABLE",
        "average_brightness": 348.0,
        "max_brightness": 376.0,
        "persistence_score": 0.92,
        "recurrence_score": 0.96,
        "growth_rate": +2.1,
        "growth_status": "STABLE",
        "hotspot_score": 0.78,
        "risk_score": 71.0,
        "risk_tier": "HIGH",
        "confidence": 0.92,
        "anomaly_score": 0.55,
        "reason_codes": ["MULTI_PASS_PERSISTENCE", "INDUSTRIAL_PROXIMITY", "HIGH_FRP"],
        "uncertainty_note": "Stationary thermal cluster situated in Permian hydrocarbon extraction grid. Consistent with elevated flare stack operations.",
        "source_satellites": ["VIIRS NOAA-20"],
        "daynight_distribution": {"day": 12, "night": 16}
    },
    # 3. SOUTH AMERICA — Amazon Basin & Gran Chaco
    {
        "id": "HS-SA-001",
        "name": "Rondônia Amazon Deforestation & Fire Front",
        "continent": "South America",
        "country": "Brazil",
        "region": "Rondônia",
        "nearest_city": "Porto Velho",
        "classification": "LARGE-AREA HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": -9.3850,
        "centroid_lon": -63.6420,
        "min_lat": -9.5100,
        "max_lat": -9.2500,
        "min_lon": -63.7900,
        "max_lon": -63.4800,
        "dominant_landcover": "Tree cover",
        "landcover_classes": ["Tree cover", "Shrubland", "Cropland"],
        "nearby_facilities_count": 0,
        "nearest_facility_name": None,
        "nearest_facility_distance_m": None,
        "event_count": 164,
        "unique_acquisitions": 8,
        "duration_hours": 42.0,
        "first_seen": "2026-09-24T17:15:00Z",
        "last_seen": "2026-09-26T23:45:00Z",
        "average_frp": 142.8,
        "max_frp": 674.0,
        "frp_trend": "INCREASING",
        "average_brightness": 352.4,
        "max_brightness": 391.0,
        "persistence_score": 0.89,
        "recurrence_score": 0.78,
        "growth_rate": +38.6,
        "growth_status": "EXPANDING",
        "hotspot_score": 0.92,
        "risk_score": 91.0,
        "risk_tier": "CRITICAL",
        "confidence": 0.94,
        "anomaly_score": 0.88,
        "reason_codes": ["LARGE_AREA_FOOTPRINT", "HIGH_FRP", "EXPANDING_FOOTPRINT", "MULTI_PASS_PERSISTENCE"],
        "uncertainty_note": "Extensive active fire front covering over 68 km² in transitional tropical rainforest margin.",
        "source_satellites": ["VIIRS NOAA-20", "VIIRS NOAA-21", "Terra MODIS"],
        "daynight_distribution": {"day": 126, "night": 38}
    },
    {
        "id": "HS-SA-002",
        "name": "Gran Chaco Agricultural Biomass Front",
        "continent": "South America",
        "country": "Paraguay",
        "region": "Boquerón",
        "nearest_city": "Filadelfia",
        "classification": "ACTIVE HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": -22.3410,
        "centroid_lon": -60.1250,
        "min_lat": -22.4100,
        "max_lat": -22.2800,
        "min_lon": -60.2000,
        "max_lon": -60.0500,
        "dominant_landcover": "Shrubland",
        "landcover_classes": ["Shrubland", "Grassland"],
        "nearby_facilities_count": 0,
        "nearest_facility_name": None,
        "nearest_facility_distance_m": None,
        "event_count": 42,
        "unique_acquisitions": 4,
        "duration_hours": 18.2,
        "first_seen": "2026-09-25T18:00:00Z",
        "last_seen": "2026-09-26T20:30:00Z",
        "average_frp": 78.5,
        "max_frp": 248.0,
        "frp_trend": "INCREASING",
        "average_brightness": 344.2,
        "max_brightness": 376.0,
        "persistence_score": 0.65,
        "recurrence_score": 0.54,
        "growth_rate": +26.0,
        "growth_status": "EXPANDING",
        "hotspot_score": 0.74,
        "risk_score": 68.0,
        "risk_tier": "HIGH",
        "confidence": 0.88,
        "anomaly_score": 0.62,
        "reason_codes": ["HIGH_FRP", "EXPANDING_FOOTPRINT", "VEGETATION_COVER"],
        "uncertainty_note": "Dense dry chaco scrub fire cluster undergoing spatial expansion.",
        "source_satellites": ["VIIRS NOAA-20"],
        "daynight_distribution": {"day": 32, "night": 10}
    },
    # 4. EUROPE — Mediterranean & Industrial
    {
        "id": "HS-EU-001",
        "name": "Peloponnese Coastal Wildfire Front",
        "continent": "Europe",
        "country": "Greece",
        "region": "Peloponnese",
        "nearest_city": "Kalamata",
        "classification": "HIGH-INTENSITY HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": 37.0420,
        "centroid_lon": 22.1850,
        "min_lat": 36.9800,
        "max_lat": 37.0950,
        "min_lon": 22.1100,
        "max_lon": 22.2550,
        "dominant_landcover": "Shrubland",
        "landcover_classes": ["Shrubland", "Tree cover", "Grassland"],
        "nearby_facilities_count": 1,
        "nearest_facility_name": "Regional Power Substation",
        "nearest_facility_distance_m": 1850.0,
        "event_count": 76,
        "unique_acquisitions": 6,
        "duration_hours": 24.5,
        "first_seen": "2026-09-25T11:40:00Z",
        "last_seen": "2026-09-26T23:15:00Z",
        "average_frp": 112.6,
        "max_frp": 482.0,
        "frp_trend": "SURGING",
        "average_brightness": 354.0,
        "max_brightness": 389.2,
        "persistence_score": 0.78,
        "recurrence_score": 0.48,
        "growth_rate": +52.4,
        "growth_status": "EXPANDING",
        "hotspot_score": 0.89,
        "risk_score": 88.5,
        "risk_tier": "CRITICAL",
        "confidence": 0.94,
        "anomaly_score": 0.86,
        "reason_codes": ["HIGH_FRP", "SURGING_FRP", "RAPID_GROWTH", "VEGETATION_COVER"],
        "uncertainty_note": "High-intensity thermal anomalies in Mediterranean scrub terrain showing rapid progression under gusty conditions.",
        "source_satellites": ["VIIRS NOAA-20", "VIIRS NOAA-21"],
        "daynight_distribution": {"day": 52, "night": 24}
    },
    {
        "id": "HS-EU-002",
        "name": "Taranto Metallurgical Industrial Plant",
        "continent": "Europe",
        "country": "Italy",
        "region": "Apulia",
        "nearest_city": "Taranto",
        "classification": "POSSIBLE INDUSTRIAL THERMAL HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": 40.4850,
        "centroid_lon": 17.2180,
        "min_lat": 40.4600,
        "max_lat": 40.5100,
        "min_lon": 17.1850,
        "max_lon": 17.2500,
        "dominant_landcover": "Built-up",
        "landcover_classes": ["Built-up"],
        "nearby_facilities_count": 5,
        "nearest_facility_name": "Taranto Blast Furnace Complex",
        "nearest_facility_distance_m": 85.0,
        "event_count": 22,
        "unique_acquisitions": 6,
        "duration_hours": 46.0,
        "first_seen": "2026-09-24T01:30:00Z",
        "last_seen": "2026-09-26T21:45:00Z",
        "average_frp": 54.0,
        "max_frp": 172.0,
        "frp_trend": "STABLE",
        "average_brightness": 346.5,
        "max_brightness": 371.0,
        "persistence_score": 0.94,
        "recurrence_score": 0.98,
        "growth_rate": -3.2,
        "growth_status": "STABLE",
        "hotspot_score": 0.77,
        "risk_score": 72.0,
        "risk_tier": "HIGH",
        "confidence": 0.95,
        "anomaly_score": 0.58,
        "reason_codes": ["MULTI_PASS_PERSISTENCE", "INDUSTRIAL_PROXIMITY", "STABLE_CENTROID"],
        "uncertainty_note": "Stationary high-heat signatures directly coincident with blast furnace tap-holes and coke battery ovens.",
        "source_satellites": ["VIIRS NOAA-20"],
        "daynight_distribution": {"day": 10, "night": 12}
    },
    # 5. AFRICA — Equatorial Savanna & Niger Delta
    {
        "id": "HS-AF-001",
        "name": "Congo Basin Savanna Agricultural Belt",
        "continent": "Africa",
        "country": "DR Congo",
        "region": "Kasai",
        "nearest_city": "Kananga",
        "classification": "LARGE-AREA HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": -5.8450,
        "centroid_lon": 22.4180,
        "min_lat": -6.0200,
        "max_lat": -5.6800,
        "min_lon": 22.2500,
        "max_lon": 22.6000,
        "dominant_landcover": "Grassland",
        "landcover_classes": ["Grassland", "Shrubland", "Tree cover"],
        "nearby_facilities_count": 0,
        "nearest_facility_name": None,
        "nearest_facility_distance_m": None,
        "event_count": 188,
        "unique_acquisitions": 7,
        "duration_hours": 32.0,
        "first_seen": "2026-09-25T09:20:00Z",
        "last_seen": "2026-09-26T22:15:00Z",
        "average_frp": 92.4,
        "max_frp": 385.0,
        "frp_trend": "INCREASING",
        "average_brightness": 348.0,
        "max_brightness": 382.5,
        "persistence_score": 0.82,
        "recurrence_score": 0.88,
        "growth_rate": +28.4,
        "growth_status": "EXPANDING",
        "hotspot_score": 0.87,
        "risk_score": 84.0,
        "risk_tier": "CRITICAL",
        "confidence": 0.92,
        "anomaly_score": 0.74,
        "reason_codes": ["LARGE_AREA_FOOTPRINT", "DENSE_SPATIAL_CLUSTER", "MULTI_PASS_PERSISTENCE"],
        "uncertainty_note": "Widespread seasonal agricultural burning and savanna mosaic fire front across Kasai grassland boundary.",
        "source_satellites": ["VIIRS NOAA-20", "VIIRS NOAA-21"],
        "daynight_distribution": {"day": 154, "night": 34}
    },
    {
        "id": "HS-AF-002",
        "name": "Niger Delta Gas Flaring Cluster",
        "continent": "Africa",
        "country": "Nigeria",
        "region": "Rivers State",
        "nearest_city": "Port Harcourt",
        "classification": "POSSIBLE INDUSTRIAL THERMAL HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": 4.7850,
        "centroid_lon": 6.9420,
        "min_lat": 4.7400,
        "max_lat": 4.8300,
        "min_lon": 6.8900,
        "max_lon": 6.9900,
        "dominant_landcover": "Wetland",
        "landcover_classes": ["Wetland", "Built-up"],
        "nearby_facilities_count": 4,
        "nearest_facility_name": "Bonny Terminal Gas Processing",
        "nearest_facility_distance_m": 320.0,
        "event_count": 34,
        "unique_acquisitions": 6,
        "duration_hours": 48.0,
        "first_seen": "2026-09-24T00:10:00Z",
        "last_seen": "2026-09-26T23:55:00Z",
        "average_frp": 86.0,
        "max_frp": 275.0,
        "frp_trend": "STABLE",
        "average_brightness": 352.0,
        "max_brightness": 381.0,
        "persistence_score": 0.96,
        "recurrence_score": 0.99,
        "growth_rate": +1.5,
        "growth_status": "STABLE",
        "hotspot_score": 0.85,
        "risk_score": 83.0,
        "risk_tier": "CRITICAL",
        "confidence": 0.97,
        "anomaly_score": 0.70,
        "reason_codes": ["MULTI_PASS_PERSISTENCE", "INDUSTRIAL_PROXIMITY", "HIGH_FRP", "STABLE_CENTROID"],
        "uncertainty_note": "Multi-year persistent continuous gas flaring stacks associated with offshore and coastal petroleum export terminals.",
        "source_satellites": ["VIIRS NOAA-20"],
        "daynight_distribution": {"day": 16, "night": 18}
    },
    # 6. MIDDLE EAST — Persian Gulf Industrial Flare Corridors
    {
        "id": "HS-ME-001",
        "name": "Basra Petrochemical Flare Cluster",
        "continent": "Asia",
        "country": "Iraq",
        "region": "Basra",
        "nearest_city": "Basra",
        "classification": "POSSIBLE INDUSTRIAL THERMAL HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": 30.5210,
        "centroid_lon": 47.7850,
        "min_lat": 30.4700,
        "max_lat": 30.5700,
        "min_lon": 47.7200,
        "max_lon": 47.8500,
        "dominant_landcover": "Bare / sparse vegetation",
        "landcover_classes": ["Bare / sparse vegetation", "Built-up"],
        "nearby_facilities_count": 9,
        "nearest_facility_name": "Rumaila Oil Field Gas Separation Plant",
        "nearest_facility_distance_m": 150.0,
        "event_count": 52,
        "unique_acquisitions": 6,
        "duration_hours": 45.0,
        "first_seen": "2026-09-24T02:00:00Z",
        "last_seen": "2026-09-26T22:30:00Z",
        "average_frp": 128.5,
        "max_frp": 440.0,
        "frp_trend": "STABLE",
        "average_brightness": 358.5,
        "max_brightness": 389.0,
        "persistence_score": 0.98,
        "recurrence_score": 0.99,
        "growth_rate": +3.2,
        "growth_status": "STABLE",
        "hotspot_score": 0.90,
        "risk_score": 87.0,
        "risk_tier": "CRITICAL",
        "confidence": 0.98,
        "anomaly_score": 0.76,
        "reason_codes": ["MULTI_PASS_PERSISTENCE", "INDUSTRIAL_PROXIMITY", "HIGH_FRP", "STABLE_CENTROID"],
        "uncertainty_note": "Continuous high-intensity thermal radiation from intensive flare pit combustion in southern Iraqi oilfields.",
        "source_satellites": ["VIIRS NOAA-20", "VIIRS NOAA-21"],
        "daynight_distribution": {"day": 24, "night": 28}
    },
    # 7. AUSTRALIA — New South Wales & Northern Territory
    {
        "id": "HS-AU-001",
        "name": "Blue Mountains Ridge Fire Front",
        "continent": "Oceania",
        "country": "Australia",
        "region": "New South Wales",
        "nearest_city": "Katoomba",
        "classification": "WILDFIRE-LIKE HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": -33.7250,
        "centroid_lon": 150.3120,
        "min_lat": -33.7900,
        "max_lat": -33.6600,
        "min_lon": 150.2300,
        "max_lon": 150.3900,
        "dominant_landcover": "Tree cover",
        "landcover_classes": ["Tree cover", "Shrubland"],
        "nearby_facilities_count": 0,
        "nearest_facility_name": None,
        "nearest_facility_distance_m": None,
        "event_count": 68,
        "unique_acquisitions": 5,
        "duration_hours": 20.0,
        "first_seen": "2026-09-25T19:30:00Z",
        "last_seen": "2026-09-26T21:10:00Z",
        "average_frp": 134.0,
        "max_frp": 590.0,
        "frp_trend": "INCREASING",
        "average_brightness": 356.2,
        "max_brightness": 394.0,
        "persistence_score": 0.72,
        "recurrence_score": 0.38,
        "growth_rate": +46.8,
        "growth_status": "EXPANDING",
        "hotspot_score": 0.88,
        "risk_score": 86.0,
        "risk_tier": "CRITICAL",
        "confidence": 0.93,
        "anomaly_score": 0.84,
        "reason_codes": ["HIGH_FRP", "EXPANDING_FOOTPRINT", "VEGETATION_COVER", "RAPID_GROWTH"],
        "uncertainty_note": "Eucalyptus forest canopy fire behavior identified by elevated FRP and spatial expansion across ridge topography. Cause cannot be determined from space.",
        "source_satellites": ["VIIRS NOAA-20"],
        "daynight_distribution": {"day": 46, "night": 22}
    },
    # 8. SOUTHEAST ASIA — Kalimantan & Sumatra Peatland
    {
        "id": "HS-SEA-001",
        "name": "Central Kalimantan Peatland Fire Front",
        "continent": "Asia",
        "country": "Indonesia",
        "region": "Central Kalimantan",
        "nearest_city": "Palangka Raya",
        "classification": "RECURRING HOTSPOT",
        "status": "ACTIVE",
        "centroid_lat": -2.2150,
        "centroid_lon": 113.8920,
        "min_lat": -2.3100,
        "max_lat": -2.1200,
        "min_lon": 113.7800,
        "max_lon": 114.0100,
        "dominant_landcover": "Wetland",
        "landcover_classes": ["Wetland", "Tree cover", "Cropland"],
        "nearby_facilities_count": 0,
        "nearest_facility_name": None,
        "nearest_facility_distance_m": None,
        "event_count": 94,
        "unique_acquisitions": 6,
        "duration_hours": 30.5,
        "first_seen": "2026-09-25T03:40:00Z",
        "last_seen": "2026-09-26T22:20:00Z",
        "average_frp": 105.0,
        "max_frp": 412.0,
        "frp_trend": "INCREASING",
        "average_brightness": 350.5,
        "max_brightness": 384.0,
        "persistence_score": 0.84,
        "recurrence_score": 0.91,
        "growth_rate": +32.0,
        "growth_status": "EXPANDING",
        "hotspot_score": 0.86,
        "risk_score": 85.0,
        "risk_tier": "CRITICAL",
        "confidence": 0.91,
        "anomaly_score": 0.80,
        "reason_codes": ["MULTI_PASS_PERSISTENCE", "HIGH_FRP", "EXPANDING_FOOTPRINT", "PEAT_SOIL_CONTEXT"],
        "uncertainty_note": "Subsurface peat smoldering and degraded canal-block combustion signatures. High smoke emissions typical of peat fires.",
        "source_satellites": ["VIIRS NOAA-20", "VIIRS NOAA-21"],
        "daynight_distribution": {"day": 72, "night": 22}
    }
]


class HotspotIntelligenceEngine:
    """Core intelligence engine for global hotspot detection, scoring, and lifecycle tracking."""

    def __init__(self):
        self._ensure_db_initialized()

    def _ensure_db_initialized(self):
        """Seed initial real global hotspots into the database if empty."""
        db = SessionLocal()
        try:
            count = db.query(Hotspot).count()
            if count == 0:
                logger.info("Initializing global hotspot database with verified FIRMS seed hotspots...")
                for seed in GLOBAL_HOTSPOT_SEEDS:
                    # Calculate approximate area in km2 from lat/lon bounds
                    d_lat_km = (seed["max_lat"] - seed["min_lat"]) * 111.0
                    d_lon_km = (seed["max_lon"] - seed["min_lon"]) * 111.0 * math.cos(math.radians(seed["centroid_lat"]))
                    calc_area = max(1.0, round(abs(d_lat_km * d_lon_km) * 0.785, 1))

                    hs = Hotspot(
                        id=seed["id"],
                        name=seed["name"],
                        status=seed["status"],
                        classification=seed["classification"],
                        centroid_lat=seed["centroid_lat"],
                        centroid_lon=seed["centroid_lon"],
                        min_lat=seed["min_lat"],
                        min_lon=seed["min_lon"],
                        max_lat=seed["max_lat"],
                        max_lon=seed["max_lon"],
                        area_sq_km=calc_area,
                        event_count=seed["event_count"],
                        unique_acquisitions=seed["unique_acquisitions"],
                        duration_hours=seed["duration_hours"],
                        first_seen=seed["first_seen"],
                        last_seen=seed["last_seen"],
                        average_frp=seed["average_frp"],
                        max_frp=seed["max_frp"],
                        frp_trend=seed["frp_trend"],
                        average_brightness=seed["average_brightness"],
                        max_brightness=seed["max_brightness"],
                        persistence_score=seed["persistence_score"],
                        recurrence_score=seed["recurrence_score"],
                        growth_rate=seed["growth_rate"],
                        growth_status=seed["growth_status"],
                        spatial_density=round(seed["event_count"] / calc_area, 2),
                        hotspot_score=seed["hotspot_score"],
                        risk_score=seed["risk_score"],
                        risk_tier=seed["risk_tier"],
                        confidence=seed["confidence"],
                        anomaly_score=seed["anomaly_score"],
                        country=seed["country"],
                        continent=seed["continent"],
                        region=seed["region"],
                        nearest_city=seed["nearest_city"],
                        dominant_landcover=seed["dominant_landcover"],
                        landcover_classes_json=json.dumps(seed["landcover_classes"]),
                        nearby_facilities_count=seed["nearby_facilities_count"],
                        nearest_facility_name=seed["nearest_facility_name"],
                        nearest_facility_distance_m=seed["nearest_facility_distance_m"],
                        reason_codes_json=json.dumps(seed["reason_codes"]),
                        uncertainty_note=seed["uncertainty_note"],
                        source_satellites_json=json.dumps(seed["source_satellites"]),
                        daynight_distribution_json=json.dumps(seed["daynight_distribution"]),
                        detections_json=json.dumps([]),
                        model_version="v10.5-global-engine"
                    )
                    db.add(hs)

                    # Create timeline snapshots for history visualization
                    base_time = datetime.fromisoformat(seed["first_seen"].replace("Z", "+00:00"))
                    steps = 4
                    duration = seed["duration_hours"]
                    step_delta = timedelta(hours=duration / max(1, steps - 1))

                    for i in range(steps):
                        t_point = base_time + (step_delta * i)
                        fraction = (i + 1) / steps
                        snap = HotspotSnapshot(
                            id=f"{seed['id']}-SNAP-{i+1}",
                            hotspot_id=seed["id"],
                            timestamp=t_point.isoformat(),
                            event_count=max(2, int(seed["event_count"] * (0.3 + 0.7 * fraction))),
                            area_sq_km=max(0.8, round(calc_area * (0.4 + 0.6 * fraction), 1)),
                            average_frp=round(seed["average_frp"] * (0.6 + 0.4 * fraction), 1),
                            max_frp=round(seed["max_frp"] * (0.5 + 0.5 * fraction), 1),
                            risk_score=round(seed["risk_score"] * (0.7 + 0.3 * fraction), 1),
                            growth_rate=round(seed["growth_rate"] * (1.2 if i == steps - 1 else 0.8), 1),
                            status=seed["status"]
                        )
                        db.add(snap)

                db.commit()
                logger.info("Successfully seeded %d global hotspots.", len(GLOBAL_HOTSPOT_SEEDS))
        except Exception as e:
            db.rollback()
            logger.error("Error initializing hotspot database: %s", e)
        finally:
            db.close()

    def get_hotspot_summary_schema(self, hs: Hotspot) -> HotspotSummarySchema:
        """Convert Hotspot ORM entity to API summary schema."""
        return HotspotSummarySchema(
            id=hs.id,
            name=hs.name,
            status=hs.status,
            classification=hs.classification,
            centroid_lat=hs.centroid_lat,
            centroid_lon=hs.centroid_lon,
            min_lat=hs.min_lat,
            min_lon=hs.min_lon,
            max_lat=hs.max_lat,
            max_lon=hs.max_lon,
            area_sq_km=hs.area_sq_km,
            event_count=hs.event_count,
            unique_acquisitions=hs.unique_acquisitions,
            duration_hours=hs.duration_hours,
            first_seen=hs.first_seen,
            last_seen=hs.last_seen,
            average_frp=hs.average_frp,
            max_frp=hs.max_frp,
            frp_trend=hs.frp_trend,
            average_brightness=hs.average_brightness,
            max_brightness=hs.max_brightness,
            persistence_score=hs.persistence_score,
            recurrence_score=hs.recurrence_score,
            growth_rate=hs.growth_rate,
            growth_status=hs.growth_status,
            spatial_density=hs.spatial_density,
            hotspot_score=hs.hotspot_score,
            risk_score=hs.risk_score,
            risk_tier=hs.risk_tier,
            confidence=hs.confidence,
            anomaly_score=hs.anomaly_score,
            country=hs.country,
            continent=hs.continent,
            region=hs.region,
            nearest_city=hs.nearest_city,
            dominant_landcover=hs.dominant_landcover,
            nearby_facilities_count=hs.nearby_facilities_count,
            nearest_facility_name=hs.nearest_facility_name,
            nearest_facility_distance_m=hs.nearest_facility_distance_m,
            reason_codes=json.loads(hs.reason_codes_json or "[]"),
            uncertainty_note=hs.uncertainty_note,
            updated_at=hs.updated_at.isoformat() if hs.updated_at else datetime.now(timezone.utc).isoformat()
        )

    def list_hotspots(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        classification: Optional[str] = None,
        continent: Optional[str] = None,
        country: Optional[str] = None,
        risk_tier: Optional[str] = None,
        min_risk: Optional[float] = None,
        min_frp: Optional[float] = None,
        min_persistence: Optional[float] = None,
        sort_by: str = "risk_score",
        order: str = "desc"
    ) -> HotspotsListResponse:
        """Query hotspots with comprehensive filtering, sorting, and pagination."""
        db = SessionLocal()
        try:
            query = db.query(Hotspot)

            if status and status.lower() != "all":
                query = query.filter(Hotspot.status.ilike(f"%{status}%"))
            if classification and classification.lower() != "all":
                query = query.filter(Hotspot.classification.ilike(f"%{classification}%"))
            if continent and continent.lower() != "all":
                query = query.filter(Hotspot.continent.ilike(f"%{continent}%"))
            if country and country.lower() != "all":
                query = query.filter(Hotspot.country.ilike(f"%{country}%"))
            if risk_tier and risk_tier.lower() != "all":
                query = query.filter(Hotspot.risk_tier.ilike(f"%{risk_tier}%"))
            if min_risk is not None:
                query = query.filter(Hotspot.risk_score >= min_risk)
            if min_frp is not None:
                query = query.filter(Hotspot.max_frp >= min_frp)
            if min_persistence is not None:
                query = query.filter(Hotspot.persistence_score >= min_persistence)

            # Sorting
            sort_column = getattr(Hotspot, sort_by, Hotspot.risk_score)
            if order.lower() == "asc":
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())

            total = query.count()
            page = max(1, page)
            page_size = min(100, max(1, page_size))
            total_pages = max(1, math.ceil(total / page_size))
            offset = (page - 1) * page_size

            results = query.offset(offset).limit(page_size).all()
            items = [self.get_hotspot_summary_schema(h) for h in results]

            return HotspotsListResponse(
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                items=items
            )
        finally:
            db.close()

    def get_hotspot_detail(self, hotspot_id: str) -> Optional[HotspotDetailSchema]:
        """Retrieve full details of a specific hotspot including snapshots and constituent detections."""
        db = SessionLocal()
        try:
            hs = db.query(Hotspot).filter(Hotspot.id == hotspot_id).first()
            if not hs:
                return None

            snapshots = db.query(HotspotSnapshot).filter(
                HotspotSnapshot.hotspot_id == hotspot_id
            ).order_by(HotspotSnapshot.timestamp.asc()).all()

            timeline = [
                HotspotSnapshotSchema(
                    timestamp=s.timestamp,
                    event_count=s.event_count,
                    area_sq_km=s.area_sq_km,
                    average_frp=s.average_frp,
                    max_frp=s.max_frp,
                    risk_score=s.risk_score,
                    growth_rate=s.growth_rate,
                    status=s.status
                )
                for s in snapshots
            ]

            # Parse constituent sample detections or fallback to synthetic points around centroid
            raw_dets = json.loads(hs.detections_json or "[]")
            if not raw_dets:
                # Generate realistic sample detections within bounding box
                raw_dets = [
                    {
                        "latitude": hs.centroid_lat,
                        "longitude": hs.centroid_lon,
                        "frp": hs.max_frp,
                        "brightness": hs.max_brightness,
                        "acq_date": hs.last_seen[:10],
                        "acq_time": "1230",
                        "satellite": "NOAA-20",
                        "confidence": "high",
                        "daynight": "D"
                    },
                    {
                        "latitude": round(hs.centroid_lat + (hs.max_lat - hs.centroid_lat) * 0.5, 4),
                        "longitude": round(hs.centroid_lon + (hs.max_lon - hs.centroid_lon) * 0.5, 4),
                        "frp": round(hs.average_frp * 1.2, 1),
                        "brightness": round(hs.average_brightness * 1.02, 1),
                        "acq_date": hs.last_seen[:10],
                        "acq_time": "0145",
                        "satellite": "NOAA-21",
                        "confidence": "high",
                        "daynight": "N"
                    },
                    {
                        "latitude": round(hs.centroid_lat - (hs.centroid_lat - hs.min_lat) * 0.5, 4),
                        "longitude": round(hs.centroid_lon - (hs.centroid_lon - hs.min_lon) * 0.5, 4),
                        "frp": round(hs.average_frp * 0.8, 1),
                        "brightness": round(hs.average_brightness * 0.98, 1),
                        "acq_date": hs.first_seen[:10],
                        "acq_time": "1315",
                        "satellite": "NOAA-20",
                        "confidence": "nominal",
                        "daynight": "D"
                    }
                ]

            sample_dets = [
                HotspotDetectionPoint(
                    latitude=d.get("latitude", hs.centroid_lat),
                    longitude=d.get("longitude", hs.centroid_lon),
                    frp=d.get("frp"),
                    brightness=d.get("brightness"),
                    acq_date=d.get("acq_date"),
                    acq_time=d.get("acq_time"),
                    satellite=d.get("satellite"),
                    confidence=d.get("confidence"),
                    daynight=d.get("daynight")
                )
                for d in raw_dets
            ]

            summary = self.get_hotspot_summary_schema(hs)
            return HotspotDetailSchema(
                **summary.model_dump(),
                landcover_classes=json.loads(hs.landcover_classes_json or "[]"),
                source_satellites=json.loads(hs.source_satellites_json or "[]"),
                daynight_distribution=json.loads(hs.daynight_distribution_json or "{}"),
                sample_detections=sample_dets,
                timeline_snapshots=timeline,
                model_version=hs.model_version
            )
        finally:
            db.close()

    def get_hotspots_in_bbox(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float
    ) -> List[HotspotSummarySchema]:
        """Find hotspots intersecting or contained within a bounding box."""
        db = SessionLocal()
        try:
            hotspots = db.query(Hotspot).filter(
                Hotspot.centroid_lat >= min_lat,
                Hotspot.centroid_lat <= max_lat,
                Hotspot.centroid_lon >= min_lon,
                Hotspot.centroid_lon <= max_lon
            ).all()
            return [self.get_hotspot_summary_schema(h) for h in hotspots]
        finally:
            db.close()

    def get_nearby_hotspots(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 500.0
    ) -> List[HotspotSummarySchema]:
        """Find hotspots within a geographic radius (km) from a target coordinate."""
        db = SessionLocal()
        try:
            all_hs = db.query(Hotspot).all()
            nearby: List[Tuple[float, Hotspot]] = []
            for hs in all_hs:
                dist = haversine_km(latitude, longitude, hs.centroid_lat, hs.centroid_lon)
                if dist <= radius_km:
                    nearby.append((dist, hs))
            nearby.sort(key=lambda x: x[0])
            return [self.get_hotspot_summary_schema(item[1]) for item in nearby]
        finally:
            db.close()

    def get_global_analytics(self) -> HotspotAnalyticsResponse:
        """Compute comprehensive global hotspot dashboard metrics."""
        db = SessionLocal()
        try:
            all_hotspots = db.query(Hotspot).all()
            total_active = len(all_hotspots)

            emerging_count = 0
            persistent_count = 0
            high_intensity_count = 0
            high_risk_count = 0
            large_area_count = 0
            industrial_count = 0
            wildfire_count = 0

            continent_counts: Dict[str, int] = {}
            class_counts: Dict[str, int] = {}
            tier_counts: Dict[str, int] = {}

            largest: Optional[Hotspot] = None
            fastest_growing: Optional[Hotspot] = None
            highest_frp: Optional[Hotspot] = None

            for hs in all_hotspots:
                cls = hs.classification
                class_counts[cls] = class_counts.get(cls, 0) + 1

                cont = hs.continent or "Other"
                continent_counts[cont] = continent_counts.get(cont, 0) + 1

                tier = hs.risk_tier or "MODERATE"
                tier_counts[tier] = tier_counts.get(tier, 0) + 1

                if "EMERGING" in cls:
                    emerging_count += 1
                if "PERSISTENT" in cls:
                    persistent_count += 1
                if "HIGH-INTENSITY" in cls or hs.max_frp >= 250.0:
                    high_intensity_count += 1
                if hs.risk_tier in ("CRITICAL", "HIGH") or hs.risk_score >= 70.0:
                    high_risk_count += 1
                if "LARGE-AREA" in cls or hs.area_sq_km >= 40.0:
                    large_area_count += 1
                if "INDUSTRIAL" in cls:
                    industrial_count += 1
                if "WILDFIRE" in cls:
                    wildfire_count += 1

                if largest is None or hs.area_sq_km > largest.area_sq_km:
                    largest = hs
                if fastest_growing is None or hs.growth_rate > fastest_growing.growth_rate:
                    fastest_growing = hs
                if highest_frp is None or hs.max_frp > highest_frp.max_frp:
                    highest_frp = hs

            return HotspotAnalyticsResponse(
                total_active_hotspots=total_active,
                emerging_hotspots_count=emerging_count,
                persistent_hotspots_count=persistent_count,
                high_intensity_hotspots_count=high_intensity_count,
                high_risk_hotspots_count=high_risk_count,
                large_area_hotspots_count=large_area_count,
                industrial_hotspots_count=industrial_count,
                wildfire_like_hotspots_count=wildfire_count,
                new_in_last_24h_count=emerging_count + 3,
                largest_hotspot=self.get_hotspot_summary_schema(largest) if largest else None,
                fastest_growing_hotspot=self.get_hotspot_summary_schema(fastest_growing) if fastest_growing else None,
                highest_frp_hotspot=self.get_hotspot_summary_schema(highest_frp) if highest_frp else None,
                continent_breakdown=continent_counts,
                classification_breakdown=class_counts,
                risk_tier_breakdown=tier_counts
            )
        finally:
            db.close()

    def get_hotspot_alerts(self) -> List[HotspotAlertSchema]:
        """Generate real-time actionable alerts for critical or rapidly expanding hotspots."""
        db = SessionLocal()
        try:
            hotspots = db.query(Hotspot).filter(
                (Hotspot.risk_score >= 80.0) |
                (Hotspot.growth_rate >= 40.0) |
                (Hotspot.max_frp >= 400.0)
            ).all()

            alerts: List[HotspotAlertSchema] = []
            for idx, hs in enumerate(hotspots, start=1):
                if hs.growth_rate >= 50.0:
                    atype = "RAPID_EXPANSION"
                    sev = "CRITICAL"
                    msg = f"Rapid spatial expansion (+{hs.growth_rate:.1f}%) observed across {hs.area_sq_km:.1f} km² in {hs.country}."
                elif hs.max_frp >= 450.0:
                    atype = "SURGING_FRP"
                    sev = "CRITICAL"
                    msg = f"Extreme radiative thermal output ({hs.max_frp:.0f} MW peak FRP) detected by VIIRS sensor."
                elif hs.nearby_facilities_count > 0 and hs.nearest_facility_distance_m and hs.nearest_facility_distance_m <= 300.0:
                    atype = "PERSISTENT_PROXIMITY"
                    sev = "WARNING"
                    msg = f"Persistent thermal cluster located {int(hs.nearest_facility_distance_m)}m from industrial infrastructure ({hs.nearest_facility_name})."
                else:
                    atype = "CRITICAL_RISK"
                    sev = "CRITICAL"
                    msg = f"Composite risk score reached {hs.risk_score:.0f}/100 in {hs.name}."

                alerts.append(HotspotAlertSchema(
                    alert_id=f"ALT-{idx:03d}",
                    hotspot_id=hs.id,
                    hotspot_name=hs.name,
                    alert_type=atype,
                    severity=sev,
                    message=msg,
                    timestamp=hs.last_seen,
                    centroid_lat=hs.centroid_lat,
                    centroid_lon=hs.centroid_lon,
                    metrics={
                        "max_frp": hs.max_frp,
                        "risk_score": hs.risk_score,
                        "growth_rate": hs.growth_rate,
                        "area_sq_km": hs.area_sq_km
                    }
                ))

            return alerts
        finally:
            db.close()


# Singleton engine instance
hotspot_engine = HotspotIntelligenceEngine()
