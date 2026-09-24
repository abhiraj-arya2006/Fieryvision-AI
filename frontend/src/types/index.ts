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
}

export interface ActiveEventsResponse {
  total: number;
  data_mode: 'active' | 'cached' | 'historical' | string;
  last_updated: string;
  giaspura_center: {
    latitude: number;
    longitude: number;
  };
  radius_km: number;
  events: CanonicalEvent[];
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
  in_giaspura_zone: boolean;
  distance_to_giaspura_center_m: number;
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
  priority: string;
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
}

export interface FacilitiesResponse {
  total: number;
  study_area: string;
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
