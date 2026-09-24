"""
Central Configuration for FieryVision AI — FIRMS & Temporal Intelligence.
All geospatial centers, regional thresholds, and clustering parameters are defined here.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class GeoConfig:
    """Geographic configuration for Giaspura, Ludhiana operational and monitoring areas."""
    # Giaspura reference coordinates (WGS84)
    GIASPURA_LATITUDE: float = 30.875625
    GIASPURA_LONGITUDE: float = 75.898481
    
    # Regional monitoring radius in kilometers
    DEFAULT_MONITORING_RADIUS_KM: float = 50.0
    
    # Local contextual radius in kilometers (for nearby facilities/infrastructure)
    LOCAL_CONTEXT_RADIUS_KM: float = 5.0
    
    # Primary Projected CRS for Punjab/Ludhiana UTM Zone 43N
    PROJECTED_CRS: str = "EPSG:32643"
    
    # Earth radius in kilometers (WGS84 mean)
    EARTH_RADIUS_KM: float = 6371.0088


@dataclass(frozen=True)
class FIRMSConfig:
    """NASA FIRMS API and product configuration."""
    ENV_MAP_KEY_NAME: str = "FIRMS_MAP_KEY"
    BASE_API_URL: str = "https://firms.modaps.eosdis.nasa.gov/api"
    OPEN_NRT_CSV_BASE: str = "https://firms.modaps.eosdis.nasa.gov/data/active_fire"
    
    # Standard VIIRS NRT Products
    DEFAULT_PRODUCTS: Tuple[str, ...] = (
        "VIIRS_NOAA20_NRT",
        "VIIRS_NOAA21_NRT",
        "VIIRS_SNPP_NRT",
    )
    
    # Default buffer days for active query
    DEFAULT_ACTIVE_DAYS: int = 2
    
    # Request timeout in seconds
    REQUEST_TIMEOUT_SECONDS: float = 15.0


@dataclass(frozen=True)
class ClusteringConfig:
    """Spatio-temporal clustering parameters for FIRMS hotspot detections."""
    # Spatial distance threshold in meters (~375m VIIRS I-band nominal pixel resolution)
    SPATIAL_EPS_METERS: float = 375.0
    
    # Temporal clustering window in hours (to merge morning/evening passes into one event)
    TEMPORAL_WINDOW_HOURS: float = 24.0
    
    # Minimum samples for core cluster point
    MIN_SAMPLES: int = 1


@dataclass(frozen=True)
class PersistenceConfig:
    """Temporal persistence classification thresholds over a 30-day window."""
    ANALYSIS_WINDOW_DAYS: int = 30
    SHORT_WINDOW_DAYS: int = 7
    
    # Unique detection days thresholds
    TRANSIENT_MAX_DAYS: int = 1
    RECURRING_MIN_DAYS: int = 2
    RECURRING_MAX_DAYS: int = 4
    PERSISTENT_MIN_DAYS: int = 5


GEO_CONFIG = GeoConfig()
FIRMS_CONFIG = FIRMSConfig()
CLUSTERING_CONFIG = ClusteringConfig()
PERSISTENCE_CONFIG = PersistenceConfig()
