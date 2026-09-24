from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class CanonicalEventSchema(BaseModel):
    event_id: str
    latitude: float
    longitude: float
    acq_date: str
    acq_time: str
    frp: Optional[float] = None
    brightness: Optional[float] = None
    confidence: Optional[str] = None
    satellite: Optional[str] = None
    daynight: Optional[str] = None

    nearest_facility_name: Optional[str] = None
    nearest_facility_type: Optional[str] = None
    distance_to_facility_m: Optional[float] = None
    inside_industrial_zone: bool = False

    landcover: Optional[str] = None

    detections_7d: int = 0
    detections_30d: int = 0
    unique_detection_days: int = 0
    average_frp: Optional[float] = None
    maximum_frp: Optional[float] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    persistence: str = "transient"

    classification: str = "unclassified"
    classification_method: str = "evidence_based"  # supervised_ml, evidence_based, cached, active, unclassified
    classification_confidence: Optional[float] = None

    risk_score: float = 0.0
    priority: str = "low"
    anomaly_score: Optional[float] = 0.0
    is_anomaly: bool = False
    anomaly_flag: bool = False

    evidence: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None

class ActiveEventsResponse(BaseModel):
    total: int
    data_mode: str  # active, cached, historical
    last_updated: str
    giaspura_center: Dict[str, float]
    radius_km: float
    events: List[CanonicalEventSchema]

class HealthResponse(BaseModel):
    status: str
    service: str
    firms_available: bool
    classification_mode: str
    data_mode: str

class LocationAnalysisRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude degree")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude degree")

class LocationAnalysisResponse(BaseModel):
    latitude: float
    longitude: float
    in_giaspura_zone: bool
    distance_to_giaspura_center_m: float
    thermal_activity_detected: bool
    assessment_mode: str  # evidence_based, supervised_ml, no_activity, insufficient_evidence
    active_anomalies_count: int
    nearest_facility_name: Optional[str] = None
    nearest_facility_type: Optional[str] = None
    distance_to_facility_m: Optional[float] = None
    inside_industrial_zone: bool = False
    landcover: Optional[str] = None
    temporal_summary: Dict[str, Any] = Field(default_factory=dict)
    classification: str = "unclassified"
    classification_method: str = "evidence_based"
    classification_confidence: Optional[float] = None
    risk_score: float = 0.0
    priority: str = "low"
    anomaly_score: Optional[float] = 0.0
    is_anomaly: bool = False
    anomaly_flag: bool = False
    evidence: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None

class FacilitySchema(BaseModel):
    id: str
    name: str
    site_type: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    operating_status: str = "active"

class FacilitiesResponse(BaseModel):
    total: int
    study_area: str = "Giaspura, Ludhiana, Punjab"
    facilities: List[FacilitySchema]

class StatisticsResponse(BaseModel):
    total_events: int
    industrial_events: int
    persistent_events: int
    natural_events: int
    agricultural_events: int
    critical_priority_events: int = 0
    high_priority_events: int = 0
    moderate_priority_events: int = 0
    low_priority_events: int = 0
    classified_events: int
    unclassified_events: int
    classification_mode: str

class SatelliteContextResponse(BaseModel):
    event_id: str
    status: str  # available, unavailable
    satellite: Optional[str] = None
    sensor: Optional[str] = None
    acquisition_date: Optional[str] = None
    acquisition_time: Optional[str] = None
    resolution_m: Optional[float] = None
    bands_available: List[str] = Field(default_factory=list)
    provider: Optional[str] = None
    message: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question for FieryVision AI")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Investigation context from a previous analyse-location call"
    )


class ChatResponse(BaseModel):
    response: str
    llm_available: bool

