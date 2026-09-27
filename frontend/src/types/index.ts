/**
 * FieryVision AI - TypeScript Definitions
 * Directly mapped to backend FastAPI schemas in app/schemas/event.py
 */

export interface CanonicalEvent {
  event_id: string;
  latitude: number;
  longitude: number;
  acq_date: string;
  acq_time: string;
  frp?: number | null;
  brightness?: number | null;
  confidence?: string | null;
  satellite?: string | null;
  daynight?: string | null;

  nearest_facility_name?: string | null;
  nearest_facility_type?: string | null;
  distance_to_facility_m?: number | null;
  inside_industrial_zone: boolean;

  landcover?: string | null;

  detections_7d: number;
  detections_30d: number;
  unique_detection_days: number;
  average_frp?: number | null;
  maximum_frp?: number | null;
  first_seen?: string | null;
  last_seen?: string | null;
  persistence: string;

  classification: string;
  classification_method: string;
  classification_confidence?: number | null;

  risk_score: number;
  priority: string;
  anomaly_score?: number | null;
  is_anomaly: boolean;
  anomaly_flag: boolean;

  evidence: string[];
  explanation?: string | null;
  source: string;
  ml_status?: 'evaluated' | 'not_evaluated' | 'unavailable' | string;
}

export interface RawFirmsDetection {
  event_id: string;
  latitude: number;
  longitude: number;
  acq_date: string;
  acq_time: string;
  frp?: number | null;
  brightness?: number | null;
  confidence?: string | null;
  satellite?: string | null;
  daynight?: string | null;
  source: string;
}

export interface RawDetectionsResponse {
  total_available: number;
  data_mode: string;
  freshness: string;
  last_successful_fetch?: string | null;
  returned_count: number;
  detections: RawFirmsDetection[];
}

export interface ActiveEventsResponse {
  total: number;
  data_mode: 'live' | 'cached' | 'unavailable' | string;
  freshness: 'live' | 'cached' | 'unavailable' | string;
  last_successful_fetch?: string | null;
  last_updated: string;
  live_event_count: number;
  cached_event_count: number;
  events: CanonicalEvent[];
}

export interface FirmsStatusResponse {
  api_reachable: boolean;
  api_success: boolean;
  live_event_count: number;
  cached_event_count: number;
  data_mode: string;
  freshness: string;
  source: string;
  coverage: string;
  last_successful_fetch?: string | null;
  message?: string | null;
}

export interface HealthResponse {
  status: string;
  service: string;
  firms_available: boolean;
  classification_mode: string;
  data_mode: string;
}

export interface LocationAnalysisRequest {
  latitude: number;
  longitude: number;
}

export interface LocationAnalysisResponse {
  latitude: number;
  longitude: number;
  thermal_activity_detected: boolean;
  assessment_mode: 'evidence_based' | 'supervised_ml' | 'no_activity' | 'insufficient_evidence' | string;
  active_anomalies_count: number;
  nearest_facility_name?: string | null;
  nearest_facility_type?: string | null;
  distance_to_facility_m?: number | null;
  inside_industrial_zone: boolean;
  landcover?: string | null;
  temporal_summary: {
    detections_7d?: number;
    detections_30d?: number;
    unique_detection_days?: number;
    average_frp?: number | null;
    maximum_frp?: number | null;
    first_seen?: string | null;
    last_seen?: string | null;
    persistence?: string;
    [key: string]: any;
  };
  classification: string;
  classification_method: string;
  classification_confidence?: number | null;
  risk_score: number;
  event_risk_score?: number | null;
  localized_risk_score?: number;
  risk_difference?: number | null;
  matched_hotspot_id?: string | null;
  matched_hotspot_name?: string | null;
  matched_hotspot_distance_km?: number | null;
  nearest_fire_station?: EmergencyFacility | null;
  nearest_hospital?: EmergencyFacility | null;
  nearest_burn_trauma?: EmergencyFacility | null;
  emergency_facilities?: EmergencyFacility[];
  emergency_search_radius_km?: number | null;
  priority: string;
  ml_status: 'evaluated' | 'not_evaluated' | 'unavailable' | string;
  anomaly_score?: number | null;
  is_anomaly: boolean;
  anomaly_flag: boolean;
  evidence: string[];
  explanation?: string | null;
}

