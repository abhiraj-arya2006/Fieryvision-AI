"""Central configuration and constants for FIRMS processing and Giaspura study area."""

# Reference center: Giaspura, Ludhiana, Punjab, India
GIASPURA_LAT = 30.875625
GIASPURA_LON = 75.898481

# Regional monitoring radius (default: 50 km)
DEFAULT_REGION_RADIUS_KM = 50.0

# Spatial-temporal event clustering parameters
SPATIAL_CLUSTER_RADIUS_M = 375.0
TEMPORAL_CLUSTER_WINDOW_HOURS = 24.0

# Coordinate reference systems
EPSG_WGS84 = "EPSG:4326"
EPSG_METRIC_UTM43N = "EPSG:32643"

# Persistence thresholds (unique detection days)
PERSISTENCE_TRANSIENT_DAYS = 1
PERSISTENCE_RECURRING_MIN_DAYS = 2
PERSISTENCE_RECURRING_MAX_DAYS = 4
PERSISTENCE_PERSISTENT_DAYS = 5

# Priority score thresholds
PRIORITY_CRITICAL_MIN = 85
PRIORITY_HIGH_MIN = 65
PRIORITY_MODERATE_MIN = 40
