/**
 * Centralized API Service for FieryVision AI
 * Connects directly to FastAPI backend on localhost:8000 (or via Vite /api proxy)
 */

import type {
  ActiveEventsResponse,
  RawDetectionsResponse,
  CanonicalEvent,
  FacilitiesResponse,
  HealthResponse,
  FirmsStatusResponse,
  LocationAnalysisRequest,
  LocationAnalysisResponse,
  SatelliteContextResponse,
  StatisticsResponse,
  ChatRequest,
  ChatResponse,
  HotspotSummary,
  HotspotDetail,
  HotspotSnapshot,
  HotspotAnalytics,
  HotspotAlert,
  HotspotsListResponse,
  WindData,
  PlumeConeResponse,
  EmergencyFacility,
  EmergencyContextResponse,
  IncidentIntelResponse
} from '../types';

const RAW_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
export const API_BASE_URL = RAW_BASE_URL ? RAW_BASE_URL.replace(/\/$/, '') : '';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  
  const headers = new Headers(options.headers || {});
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    let errData: any = null;
    try {
      errData = await response.json();
      if (errData && errData.detail) {
        errorDetail = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // ignore json parse error on non-json error responses
    }
    throw new ApiError(errorDetail, response.status, errData);
  }

  return response.json() as Promise<T>;
}