export interface Facility {
  id: string;
  name: string;
  site_type: string;
  latitude: number;
  longitude: number;
  address?: string | null;
  operating_status: string;
  country?: string;
  continent?: string;
  classification?: string;
  risk_tier?: string;
  hotspot_id?: string;
}

export interface FacilitiesResponse {
  total: number;
  study_area?: string;
  facilities: Facility[];
}

export interface StatisticsResponse {
  total_events: number;
  industrial_events: number;
  persistent_events: number;
  natural_events: number;
  agricultural_events: number;
  critical_priority_events: number;
  high_priority_events: number;
  moderate_priority_events: number;
  low_priority_events: number;
  classified_events: number;
  unclassified_events: number;
  classification_mode: string;
}

export interface SatelliteContextResponse {
  event_id: string;
  status: 'available' | 'unavailable' | string;
  satellite?: string | null;
  sensor?: string | null;
  acquisition_date?: string | null;
  acquisition_time?: string | null;
  resolution_m?: number | null;
  bands_available: string[];
  provider?: string | null;
  message: string;
}

export interface ChatRequest {
  question: string;
  context?: Record<string, any> | null;
}

export interface ChatResponse {
  response: string;
  llm_available: boolean;
}

export interface EventFilterState {
  classification: string;
  priority: string;
  persistence: string;
  confidence: string;
  anomaly: string;
  search: string;
}

// =====================================================================
// PHASE 10.5: GLOBAL HOTSPOT INTELLIGENCE TYPES
// =====================================================================

export interface HotspotDetectionPoint {
  latitude: number;
  longitude: number;
  frp?: number | null;
  brightness?: number | null;
  acq_date?: string | null;
  acq_time?: string | null;
  satellite?: string | null;
  confidence?: string | null;
  daynight?: string | null;
}

export interface HotspotSnapshot {
  timestamp: string;
  event_count: number;
  area_sq_km: number;
  average_frp: number;
  max_frp: number;
  risk_score: number;
  growth_rate: number;
  status: string;
}

export interface HotspotSummary {
  id: string;
  name: string;
  status: 'ACTIVE' | 'CONTAINED' | 'EXTINGUISHED' | 'MONITORING' | string;
  classification: string; // ACTIVE HOTSPOT, PERSISTENT HOTSPOT, EMERGING HOTSPOT, etc.
  centroid_lat: number;
  centroid_lon: number;
  min_lat: number;
  min_lon: number;
  max_lat: number;
  max_lon: number;
  area_sq_km: number;
  event_count: number;
  unique_acquisitions: number;
  duration_hours: number;
  first_seen: string;
  last_seen: string;
  average_frp: number;
  max_frp: number;
  frp_trend: 'INCREASING' | 'DECREASING' | 'STABLE' | 'SURGING' | string;
  average_brightness: number;
  max_brightness: number;
  persistence_score: number;
  recurrence_score: number;
  growth_rate: number;
  growth_status: 'EXPANDING' | 'CONTRACTING' | 'STABLE' | 'MOVING' | 'NEWLY_FORMED' | string;
  spatial_density: number;
  hotspot_score: number;
  risk_score: number;
  risk_tier: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW' | string;
  confidence: number;
  anomaly_score: number;
  country: string;
  continent: string;
  region?: string | null;
  nearest_city?: string | null;
  dominant_landcover: string;
  nearby_facilities_count: number;
  nearest_facility_name?: string | null;
  nearest_facility_distance_m?: number | null;
  reason_codes: string[];
  uncertainty_note?: string | null;
  updated_at: string;
}

export interface HotspotDetail extends HotspotSummary {
  landcover_classes: string[];
  source_satellites: string[];
  daynight_distribution: Record<string, number>;
  sample_detections: HotspotDetectionPoint[];
  timeline_snapshots: HotspotSnapshot[];
  model_version: string;
}

export interface HotspotsListResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: HotspotSummary[];
}

