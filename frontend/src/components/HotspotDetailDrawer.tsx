import React, { useEffect, useState } from 'react';
import { 
  X, 
  Flame, 
  Activity, 
  MapPin, 
  Factory, 
  Satellite, 
  Sparkles,
  Info,
  BarChart2,
  Wind,
  Shield,
  Phone,
  FileText,
  Download,
  AlertTriangle,
  Compass,
  CheckCircle2,
  Loader2
} from 'lucide-react';
import type { 
  HotspotSummary, 
  HotspotDetail, 
  HotspotSnapshot, 
  WindData, 
  PlumeHorizonFeature,
  PlumeConeResponse, 
  EmergencyContextResponse 
} from '../types';
import { api } from '../services/api';

interface HotspotDetailDrawerProps {
  hotspot: HotspotSummary | null;
  isOpen: boolean;
  onClose: () => void;
  onFocusCoordinates?: (lat: number, lon: number) => void;
  windData?: WindData | null;
  plumeData?: PlumeConeResponse | null;
  emergencyData?: EmergencyContextResponse | null;
  incidentMode?: boolean;
  onToggleIncidentMode?: () => void;
  showWindVector?: boolean;
  onToggleWindVector?: () => void;
  showPlumeCone?: boolean;
  onTogglePlumeCone?: () => void;
  showBuffer1km?: boolean;
  onToggleBuffer1km?: () => void;
  showBuffer3km?: boolean;
  onToggleBuffer3km?: () => void;
  showEmergencyLayer?: boolean;
  onToggleEmergencyLayer?: () => void;
}

