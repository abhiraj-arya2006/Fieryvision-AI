/**
 * Centralized API Service for FieryVision AI
 * Connects directly to FastAPI backend on localhost:8000 (or via Vite /api proxy)
 */

import type {
  ActiveEventsResponse,
  CanonicalEvent,
  FacilitiesResponse,
  HealthResponse,
  LocationAnalysisRequest,
  LocationAnalysisResponse,
  SatelliteContextResponse,
  StatisticsResponse,
  ChatRequest,
  ChatResponse
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
   * Retrieve active FIRMS thermal anomalies in Giaspura
   */
  async getActiveEvents(): Promise<ActiveEventsResponse> {
    return request<ActiveEventsResponse>('/api/active-events');
  },

  /**
   * Retrieve single thermal event details by ID
   */
  async getEvent(eventId: string): Promise<CanonicalEvent> {
    return request<CanonicalEvent>(`/api/events/${encodeURIComponent(eventId)}`);
  },

  /**
   * Retrieve cached industrial facilities in Giaspura
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
};

export default api;