export interface HotspotAnalytics {
  total_active_hotspots: number;
  raw_detections_count?: number;
  ai_anomalies_count?: number;
  emerging_hotspots_count: number;
  persistent_hotspots_count: number;
  high_intensity_hotspots_count: number;
  high_risk_hotspots_count: number;
  large_area_hotspots_count: number;
  industrial_hotspots_count: number;
  wildfire_like_hotspots_count: number;
  new_in_last_24h_count: number;
  largest_hotspot?: HotspotSummary | null;
  fastest_growing_hotspot?: HotspotSummary | null;
  highest_frp_hotspot?: HotspotSummary | null;
  continent_breakdown: Record<string, number>;
  classification_breakdown: Record<string, number>;
  risk_tier_breakdown: Record<string, number>;
}

export interface HotspotAlert {
  alert_id: string;
  hotspot_id: string;
  hotspot_name: string;
  alert_type: string;
  severity: 'CRITICAL' | 'WARNING' | 'ADVISORY' | string;
  message: string;
  timestamp: string;
  centroid_lat: number;
  centroid_lon: number;
  metrics: Record<string, any>;
}

export interface HotspotFilterState {
  continent: string;
  country: string;
  classification: string;
  riskTier: string;
  status: string;
  minRisk: number;
  sortBy: string;
  order: 'asc' | 'desc';
  search: string;
}

// =====================================================================
// PHASE 11: WIND, PLUME, EMERGENCY & INCIDENT RESPONSE TYPES
// =====================================================================

export interface HourlyWindForecast {
  hour_offset: number;
  time: string;
  wind_speed_kmh: number;
  wind_direction_deg: number;
  downwind_bearing_deg: number;
  cardinal: string;
}

export interface WindData {
  latitude: number;
  longitude: number;
  wind_speed_kmh: number;
  wind_direction_deg: number;
  downwind_bearing_deg: number;
  cardinal_direction: string;
  temperature_c?: number | null;
  humidity_percent?: number | null;
  hourly_forecast: HourlyWindForecast[];
  timestamp: string;
  source: string;
  is_cached: boolean;
  attribution: string;
}

export interface PlumeHorizonFeature {
  horizon_hours: number;
  projected_distance_km: number;
  bearing_deg: number;
  cone_spread_angle_deg: number;
  confidence_rating: string;
  polygon_coordinates: [number, number][];
  centerline_coordinates: [number, number][];
}

export interface PlumeConeResponse {
  hotspot_id: string;
  hotspot_name: string;
  centroid_lat: number;
  centroid_lon: number;
  current_wind: WindData;
  horizons: PlumeHorizonFeature[];
  screening_disclaimer: string;
  generated_at: string;
}

export interface EmergencyFacility {
  id: string;
  name: string;
  facility_type: 'fire_station' | 'hospital' | 'burn_trauma_unit' | 'fire_hydrant' | string;
  latitude: number;
  longitude: number;
  distance_m: number;
  bearing_deg: number;
  cardinal_direction?: string | null;
  address?: string | null;
  phone?: string | null;
  operator?: string | null;
  specialty_verified: boolean;
  specialty_note?: string | null;
  source: string;
  data_quality: string;
}

export interface BufferIntersectionSummary {
  buffer_radius_m: number;
  fire_stations_count: number;
  hospitals_count: number;
  burn_trauma_count: number;
  hydrants_count: number;
  industrial_facilities_count: number;
  critical_sites_names: string[];
  data_completeness_note: string;
}

export interface EmergencyContextResponse {
  hotspot_id: string;
  hotspot_name: string;
  centroid_lat: number;
  centroid_lon: number;
  nearest_fire_station?: EmergencyFacility | null;
  nearest_hospital?: EmergencyFacility | null;
  nearest_burn_trauma?: EmergencyFacility | null;
  nearest_hydrant?: EmergencyFacility | null;
  buffer_1km: BufferIntersectionSummary;
  buffer_3km: BufferIntersectionSummary;
  nearby_facilities: EmergencyFacility[];
  source: string;
  coverage_disclaimer: string;
  generated_at: string;
}

export interface IncidentIntelResponse {
  hotspot: HotspotDetail;
  wind: WindData;
  plume: PlumeConeResponse;
  emergency: EmergencyContextResponse;
  ai_investigation_summary: string;
  generated_at: string;
}