export const api = {
  /**
   * Health check endpoint
   */
  async getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>('/api/health');
  },

  /**
   * Retrieve real NASA FIRMS connectivity status
   */
  async getFirmsStatus(): Promise<FirmsStatusResponse> {
    return request<FirmsStatusResponse>('/api/firms/status');
  },

  /**
   * Retrieve active FIRMS thermal anomalies worldwide
   */
  async getActiveEvents(): Promise<ActiveEventsResponse> {
    return request<ActiveEventsResponse>('/api/active-events');
  },

  /**
   * Retrieve raw NASA FIRMS satellite observations directly
   */
  async getRawDetections(limit: number = 1000, min_frp?: number): Promise<RawDetectionsResponse> {
    const query = new URLSearchParams();
    if (limit) query.set('limit', String(limit));
    if (min_frp != null) query.set('min_frp', String(min_frp));
    const qs = query.toString();
    return request<RawDetectionsResponse>(`/api/firms/raw-detections${qs ? `?${qs}` : ''}`);
  },

  /**
   * Retrieve single thermal event details by ID
   */
  async getEvent(eventId: string): Promise<CanonicalEvent> {
    return request<CanonicalEvent>(`/api/events/${encodeURIComponent(eventId)}`);
  },

  /**
   * Retrieve cached industrial facilities and active hotspots
   */
  async getFacilities(): Promise<FacilitiesResponse> {
    return request<FacilitiesResponse>('/api/facilities');
  },

  /**
   * Retrieve summary statistics of fire events
   */
  async getStatistics(): Promise<StatisticsResponse> {
    return request<StatisticsResponse>('/api/statistics');
  },

  /**
   * Coordinate-based AI investigation for arbitrary lat/lon
   */
  async analyseLocation(latitude: number, longitude: number): Promise<LocationAnalysisResponse> {
    const payload: LocationAnalysisRequest = { latitude, longitude };
    return request<LocationAnalysisResponse>('/api/analyse-location', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
  },

  /**
   * Retrieve satellite context imagery metadata for specified event
   */
  async getSatelliteContext(eventId: string): Promise<SatelliteContextResponse> {
    return request<SatelliteContextResponse>(`/api/satellite-context/${encodeURIComponent(eventId)}`);
  },

  /**
   * AI Question & Answer with context grounding via local Ollama/Qwen
   */
  async chat(question: string, context?: Record<string, any> | null): Promise<ChatResponse> {
    const payload: ChatRequest = { question, context: context || null };
    return request<ChatResponse>('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
  },

  // =====================================================================
  // PHASE 10.5: GLOBAL HOTSPOT INTELLIGENCE METHODS
  // =====================================================================

  /**
   * Query global hotspots with pagination, continent, country, classification, and risk filters
   */
  async getHotspots(params: {
    page?: number;
    page_size?: number;
    status?: string;
    classification?: string;
    continent?: string;
    country?: string;
    risk_tier?: string;
    min_risk?: number;
    min_frp?: number;
    min_persistence?: number;
    sort_by?: string;
    order?: string;
  } = {}): Promise<HotspotsListResponse> {
    const query = new URLSearchParams();
    if (params.page) query.set('page', String(params.page));
    if (params.page_size) query.set('page_size', String(params.page_size));
    if (params.status && params.status !== 'all') query.set('status', params.status);
    if (params.classification && params.classification !== 'all') query.set('classification', params.classification);
    if (params.continent && params.continent !== 'all') query.set('continent', params.continent);
    if (params.country && params.country !== 'all') query.set('country', params.country);
    if (params.risk_tier && params.risk_tier !== 'all') query.set('risk_tier', params.risk_tier);
    if (params.min_risk != null) query.set('min_risk', String(params.min_risk));
    if (params.min_frp != null) query.set('min_frp', String(params.min_frp));
    if (params.min_persistence != null) query.set('min_persistence', String(params.min_persistence));
    if (params.sort_by) query.set('sort_by', params.sort_by);
    if (params.order) query.set('order', params.order);

    const qs = query.toString();
    return request<HotspotsListResponse>(`/api/hotspots${qs ? `?${qs}` : ''}`);
  },

  /**
   * Retrieve global hotspot dashboard metrics and continent breakdown
   */
  async getHotspotAnalytics(): Promise<HotspotAnalytics> {
    return request<HotspotAnalytics>('/api/hotspots/analytics');
  },

  /**
   * Retrieve real-time actionable alerts for critical / rapidly expanding hotspots
   */
  async getHotspotAlerts(): Promise<HotspotAlert[]> {
    return request<HotspotAlert[]>('/api/hotspots/alerts');
  },

  /**
   * Retrieve single hotspot detailed scientific profile and timeline
   */
  async getHotspot(hotspotId: string): Promise<HotspotDetail> {
    return request<HotspotDetail>(`/api/hotspots/${encodeURIComponent(hotspotId)}`);
  },

  /**
   * Retrieve historical timeline snapshots for a hotspot
   */
  async getHotspotHistory(hotspotId: string): Promise<HotspotSnapshot[]> {
    return request<HotspotSnapshot[]>(`/api/hotspots/${encodeURIComponent(hotspotId)}/history`);
  },

  /**
   * Retrieve hotspots within a bounding box
   */
  async getHotspotsBBox(min_lat: number, min_lon: number, max_lat: number, max_lon: number): Promise<HotspotSummary[]> {
    return request<HotspotSummary[]>(`/api/hotspots/bbox?min_lat=${min_lat}&min_lon=${min_lon}&max_lat=${max_lat}&max_lon=${max_lon}`);
  },

  /**
   * Retrieve hotspots within a radius of a center coordinate
   */
  async getHotspotsNearby(latitude: number, longitude: number, radius_km: number = 500): Promise<HotspotSummary[]> {
    return request<HotspotSummary[]>(`/api/hotspots/nearby?latitude=${latitude}&longitude=${longitude}&radius_km=${radius_km}`);
  },

  // =====================================================================
  // PHASE 11: INCIDENT RESPONSE, WIND, PLUME, EMERGENCY & REPORT METHODS
  // =====================================================================

  /**
   * Retrieve real-time wind speed, direction, and hourly forecasts for a hotspot
   */
  async getHotspotWind(hotspotId: string): Promise<WindData> {
    return request<WindData>(`/api/hotspots/${encodeURIComponent(hotspotId)}/wind`);
  },

  /**
   * Retrieve time-aware indicative plume transport polygons (1h, 3h, 6h, 12h)
   */
  async getHotspotPlume(hotspotId: string): Promise<PlumeConeResponse> {
    return request<PlumeConeResponse>(`/api/hotspots/${encodeURIComponent(hotspotId)}/plume`);
  },

  /**
   * Retrieve nearby fire stations, hospitals, verified burn/trauma units, and hydrants
   */
  async getEmergencyNearby(latitude: number, longitude: number, radiusKm: number = 12): Promise<EmergencyFacility[]> {
    return request<EmergencyFacility[]>(`/api/emergency/nearby?latitude=${latitude}&longitude=${longitude}&radius_km=${radiusKm}`);
  },

  /**
   * Evaluate nearest emergency resources and calculate 1km / 3km evacuation planning buffer intersections
   */
  async getHotspotEmergencyContext(hotspotId: string): Promise<EmergencyContextResponse> {
    return request<EmergencyContextResponse>(`/api/hotspots/${encodeURIComponent(hotspotId)}/emergency-context`);
  },

  /**
   * Retrieve unified incident intelligence payload
   */
  async getHotspotIncidentIntel(hotspotId: string): Promise<IncidentIntelResponse> {
    return request<IncidentIntelResponse>(`/api/hotspots/${encodeURIComponent(hotspotId)}/incident-intel`);
  },

  /**
   * Download 2-page Executive Incident Disaster Brief in PDF format
   */
  getHotspotPdfReportUrl(hotspotId: string): string {
    return `/api/hotspots/${encodeURIComponent(hotspotId)}/report/pdf`;
  },
};

export default api;
