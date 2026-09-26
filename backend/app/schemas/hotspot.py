from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class HotspotDetectionPoint(BaseModel):
    latitude: float
    longitude: float
    frp: Optional[float] = None
    brightness: Optional[float] = None
    acq_date: Optional[str] = None
    acq_time: Optional[str] = None
    satellite: Optional[str] = None
    confidence: Optional[str] = None
    daynight: Optional[str] = None


class HotspotSnapshotSchema(BaseModel):
    timestamp: str
    event_count: int
    area_sq_km: float
    average_frp: float
    max_frp: float
    risk_score: float
    growth_rate: float
    status: str


class HotspotSummarySchema(BaseModel):
    id: str
    name: str
    status: str  # ACTIVE, CONTAINED, EXTINGUISHED, MONITORING
    classification: str  # ACTIVE HOTSPOT, PERSISTENT HOTSPOT, EMERGING HOTSPOT, etc.
    centroid_lat: float
    centroid_lon: float
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float
    area_sq_km: float
    event_count: int
    unique_acquisitions: int
    duration_hours: float
    first_seen: str
    last_seen: str
    average_frp: float
    max_frp: float
    frp_trend: str
    average_brightness: float
    max_brightness: float
    persistence_score: float
    recurrence_score: float
    growth_rate: float
    growth_status: str
    spatial_density: float
    hotspot_score: float
    risk_score: float
    risk_tier: str
    confidence: float
    anomaly_score: float
    country: str
    continent: str
    region: Optional[str] = None
    nearest_city: Optional[str] = None
    dominant_landcover: str
    nearby_facilities_count: int
    nearest_facility_name: Optional[str] = None
    nearest_facility_distance_m: Optional[float] = None
    reason_codes: List[str] = Field(default_factory=list)
    uncertainty_note: Optional[str] = None
    updated_at: str


class HotspotDetailSchema(HotspotSummarySchema):
    landcover_classes: List[str] = Field(default_factory=list)
    source_satellites: List[str] = Field(default_factory=list)
    daynight_distribution: Dict[str, int] = Field(default_factory=dict)
    sample_detections: List[HotspotDetectionPoint] = Field(default_factory=list)
    timeline_snapshots: List[HotspotSnapshotSchema] = Field(default_factory=list)
    model_version: str = "v10.5-global-engine"


class HotspotsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[HotspotSummarySchema]


class HotspotAnalyticsResponse(BaseModel):
    total_active_hotspots: int
    emerging_hotspots_count: int
    persistent_hotspots_count: int
    high_intensity_hotspots_count: int
    high_risk_hotspots_count: int
    large_area_hotspots_count: int
    industrial_hotspots_count: int
    wildfire_like_hotspots_count: int
    new_in_last_24h_count: int
    largest_hotspot: Optional[HotspotSummarySchema] = None
    fastest_growing_hotspot: Optional[HotspotSummarySchema] = None
    highest_frp_hotspot: Optional[HotspotSummarySchema] = None
    continent_breakdown: Dict[str, int] = Field(default_factory=dict)
    classification_breakdown: Dict[str, int] = Field(default_factory=dict)
    risk_tier_breakdown: Dict[str, int] = Field(default_factory=dict)


class HotspotAlertSchema(BaseModel):
    alert_id: str
    hotspot_id: str
    hotspot_name: str
    alert_type: str  # SURGING_FRP, RAPID_EXPANSION, CRITICAL_RISK, PERSISTENT_PROXIMITY
    severity: str  # CRITICAL, WARNING, ADVISORY
    message: str
    timestamp: str
    centroid_lat: float
    centroid_lon: float
    metrics: Dict[str, Any] = Field(default_factory=dict)


# =====================================================================
# PHASE 11: WIND, PLUME, EMERGENCY & INCIDENT RESPONSE SCHEMAS
# =====================================================================

class HourlyWindForecast(BaseModel):
    hour_offset: int
    time: str
    wind_speed_kmh: float
    wind_direction_deg: float
    downwind_bearing_deg: float
    cardinal: str


class WindDataSchema(BaseModel):
    latitude: float
    longitude: float
    wind_speed_kmh: float
    wind_direction_deg: float
    downwind_bearing_deg: float
    cardinal_direction: str
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    hourly_forecast: List[HourlyWindForecast] = Field(default_factory=list)
    timestamp: str
    source: str = "Open-Meteo"
    is_cached: bool = False
    attribution: str = "Weather data provided by Open-Meteo under CC BY 4.0 license"


class PlumeHorizonFeature(BaseModel):
    horizon_hours: int
    projected_distance_km: float
    bearing_deg: float
    cone_spread_angle_deg: float
    confidence_rating: str  # High, Moderate, Indicative Screening
    polygon_coordinates: List[List[float]]  # [[lat, lon], ...]
    centerline_coordinates: List[List[float]]  # [[lat, lon], ...]


class PlumeConeResponse(BaseModel):
    hotspot_id: str
    hotspot_name: str
    centroid_lat: float
    centroid_lon: float
    current_wind: WindDataSchema
    horizons: List[PlumeHorizonFeature]
    screening_disclaimer: str = (
        "INDICATIVE SCREENING ONLY: This wind-projected zone represents atmospheric transport "
        "potential based on weather-model wind vectors. It is not a certified fire spread perimeter "
        "or validated smoke concentration forecast."
    )
    generated_at: str


class EmergencyFacilitySchema(BaseModel):
    id: str
    name: str
    facility_type: str  # fire_station, hospital, burn_trauma_unit, fire_hydrant
    latitude: float
    longitude: float
    distance_m: float
    bearing_deg: float
    address: Optional[str] = "Address not listed"
    phone: Optional[str] = "Contact number unavailable"
    operator: Optional[str] = None
    specialty_verified: bool = False
    specialty_note: Optional[str] = None
    source: str = "OpenStreetMap / Municipal Geospatial Data"
    data_quality: str = "MAPPED_GEOSPATIAL"


class BufferIntersectionSummary(BaseModel):
    buffer_radius_m: float
    fire_stations_count: int = 0
    hospitals_count: int = 0
    burn_trauma_count: int = 0
    hydrants_count: int = 0
    industrial_facilities_count: int = 0
    critical_sites_names: List[str] = Field(default_factory=list)
    data_completeness_note: str = (
        "Counts reflect mapped open geospatial records. Absence of mapped hydrants or facilities "
        "does not confirm total absence on the ground."
    )


class EmergencyContextResponse(BaseModel):
    hotspot_id: str
    hotspot_name: str
    centroid_lat: float
    centroid_lon: float
    nearest_fire_station: Optional[EmergencyFacilitySchema] = None
    nearest_hospital: Optional[EmergencyFacilitySchema] = None
    nearest_burn_trauma: Optional[EmergencyFacilitySchema] = None
    nearest_hydrant: Optional[EmergencyFacilitySchema] = None
    buffer_1km: BufferIntersectionSummary
    buffer_3km: BufferIntersectionSummary
    nearby_facilities: List[EmergencyFacilitySchema] = Field(default_factory=list)
    source: str = "OpenStreetMap Overpass API"
    coverage_disclaimer: str = (
        "Emergency facility data is retrieved from OpenStreetMap contributors. "
        "Coverage varies by jurisdiction; verify directly with local emergency services."
    )
    generated_at: str


class IncidentIntelResponse(BaseModel):
    hotspot: HotspotDetailSchema
    wind: WindDataSchema
    plume: PlumeConeResponse
    emergency: EmergencyContextResponse
    ai_investigation_summary: str
    generated_at: str