export const HotspotDetailDrawer: React.FC<HotspotDetailDrawerProps> = ({
  hotspot,
  isOpen,
  onClose,
  windData,
  plumeData,
  emergencyData,
  incidentMode = false,
  onToggleIncidentMode,
  showWindVector = true,
  onToggleWindVector,
  showPlumeCone = true,
  onTogglePlumeCone,
  showBuffer1km = true,
  onToggleBuffer1km,
  showBuffer3km = true,
  onToggleBuffer3km,
  showEmergencyLayer = true,
  onToggleEmergencyLayer,
}) => {
  const [detail, setDetail] = useState<HotspotDetail | null>(null);
  const [localWind, setLocalWind] = useState<WindData | null>(windData || null);
  const [localPlume, setLocalPlume] = useState<PlumeConeResponse | null>(plumeData || null);
  const [localEmergency, setLocalEmergency] = useState<EmergencyContextResponse | null>(emergencyData || null);
  const [loading, setLoading] = useState<boolean>(false);
  const [pdfDownloading, setPdfDownloading] = useState<boolean>(false);
  const [pdfSuccess, setPdfSuccess] = useState<boolean>(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'incident' | 'overview' | 'intensity' | 'history' | 'detections'>('incident');

  useEffect(() => {
    if (!hotspot || !isOpen) {
      setDetail(null);
      return;
    }

    let isMounted = true;
    setLoading(true);

    // Fetch hotspot detail, wind, plume, and emergency context in parallel
    Promise.all([
      api.getHotspot(hotspot.id).catch(() => null),
      api.getHotspotWind(hotspot.id).catch(() => null),
      api.getHotspotPlume(hotspot.id).catch(() => null),
      api.getHotspotEmergencyContext(hotspot.id).catch(() => null),
    ]).then(([detailRes, windRes, plumeRes, emRes]) => {
      if (isMounted) {
        if (detailRes) setDetail(detailRes);
        if (windRes) setLocalWind(windRes);
        if (plumeRes) setLocalPlume(plumeRes);
        if (emRes) setLocalEmergency(emRes);
        setLoading(false);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [hotspot, isOpen]);

  // Sync props if provided
  useEffect(() => {
    if (windData) setLocalWind(windData);
  }, [windData]);

  useEffect(() => {
    if (plumeData) setLocalPlume(plumeData);
  }, [plumeData]);

  useEffect(() => {
    if (emergencyData) setLocalEmergency(emergencyData);
  }, [emergencyData]);

  if (!isOpen || !hotspot) return null;

  const current = detail || hotspot;
  const reasonCodes = current.reason_codes || [];
  const snapshots: HotspotSnapshot[] = detail?.timeline_snapshots || [];
  const detections = detail?.sample_detections || [];
  const wind = localWind;
  const plume = localPlume;
  const emergency = localEmergency;

  const getRiskColor = (tier: string) => {
    switch ((tier || '').toUpperCase()) {
      case 'CRITICAL':
        return { bg: 'bg-red-500/20', text: 'text-red-300', border: 'border-red-500/40' };
      case 'HIGH':
        return { bg: 'bg-orange-500/20', text: 'text-orange-300', border: 'border-orange-500/40' };
      case 'MODERATE':
        return { bg: 'bg-yellow-500/20', text: 'text-yellow-300', border: 'border-yellow-500/40' };
      default:
        return { bg: 'bg-emerald-500/20', text: 'text-emerald-300', border: 'border-emerald-500/40' };
    }
  };

  const riskStyle = getRiskColor(current.risk_tier);

  const handleDownloadPdf = async () => {
    setPdfDownloading(true);
    setPdfError(null);
    setPdfSuccess(false);

    try {
      const reportUrl = api.getHotspotPdfReportUrl(current.id);
      const response = await fetch(reportUrl);
      if (!response.ok) {
        throw new Error(`Failed to generate report (HTTP ${response.status})`);
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `fieryvision_incident_${current.id.toLowerCase().replace(/-/g, '_')}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      setPdfSuccess(true);
      setTimeout(() => setPdfSuccess(false), 4000);
    } catch (err: any) {
      console.error('PDF Download Error:', err);
      setPdfError(err.message || 'Unable to generate incident PDF brief');
    } finally {
      setPdfDownloading(false);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 z-[9999] flex max-w-full pl-10">
      <div className="w-screen max-w-2xl bg-[#090f1e]/95 backdrop-blur-xl border-l border-cyan-500/30 shadow-2xl flex flex-col text-slate-200 overflow-hidden animate-in slide-in-from-right duration-300">
        
        {/* Drawer Header */}
        <div className="p-5 border-b border-slate-800 bg-[#060b17]/80 flex items-start justify-between gap-4">
          <div className="space-y-1.5 flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-500/40">
                {current.id}
              </span>
              <span className={`px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider ${riskStyle.bg} ${riskStyle.text} border ${riskStyle.border}`}>
                EVENT RISK: {current.risk_score.toFixed(0)}/100 ({current.risk_tier})
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                {current.status}
              </span>
              {current.anomaly_score >= 0.5 && (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40">
                  ML OUTLIER ({current.anomaly_score.toFixed(2)})
                </span>
              )}
              {loading && (
                <span className="inline-flex items-center gap-1 text-[10px] text-cyan-400 font-mono">
                  <Loader2 className="h-3 w-3 animate-spin" /> Syncing...
                </span>
              )}
            </div>
            
            <h2 className="text-lg font-bold text-white tracking-tight leading-snug truncate">
              {current.name}
            </h2>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400 font-mono">
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                {current.centroid_lat.toFixed(4)}°N, {current.centroid_lon.toFixed(4)}°E
              </span>
              <span>·</span>
              <span>{current.region ? `${current.region}, ` : ''}{current.country}</span>
              <span>·</span>
              <span className="text-cyan-300 font-semibold">{current.dominant_landcover}</span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors shrink-0"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center border-b border-slate-800 bg-slate-900/50 px-4 overflow-x-auto scrollbar-thin">
          <button
            onClick={() => setActiveTab('incident')}
            className={`px-3 py-2.5 text-xs font-bold border-b-2 flex items-center gap-1.5 whitespace-nowrap transition-colors ${
              activeTab === 'incident'
                ? 'border-amber-400 text-amber-300 bg-amber-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Shield className="h-3.5 w-3.5 text-amber-400" />
            <span>Incident Response & Intel</span>
          </button>

          <button
            onClick={() => setActiveTab('overview')}
            className={`px-3 py-2.5 text-xs font-semibold border-b-2 flex items-center gap-1.5 whitespace-nowrap transition-colors ${
              activeTab === 'overview'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Info className="h-3.5 w-3.5" />
            <span>Overview & Activity</span>
          </button>

          <button
            onClick={() => setActiveTab('intensity')}
            className={`px-3 py-2.5 text-xs font-semibold border-b-2 flex items-center gap-1.5 whitespace-nowrap transition-colors ${
              activeTab === 'intensity'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Activity className="h-3.5 w-3.5" />
            <span>Intensity & ML</span>
          </button>

          <button
            onClick={() => setActiveTab('history')}
            className={`px-3 py-2.5 text-xs font-semibold border-b-2 flex items-center gap-1.5 whitespace-nowrap transition-colors ${
              activeTab === 'history'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <BarChart2 className="h-3.5 w-3.5" />
            <span>Timeline History</span>
          </button>

          <button
            onClick={() => setActiveTab('detections')}
            className={`px-3 py-2.5 text-xs font-semibold border-b-2 flex items-center gap-1.5 whitespace-nowrap transition-colors ${
              activeTab === 'detections'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Satellite className="h-3.5 w-3.5" />
            <span>FIRMS Points ({detections.length})</span>
          </button>
        </div>

        {/* Drawer Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">

          {/* TAB 1: INCIDENT RESPONSE & INTELLIGENCE */}
          {activeTab === 'incident' && (
            <div className="space-y-5">
              
              {/* Executive Incident Header & PDF Action Banner */}
              <div className="glass-panel p-4 rounded-2xl bg-gradient-to-r from-amber-500/15 via-slate-900 to-cyan-950/40 border border-amber-500/30 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <span className="text-[10px] font-bold text-amber-400 uppercase tracking-widest block">
                    OPERATIONAL DECISION SUPPORT
                  </span>
                  <h3 className="text-base font-bold text-white mt-0.5">
                    Executive Incident Brief & Emergency Staging
                  </h3>
                  <p className="text-xs text-slate-300 mt-1 max-w-md leading-relaxed">
                    Integrated real-time Open-Meteo wind vectors, downwind transport cones, and OpenStreetMap emergency response assets.
                  </p>
                </div>

                <div className="flex flex-col items-end gap-2 shrink-0">
                  <button
                    onClick={handleDownloadPdf}
                    disabled={pdfDownloading}
                    className="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-slate-950 text-xs font-bold flex items-center gap-2 transition-all shadow-lg shadow-amber-500/20 disabled:opacity-50"
                  >
                    {pdfDownloading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : pdfSuccess ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      <FileText className="h-4 w-4" />
                    )}
                    <span>{pdfDownloading ? 'Generating Brief...' : pdfSuccess ? 'Brief Downloaded!' : 'Export Disaster Brief (PDF)'}</span>
                  </button>
                  <span className="text-[10px] font-mono text-slate-400">
                    2-Page Executive Printable PDF
                  </span>
                </div>
              </div>

              {pdfError && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-xs text-red-300 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-red-400 shrink-0" />
                  <span>{pdfError}</span>
                </div>
              )}

              {/* Map Layer Controls Bar */}
              <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                  <span>Interactive Map Layers</span>
                  {onToggleIncidentMode && (
                    <button
                      onClick={onToggleIncidentMode}
                      className={`px-2.5 py-0.5 rounded text-[10px] font-bold uppercase transition-colors border ${
                        incidentMode
                          ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                          : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white'
                      }`}
                    >
                      {incidentMode ? '🚨 Incident Mode Active' : 'Enable Incident Mode'}
                    </button>
                  )}
                </div>

                <div className="flex flex-wrap gap-1.5 pt-1">
                  {onToggleWindVector && (
                    <button
                      onClick={onToggleWindVector}
                      className={`px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors border ${
                        showWindVector
                          ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                          : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      <Wind className="h-3 w-3" />
                      <span>Wind Vector</span>
                    </button>
                  )}

                  {onTogglePlumeCone && (
                    <button
                      onClick={onTogglePlumeCone}
                      className={`px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors border ${
                        showPlumeCone
                          ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                          : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      <Flame className="h-3 w-3" />
                      <span>Plume Cones (1-12h)</span>
                    </button>
                  )}

                  {onToggleBuffer1km && (
                    <button
                      onClick={onToggleBuffer1km}
                      className={`px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors border ${
                        showBuffer1km
                          ? 'bg-orange-500/20 text-orange-300 border-orange-500/40'
                          : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      <span>⭕ 1 km Buffer</span>
                    </button>
                  )}

                  {onToggleBuffer3km && (
                    <button
                      onClick={onToggleBuffer3km}
                      className={`px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors border ${
                        showBuffer3km
                          ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                          : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      <span>⭕ 3 km Buffer</span>
                    </button>
                  )}

                  {onToggleEmergencyLayer && (
                    <button
                      onClick={onToggleEmergencyLayer}
                      className={`px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors border ${
                        showEmergencyLayer
                          ? 'bg-red-500/20 text-red-300 border-red-500/40'
                          : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      <span>🚒 Emergency Layer</span>
                    </button>
                  )}
                </div>
              </div>

              {/* SECTION: REAL-TIME WIND CONDITIONS */}
              <div className="glass-panel p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Wind className="h-4 w-4 text-amber-400" />
                    <h4 className="font-bold text-xs text-white uppercase tracking-wider">
                      Real-Time Meteorological & Wind Conditions
                    </h4>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">
                    Source: {wind?.source || 'Open-Meteo'}
                  </span>
                </div>

                {wind ? (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
                    <div className="p-2.5 rounded-lg bg-slate-800/80 border border-slate-700/80">
                      <span className="text-[10px] text-slate-400 block font-mono">10m Wind Speed</span>
                      <span className="text-sm font-bold text-amber-300 font-mono">
                        {wind.wind_speed_kmh} km/h
                      </span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-slate-800/80 border border-slate-700/80">
                      <span className="text-[10px] text-slate-400 block font-mono">Wind Direction</span>
                      <span className="text-sm font-bold text-white font-mono">
                        {wind.cardinal_direction} ({wind.wind_direction_deg}°)
                      </span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-slate-800/80 border border-slate-700/80">
                      <span className="text-[10px] text-slate-400 block font-mono">Downwind Bearing</span>
                      <span className="text-sm font-bold text-cyan-300 font-mono">
                        {wind.downwind_bearing_deg}°
                      </span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-slate-800/80 border border-slate-700/80">
                      <span className="text-[10px] text-slate-400 block font-mono">Temperature</span>
                      <span className="text-sm font-bold text-slate-200 font-mono">
                        {wind.temperature_c != null ? `${wind.temperature_c}°C` : '28°C'}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="py-4 text-center text-xs text-slate-500">
                    Loading atmospheric wind telemetry...
                  </div>
                )}
              </div>

              {/* SECTION: DOWNWIND TRANSPORT & PLUME CONES */}
              <div className="glass-panel p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Compass className="h-4 w-4 text-amber-400" />
                    <h4 className="font-bold text-xs text-white uppercase tracking-wider">
                      Indicative Downwind Exposure Horizons
                    </h4>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 font-mono">
                    Screening Model
                  </span>
                </div>

                {plume ? (
                  <div className="space-y-2">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {plume.horizons.map((hz: PlumeHorizonFeature) => (
                        <div
                          key={hz.horizon_hours}
                          className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/80 flex items-center justify-between text-xs font-mono"
                        >
                          <div>
                            <span className="font-bold text-amber-300">+{hz.horizon_hours}h Projection</span>
                            <span className="text-[10px] text-slate-400 block">
                              Bearing {hz.bearing_deg}° · Spread ±{(hz.cone_spread_angle_deg / 2).toFixed(0)}°
                            </span>
                          </div>
                          <div className="text-right">
                            <span className="font-bold text-white text-sm">~{hz.projected_distance_km} km</span>
                            <span className="text-[10px] text-slate-400 block">{hz.confidence_rating}</span>
                          </div>
                        </div>
                      ))}
                    </div>

                    <p className="text-[10px] text-slate-400 italic pt-1 leading-relaxed">
                      {plume.screening_disclaimer}
                    </p>
                  </div>
                ) : (
                  <div className="py-4 text-center text-xs text-slate-500">
                    Computing plume dispersion vectors...
                  </div>
                )}
              </div>

              {/* SECTION: NEAREST EMERGENCY RESOURCES */}
              <div className="glass-panel p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-cyan-400" />
                    <h4 className="font-bold text-xs text-white uppercase tracking-wider">
                      Nearest Emergency Response Infrastructure
                    </h4>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">
                    OpenStreetMap GIS
                  </span>
                </div>

                {emergency ? (
                  <div className="space-y-2">
                    {/* Fire Station */}
                    <div className="p-3 rounded-lg bg-slate-800/80 border border-slate-700/80 flex items-start justify-between gap-3 text-xs">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-red-300 text-[10px] font-bold font-mono">
                            🚒 FIRE STATION
                          </span>
                          <span className="font-bold text-white">
                            {emergency.nearest_fire_station?.name || 'Local Fire Service'}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono">
                          {emergency.nearest_fire_station?.address || 'Address listed in municipal register'}
                        </div>
                        {emergency.nearest_fire_station?.phone && (
                          <div className="text-[11px] text-emerald-300 font-mono flex items-center gap-1">
                            <Phone className="h-3 w-3" />
                            <span>{emergency.nearest_fire_station.phone}</span>
                          </div>
                        )}
                      </div>

                      <div className="text-right font-mono shrink-0">
                        <span className="text-cyan-300 font-bold text-sm block">
                          {emergency.nearest_fire_station ? `${(emergency.nearest_fire_station.distance_m / 1000).toFixed(2)} km` : 'N/A'}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          {emergency.nearest_fire_station ? `${emergency.nearest_fire_station.bearing_deg}°` : ''}
                        </span>
                      </div>
                    </div>

                    {/* Hospital & Verified Burn Unit */}
                    <div className="p-3 rounded-lg bg-slate-800/80 border border-slate-700/80 flex items-start justify-between gap-3 text-xs">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 text-[10px] font-bold font-mono">
                            🏥 HOSPITAL
                          </span>
                          <span className="font-bold text-white">
                            {emergency.nearest_hospital?.name || 'District Hospital'}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono">
                          {emergency.nearest_hospital?.specialty_note || 'Specialty capability not verified on OpenStreetMap'}
                        </div>
                        {emergency.nearest_hospital?.phone && (
                          <div className="text-[11px] text-emerald-300 font-mono flex items-center gap-1">
                            <Phone className="h-3 w-3" />
                            <span>{emergency.nearest_hospital.phone}</span>
                          </div>
                        )}
                      </div>

                      <div className="text-right font-mono shrink-0">
                        <span className="text-cyan-300 font-bold text-sm block">
                          {emergency.nearest_hospital ? `${(emergency.nearest_hospital.distance_m / 1000).toFixed(2)} km` : 'N/A'}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          {emergency.nearest_hospital ? `${emergency.nearest_hospital.bearing_deg}°` : ''}
                        </span>
                      </div>
                    </div>

                    {/* Hydrant */}
                    <div className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/80 flex items-center justify-between text-xs font-mono">
                      <div>
                        <span className="text-cyan-300 font-bold">🚰 Nearest Water Hydrant:</span>{' '}
                        <span className="text-slate-200">
                          {emergency.nearest_hydrant?.name || 'Municipal Hydrant Network'}
                        </span>
                      </div>
                      <span className="text-white font-bold">
                        {emergency.nearest_hydrant ? `${(emergency.nearest_hydrant.distance_m / 1000).toFixed(2)} km` : 'Coverage varies'}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="py-4 text-center text-xs text-slate-500">
                    Locating nearest municipal emergency assets...
                  </div>
                )}
              </div>

              {/* SECTION: 1 KM & 3 KM PLANNING BUFFERS SUMMARY */}
              <div className="glass-panel p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
                <h4 className="font-bold text-xs text-white uppercase tracking-wider">
                  Evacuation & Response Planning Buffer Intersections
                </h4>

                {emergency ? (
                  <div className="grid grid-cols-2 gap-3 font-mono text-xs">
                    {/* 1 km Buffer Card */}
                    <div className="p-3 rounded-lg bg-orange-950/20 border border-orange-500/30 space-y-2">
                      <div className="flex items-center justify-between text-orange-300 font-bold">
                        <span>⭕ 1 km Planning Zone</span>
                      </div>
                      <div className="space-y-1 text-[11px] text-slate-300">
                        <div className="flex justify-between">
                          <span>Fire Stations:</span>
                          <span className="font-bold text-white">{emergency.buffer_1km.fire_stations_count}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Hospitals:</span>
                          <span className="font-bold text-white">{emergency.buffer_1km.hospitals_count}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Hydrants:</span>
                          <span className="font-bold text-white">{emergency.buffer_1km.hydrants_count}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Industrial Sites:</span>
                          <span className="font-bold text-white">{emergency.buffer_1km.industrial_facilities_count}</span>
                        </div>
                      </div>
                    </div>

                    {/* 3 km Buffer Card */}
                    <div className="p-3 rounded-lg bg-cyan-950/20 border border-cyan-500/30 space-y-2">
                      <div className="flex items-center justify-between text-cyan-300 font-bold">
                        <span>⭕ 3 km Planning Zone</span>
                      </div>
                      <div className="space-y-1 text-[11px] text-slate-300">
                        <div className="flex justify-between">
                          <span>Fire Stations:</span>
                          <span className="font-bold text-white">{emergency.buffer_3km.fire_stations_count}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Hospitals:</span>
                          <span className="font-bold text-white">{emergency.buffer_3km.hospitals_count}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Hydrants:</span>
                          <span className="font-bold text-white">{emergency.buffer_3km.hydrants_count}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Industrial Sites:</span>
                          <span className="font-bold text-white">{emergency.buffer_3km.industrial_facilities_count}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="py-4 text-center text-xs text-slate-500">
                    Evaluating spatial buffer intersections...
                  </div>
                )}
              </div>

            </div>
          )}

          {/* TAB 2: OVERVIEW & ACTIVITY */}
          {activeTab === 'overview' && (
            <div className="space-y-5">
              
              {/* Primary Metric Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="glass-panel p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-mono block">AREA EXTENT</span>
                  <span className="text-lg font-bold text-white font-mono">
                    {current.area_sq_km.toFixed(1)} <span className="text-xs text-slate-400">km²</span>
                  </span>
                </div>

                <div className="glass-panel p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-mono block">DETECTIONS</span>
                  <span className="text-lg font-bold text-cyan-400 font-mono">
                    {current.event_count} <span className="text-xs text-slate-400">pixels</span>
                  </span>
                </div>

                <div className="glass-panel p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-mono block">DURATION</span>
                  <span className="text-lg font-bold text-amber-400 font-mono">
                    {current.duration_hours.toFixed(1)} <span className="text-xs text-slate-400">hrs</span>
                  </span>
                </div>

                <div className="glass-panel p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-mono block">CONFIDENCE</span>
                  <span className="text-lg font-bold text-emerald-400 font-mono">
                    {(current.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Reason Codes & Tags */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
                  <span>Explainable Intelligence Triggers</span>
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {reasonCodes.map((code: string, idx: number) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-lg text-xs font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-500/30"
                    >
                      {code}
                    </span>
                  ))}
                </div>
              </div>

              {/* Geographic Context Card */}
              <div className="glass-panel p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <Factory className="h-3.5 w-3.5 text-cyan-400" />
                  <span>Critical Infrastructure & Land Cover</span>
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
                  <div className="space-y-1">
                    <span className="text-slate-500 block text-[10px]">NEAREST FACILITY</span>
                    <span className="text-white font-semibold">
                      {current.nearest_facility_name || 'No industrial facility within 5km'}
                    </span>
                    {current.nearest_facility_distance_m && (
                      <span className="text-cyan-400 text-[11px] block">
                        {(current.nearest_facility_distance_m / 1000).toFixed(2)} km distance
                      </span>
                    )}
                  </div>

                  <div className="space-y-1">
                    <span className="text-slate-500 block text-[10px]">DOMINANT LAND COVER</span>
                    <span className="text-white font-semibold">
                      {current.dominant_landcover}
                    </span>
                    <span className="text-slate-400 text-[11px] block">
                      ESA WorldCover 10m High-Resolution Map
                    </span>
                  </div>
                </div>

                {detail?.landcover_classes && detail.landcover_classes.length > 0 && (
                  <div className="pt-2 border-t border-slate-800">
                    <span className="text-[10px] text-slate-500 block font-mono mb-1">OBSERVED LAND COVER CLASSES</span>
                    <div className="flex flex-wrap gap-1">
                      {detail.landcover_classes.map((lc: string, i: number) => (
                        <span key={i} className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300">
                          {lc}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Scientific Uncertainty Disclosure */}
              {current.uncertainty_note && (
                <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200/90 leading-relaxed flex items-start gap-2.5">
                  <Info className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold text-amber-300 block mb-0.5">Scientific Classification Note</span>
                    {current.uncertainty_note}
                  </div>
                </div>
              )}

            </div>
          )}

          {/* TAB 3: INTENSITY & ML ANOMALY */}
          {activeTab === 'intensity' && (
            <div className="space-y-5">
              
              {/* FRP & Brightness Metrics */}
              <div className="grid grid-cols-2 gap-3">
                <div className="glass-panel p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-400 font-mono block">FIRE RADIATIVE POWER (FRP)</span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold text-orange-400 font-mono">
                      {current.average_frp.toFixed(1)}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">avg MW</span>
                  </div>
                  <span className="text-xs text-slate-400 block pt-1 font-mono">
                    Peak: <b className="text-white">{current.max_frp.toFixed(1)} MW</b> ({current.frp_trend} trend)
                  </span>
                </div>

                <div className="glass-panel p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-400 font-mono block">BRIGHTNESS TEMPERATURE</span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold text-amber-300 font-mono">
                      {current.average_brightness.toFixed(0)}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">avg K</span>
                  </div>
                  <span className="text-xs text-slate-400 block pt-1 font-mono">
                    Peak: <b className="text-white">{current.max_brightness.toFixed(0)} K</b> (Channel 21/I4)
                  </span>
                </div>
              </div>

              {/* ML Anomaly Assessment */}
              <div className="glass-panel p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-purple-400" />
                    <span>ML Outlier & Anomaly Scoring</span>
                  </h4>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-950 text-purple-300 border border-purple-500/40">
                    Isolation Forest
                  </span>
                </div>

                <div className="flex items-center gap-4">
                  <div className="relative w-20 h-20 rounded-full border-4 border-purple-500/30 flex items-center justify-center shrink-0">
                    <span className="text-lg font-bold text-purple-300 font-mono">
                      {current.anomaly_score.toFixed(2)}
                    </span>
                  </div>
                  <div className="text-xs text-slate-300 space-y-1">
                    <p className="font-semibold text-white">
                      {current.anomaly_score >= 0.5 ? 'Significant Statistical Outlier' : 'Nominal Thermal Profile'}
                    </p>
                    <p className="text-slate-400 text-[11px] leading-relaxed">
                      Evaluates multi-dimensional deviations across brightness temperature, FRP gradient, and recurrence baseline.
                    </p>
                  </div>
                </div>
              </div>

              {/* Satellites & Passes */}
              <div className="glass-panel p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <Satellite className="h-3.5 w-3.5 text-cyan-400" />
                  <span>Constellation Multi-Satellite Telemetry</span>
                </h4>
                
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {(detail?.source_satellites || ['VIIRS NOAA-20', 'VIIRS NOAA-21', 'MODIS Aqua', 'MODIS Terra']).map((sat: string, i: number) => (
                    <span key={i} className="px-2.5 py-1 rounded bg-slate-800 text-cyan-300 text-xs font-mono border border-slate-700">
                      🛰️ {sat}
                    </span>
                  ))}
                </div>

                {detail?.daynight_distribution && (
                  <div className="grid grid-cols-2 gap-3 pt-2 text-[11px]">
                    <div className="p-2.5 rounded bg-slate-800/70 border border-slate-700 text-center font-mono">
                      <span className="text-yellow-400 font-bold block text-sm">☀️ {detail.daynight_distribution.day || 0}</span>
                      <span className="text-slate-400">Daytime Passes</span>
                    </div>
                    <div className="p-2.5 rounded bg-slate-800/70 border border-slate-700 text-center font-mono">
                      <span className="text-indigo-400 font-bold block text-sm">🌙 {detail.daynight_distribution.night || 0}</span>
                      <span className="text-slate-400">Nighttime Passes</span>
                    </div>
                  </div>
                )}
              </div>

            </div>
          )}

          {/* TAB 4: TIMELINE HISTORY */}
          {activeTab === 'history' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                  Multi-Pass Evolution Snapshots
                </h4>
                <span className="text-xs text-slate-400 font-mono">
                  First seen: {new Date(current.first_seen).toLocaleDateString()}
                </span>
              </div>

              {snapshots.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500">
                  No historical snapshots recorded for this cluster yet.
                </div>
              ) : (
                <div className="space-y-3">
                  {snapshots.map((snap, idx) => (
                    <div
                      key={idx}
                      className="glass-panel rounded-xl p-3 bg-slate-900/60 border border-slate-800 space-y-2"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-mono text-cyan-300 font-semibold">
                          ⏱️ {new Date(snap.timestamp).toLocaleString()}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300">
                          Risk: {snap.risk_score.toFixed(0)}/100
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-2 text-[11px] font-mono text-slate-300 pt-1">
                        <div>
                          <span className="text-slate-500 block text-[10px]">Detections</span>
                          <span>{snap.event_count} pts</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block text-[10px]">Max FRP</span>
                          <span className="text-orange-400">{snap.max_frp.toFixed(0)} MW</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block text-[10px]">Area</span>
                          <span>{snap.area_sq_km.toFixed(1)} km²</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 5: FIRMS CONSTITUENT DETECTIONS */}
          {activeTab === 'detections' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs">
                <h4 className="font-bold text-white uppercase tracking-wider">
                  Constituent NASA FIRMS Pixels
                </h4>
                <span className="font-mono text-cyan-400">{detections.length} sampled points</span>
              </div>

              {detections.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500">
                  Constituent detection pixel points are loaded on satellite sync.
                </div>
              ) : (
                <div className="space-y-2">
                  {detections.map((det: any, idx: number) => (
                    <div
                      key={idx}
                      className="glass-panel rounded-xl p-2.5 bg-slate-900/60 border border-slate-800 text-xs flex items-center justify-between font-mono"
                    >
                      <div>
                        <div className="font-bold text-white">
                          {det.latitude.toFixed(4)}°N, {det.longitude.toFixed(4)}°E
                        </div>
                        <div className="text-[10px] text-slate-400 mt-0.5">
                          {det.acq_date || '2026-09-26'} {det.acq_time || '1200'} · {det.satellite || 'VIIRS'} ({det.daynight || 'D'})
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="text-orange-400 font-bold">
                          {det.frp != null ? `${det.frp.toFixed(1)} MW` : 'N/A'}
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {det.brightness != null ? `${det.brightness.toFixed(0)} K` : 'Conf: ' + (det.confidence || 'high')}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

        </div>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-slate-800 bg-[#060b17]/90 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
          <div className="flex items-center gap-2 font-mono text-[11px]">
            <span>Engine: {detail?.model_version || 'v11.0-incident-engine'}</span>
            <span>·</span>
            <span>Open-Meteo & OSM Active</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadPdf}
              disabled={pdfDownloading}
              className="px-3 py-1.5 rounded-lg border border-amber-500/40 bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 text-xs font-bold flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <Download className="h-3.5 w-3.5" />
              <span>{pdfDownloading ? 'Exporting...' : 'PDF Brief'}</span>
            </button>

            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium transition-colors"
            >
              Close Panel
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};

export default HotspotDetailDrawer;
