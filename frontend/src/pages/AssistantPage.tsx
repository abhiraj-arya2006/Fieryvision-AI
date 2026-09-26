import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { 
  Bot, 
  MapPin, 
  Search, 
  AlertTriangle, 
  Cpu, 
  Factory, 
  Clock, 
  CheckCircle2, 
  Send, 
  Sparkles, 
  Compass,
  RotateCcw
} from 'lucide-react';
import api from '../services/api';
import type { LocationAnalysisResponse } from '../types';
import { getPriorityColor, formatDistance } from '../utils/formatters';

// Giaspura presets for fast 1-click testing
const PRESETS = [
  { name: 'Giaspura Focal Point Cluster', lat: 30.876210, lon: 75.899120 },
  { name: 'Ludhiana Textile Dyeing Plant', lat: 30.874100, lon: 75.897250 },
  { name: 'Dhandari Kalan Industrial Hub', lat: 30.881000, lon: 75.905000 },
  { name: 'Giaspura Boiler & Casting Works', lat: 30.872800, lon: 75.895100 },
];

const SUGGESTED_QUESTIONS = [
  "Is this location inside an industrial zone?",
  "What is the nearest facility & distance?",
  "Explain the risk score and priority",
  "What evidence was recorded?",
  "What action should be taken?"
];

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  isLlm?: boolean;
}

export const AssistantPage: React.FC = () => {
  const [searchParams] = useSearchParams();

  const [latitude, setLatitude] = useState<string>(searchParams.get('lat') || '30.875625');
  const [longitude, setLongitude] = useState<string>(searchParams.get('lon') || '75.898481');
  const [inputErrors, setInputErrors] = useState<{ latitude?: string; longitude?: string }>({});

  const [isAnalysing, setIsAnalysing] = useState<boolean>(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisData, setAnalysisData] = useState<LocationAnalysisResponse | null>(null);

  // Chat state
  const [chatQuery, setChatQuery] = useState<string>('');
  const [isChatLoading, setIsChatLoading] = useState<boolean>(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatError, setChatError] = useState<string | null>(null);

  // Auto-run if coordinates were provided in URL query
  useEffect(() => {
    const latParam = searchParams.get('lat');
    const lonParam = searchParams.get('lon');
    if (latParam && lonParam) {
      setLatitude(latParam);
      setLongitude(lonParam);
      triggerAnalysis(parseFloat(latParam), parseFloat(lonParam));
    }
  }, [searchParams]);

  const validate = (latStr: string, lonStr: string) => {
    const errors: { latitude?: string; longitude?: string } = {};
    const lat = parseFloat(latStr);
    const lon = parseFloat(lonStr);

    if (latStr.trim() === '' || isNaN(lat)) {
      errors.latitude = 'Latitude is required (-90 to 90)';
    } else if (lat < -90 || lat > 90) {
      errors.latitude = 'Latitude must be between -90 and +90';
    }

    if (lonStr.trim() === '' || isNaN(lon)) {
      errors.longitude = 'Longitude is required (-180 to 180)';
    } else if (lon < -180 || lon > 180) {
      errors.longitude = 'Longitude must be between -180 and +180';
    }

    return errors;
  };

  const triggerAnalysis = async (lat: number, lon: number) => {
    setIsAnalysing(true);
    setAnalysisError(null);
    setAnalysisData(null);
    setChatMessages([]);
    setChatError(null);

    try {
      const data = await api.analyseLocation(lat, lon);
      setAnalysisData(data);
    } catch (err: any) {
      setAnalysisError(err?.message || 'Unable to connect to FieryVision backend.');
    } finally {
      setIsAnalysing(false);
    }
  };

  const handleAnalyseSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const errors = validate(latitude, longitude);
    setInputErrors(errors);
    if (Object.keys(errors).length > 0) return;

    triggerAnalysis(parseFloat(latitude), parseFloat(longitude));
  };

  const handleSelectPreset = (lat: number, lon: number) => {
    setLatitude(lat.toString());
    setLongitude(lon.toString());
    setInputErrors({});
    triggerAnalysis(lat, lon);
  };

  const handleChat = async (overrideQuery?: string) => {
    const question = (overrideQuery || chatQuery).trim();
    if (!question) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: question,
      timestamp: timeStr,
    };

    setChatMessages((prev) => [...prev, userMsg]);
    setIsChatLoading(true);
    setChatError(null);
    if (!overrideQuery) {
      setChatQuery('');
    }

    const context = analysisData
      ? {
          latitude: analysisData.latitude,
          longitude: analysisData.longitude,
          classification: analysisData.classification,
          classification_method: analysisData.classification_method,
          risk_score: analysisData.risk_score,
          priority: analysisData.priority,
          nearest_facility_name: analysisData.nearest_facility_name,
          nearest_facility_type: analysisData.nearest_facility_type,
          distance_to_facility_m: analysisData.distance_to_facility_m,
          inside_industrial_zone: analysisData.inside_industrial_zone,
          landcover: analysisData.landcover,
          thermal_activity_detected: analysisData.thermal_activity_detected,
          active_anomalies_count: analysisData.active_anomalies_count,
          temporal_summary: analysisData.temporal_summary || {},
          evidence: analysisData.evidence || [],
        }
      : null;

    try {
      const res = await api.chat(question, context);
      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: res.response || '- No response returned.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isLlm: res.llm_available,
      };
      setChatMessages((prev) => [...prev, aiMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: '- Note: ' + (err?.message || 'Unable to connect to AI explanation service.'),
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isLlm: false,
      };
      setChatMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const priorityStyle = getPriorityColor(analysisData?.priority);
  const temporal = analysisData?.temporal_summary || {};

  return (
    <div className="flex-1 p-3 sm:p-5 lg:p-6 w-full space-y-6">
      
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
            <Bot className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              FieryVision AI Location Investigation
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
              Coordinate-based AI assessment, thermal anomaly detection, and local Qwen LLM chat · Giaspura Study Area
            </p>
          </div>
        </div>
      </div>

      {/* Input Card & Quick Presets */}
      <div className="glass-panel p-5 rounded-2xl border border-cyan-500/25 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <MapPin className="h-4 w-4 text-cyan-400" />
            <span>Target Coordinates</span>
          </div>
          <span className="text-xs text-slate-400 font-mono">EPSG:4326 (WGS 84)</span>
        </div>

        <form onSubmit={handleAnalyseSubmit} className="grid sm:grid-cols-7 gap-3 items-end">
          <div className="sm:col-span-3 space-y-1">
            <label className="text-xs font-medium text-slate-300">Latitude</label>
            <input
              type="text"
              placeholder="e.g. 30.875625"
              value={latitude}
              onChange={(e) => {
                setLatitude(e.target.value);
                setInputErrors({});
              }}
              className={`w-full px-3 py-2 rounded-lg bg-slate-900/90 border text-white text-xs font-mono focus:outline-none focus:border-cyan-500 ${
                inputErrors.latitude ? 'border-red-500/70' : 'border-slate-700'
              }`}
            />
            {inputErrors.latitude && (
              <span className="text-[11px] text-red-400">{inputErrors.latitude}</span>
            )}
          </div>

          <div className="sm:col-span-3 space-y-1">
            <label className="text-xs font-medium text-slate-300">Longitude</label>
            <input
              type="text"
              placeholder="e.g. 75.898481"
              value={longitude}
              onChange={(e) => {
                setLongitude(e.target.value);
                setInputErrors({});
              }}
              className={`w-full px-3 py-2 rounded-lg bg-slate-900/90 border text-white text-xs font-mono focus:outline-none focus:border-cyan-500 ${
                inputErrors.longitude ? 'border-red-500/70' : 'border-slate-700'
              }`}
            />
            {inputErrors.longitude && (
              <span className="text-[11px] text-red-400">{inputErrors.longitude}</span>
            )}
          </div>

          <button
            type="submit"
            disabled={isAnalysing}
            className="sm:col-span-1 h-[38px] px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-md shadow-cyan-600/20 transition-all"
          >
            {isAnalysing ? (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <>
                <Search className="h-3.5 w-3.5" />
                <span>Analyse</span>
              </>
            )}
          </button>
        </form>

        {/* Quick Presets */}
        <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-slate-400 text-[11px] font-medium mr-1">Quick Presets:</span>
          {PRESETS.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSelectPreset(preset.lat, preset.lon)}
              className="px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-cyan-950/40 text-slate-300 hover:text-cyan-300 border border-slate-700/60 hover:border-cyan-500/40 text-[11px] transition-colors"
            >
              {preset.name}
            </button>
          ))}
        </div>
      </div>

      {/* Error Banner */}
      {analysisError && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-3 text-red-200 text-xs">
          <AlertTriangle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-red-300">Analysis Error</h4>
            <p className="mt-0.5 text-red-300/80">{analysisError}</p>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!analysisData && !isAnalysing && (
        <div className="glass-panel p-12 rounded-2xl text-center flex flex-col items-center justify-center space-y-3 border-dashed border-slate-800">
          <div className="p-3 rounded-full bg-cyan-500/10 text-cyan-400">
            <Compass className="h-8 w-8" />
          </div>
          <h3 className="text-base font-semibold text-white">Awaiting Location Coordinates</h3>
          <p className="text-xs text-slate-400 max-w-md">
            Enter a latitude and longitude above, or select one of the Giaspura industrial presets to run real-time geospatial risk assessment.
          </p>
        </div>
      )}

      {/* Full Analysis Results Dashboard */}
      {analysisData && (
        <div className="space-y-5 animate-in fade-in duration-300">
          
          {/* Top Summary Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            
            {/* Priority */}
            <div className="glass-panel p-4 rounded-xl border border-cyan-500/20">
              <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Priority Assessment
              </div>
              <div className="mt-1 flex items-center justify-between">
                <span className={`px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider text-xs border ${priorityStyle.bg} ${priorityStyle.text} ${priorityStyle.border}`}>
                  {analysisData.priority.toUpperCase()} PRIORITY
                </span>
                <span className="text-[11px] font-mono text-slate-400">
                  {analysisData.assessment_mode}
                </span>
              </div>
              <div className="text-[11px] text-slate-400 mt-2">
                Classification: <span className="text-white font-medium">{analysisData.classification}</span>
              </div>
            </div>

            {/* Risk Score */}
            <div className="glass-panel p-4 rounded-xl border border-cyan-500/20">
              <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Risk Score
              </div>
              <div className="mt-1 flex items-baseline gap-1">
                <span className="text-2xl font-bold font-mono text-white">
                  {analysisData.risk_score}
                </span>
                <span className="text-xs text-slate-400">/ 100</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden mt-2">
                <div
                  className={`h-full ${
                    analysisData.risk_score >= 70 ? 'bg-red-500' : analysisData.risk_score >= 40 ? 'bg-orange-500' : 'bg-cyan-500'
                  }`}
                  style={{ width: `${Math.max(5, analysisData.risk_score)}%` }}
                />
              </div>
            </div>

            {/* Thermal Activity */}
            <div className="glass-panel p-4 rounded-xl border border-cyan-500/20">
              <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Thermal Activity (1km)
              </div>
              <div className="mt-1 text-lg font-bold font-mono text-white flex items-center gap-2">
                <span className={analysisData.thermal_activity_detected ? 'text-orange-400' : 'text-slate-400'}>
                  {analysisData.thermal_activity_detected ? 'Detected' : 'None Detected'}
                </span>
              </div>
              <div className="text-[11px] text-slate-400 mt-2 font-mono">
                {analysisData.active_anomalies_count} nearby thermal event(s)
              </div>
            </div>

            {/* Giaspura Buffer Proximity */}
            <div className="glass-panel p-4 rounded-xl border border-cyan-500/20">
              <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Giaspura Monitoring Zone
              </div>
              <div className="mt-1 text-lg font-bold font-mono text-white">
                <span className={analysisData.in_giaspura_zone ? 'text-emerald-400' : 'text-slate-400'}>
                  {analysisData.in_giaspura_zone ? 'Inside Zone (≤ 15km)' : 'Outside Regional Zone'}
                </span>
              </div>
              <div className="text-[11px] text-slate-400 mt-2 font-mono">
                {formatDistance(analysisData.distance_to_giaspura_center_m)} from center
              </div>
            </div>

          </div>

          {/* 3-Column Detailed Analysis Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            
            {/* 1. Thermal & ML Intelligence */}
            <div className="glass-panel p-4 rounded-xl border border-slate-800 space-y-3">
              <div className="flex items-center gap-2 text-cyan-400 font-semibold border-b border-slate-800 pb-2">
                <Cpu className="h-4 w-4" />
                <span>Thermal & ML Intelligence</span>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-400">ML Isolation Forest:</span>
                  <span className={`font-semibold ${
                    analysisData.is_anomaly || analysisData.anomaly_flag ? 'text-red-400' : 'text-emerald-400'
                  }`}>
                    {analysisData.is_anomaly || analysisData.anomaly_flag ? '🚨 Outlier Flagged' : 'Normal Behavior'}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-400">ML Anomaly Score:</span>
                  <span className="font-mono text-white font-medium">
                    {analysisData.anomaly_score != null ? `${analysisData.anomaly_score} / 1.0` : '0.00'}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-400">Method:</span>
                  <span className="font-mono text-white">{analysisData.classification_method}</span>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-400">Confidence:</span>
                  <span className="font-mono text-white">
                    {analysisData.classification_confidence != null ? `${analysisData.classification_confidence}%` : 'N/A'}
                  </span>
                </div>
              </div>
            </div>

            {/* 2. Industrial Context */}
            <div className="glass-panel p-4 rounded-xl border border-slate-800 space-y-3">
              <div className="flex items-center gap-2 text-cyan-400 font-semibold border-b border-slate-800 pb-2">
                <Factory className="h-4 w-4" />
                <span>Industrial Proximity</span>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-400">Nearest Facility:</span>
                  <span className="text-white font-medium text-right max-w-[170px] truncate" title={analysisData.nearest_facility_name || 'None'}>
                    {analysisData.nearest_facility_name || 'None within 15km'}
                  </span>
                </div>

                {analysisData.nearest_facility_type && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Facility Type:</span>
                    <span className="text-slate-300 text-right">{analysisData.nearest_facility_type}</span>
                  </div>
                )}

                <div className="flex justify-between">
                  <span className="text-slate-400">Distance:</span>
                  <span className="font-mono text-cyan-300">{formatDistance(analysisData.distance_to_facility_m)}</span>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-400">Inside Industrial Zone:</span>
                  <span className={`font-semibold ${analysisData.inside_industrial_zone ? 'text-emerald-400' : 'text-slate-400'}`}>
                    {analysisData.inside_industrial_zone ? 'Yes' : 'No'}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-400">Land Cover:</span>
                  <span className="text-slate-300">{analysisData.landcover || 'Built-up / Industrial'}</span>
                </div>
              </div>
            </div>

            {/* 3. Temporal Persistence */}
            <div className="glass-panel p-4 rounded-xl border border-slate-800 space-y-3">
              <div className="flex items-center gap-2 text-cyan-400 font-semibold border-b border-slate-800 pb-2">
                <Clock className="h-4 w-4" />
                <span>Temporal Persistence</span>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-400">Status:</span>
                  <span className="text-white capitalize">{temporal.persistence || 'Transient'}</span>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-400">Detections (7 Days):</span>
                  <span className="font-mono text-white">{temporal.detections_7d ?? 'None'}</span>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-400">Detections (30 Days):</span>
                  <span className="font-mono text-white">{temporal.detections_30d ?? 'None'}</span>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-400">First Seen:</span>
                  <span className="font-mono text-white">{temporal.first_seen || 'N/A'}</span>
                </div>
              </div>
            </div>

          </div>

          {/* AI Assessment Card */}
          <div className="glass-panel p-5 rounded-xl border border-cyan-500/30 bg-cyan-950/20 space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-cyan-300 tracking-wider uppercase">
              <Sparkles className="h-4 w-4" />
              <span>AI Assessment & Synthesis</span>
            </div>
            <div className="text-xs text-slate-200 leading-relaxed space-y-1">
              {analysisData.explanation ? (
                <div className="whitespace-pre-line font-mono text-[12px]">
                  {analysisData.explanation}
                </div>
              ) : (
                <span className="text-slate-400">
                  Evidence evaluation completed. No severe thermal outlier flagged at this coordinate.
                </span>
              )}
            </div>
          </div>

          {/* Evidence Checklist & Ask FieryVision Chat */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            
            {/* Evidence Checklist */}
            <div className="glass-panel p-5 rounded-xl border border-slate-800 space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-300 uppercase tracking-wider border-b border-slate-800 pb-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span>Evidence Log</span>
              </div>

              {(analysisData.evidence || []).length > 0 ? (
                <ul className="space-y-2">
                  {(analysisData.evidence || []).map((item, idx) => (
                    <li key={idx} className="flex items-start gap-2.5 text-xs text-slate-300">
                      <span className="text-cyan-400 font-bold mt-0.5">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-slate-500 text-xs py-4">No specific evidence records for this location.</p>
              )}
            </div>

            {/* Ask FieryVision Chat Console */}
            <div className="glass-panel p-5 rounded-xl border border-slate-800 flex flex-col justify-between space-y-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-slate-300 uppercase tracking-wider">
                    <Bot className="h-4 w-4 text-cyan-400" />
                    <span>Ask FieryVision (Grounded AI)</span>
                  </div>
                  {chatMessages.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setChatMessages([])}
                      className="text-[11px] text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-1 cursor-pointer"
                    >
                      <RotateCcw className="h-3 w-3" />
                      <span>Clear</span>
                    </button>
                  )}
                </div>
                
                <p className="text-xs text-slate-400">
                  Ask questions about this specific coordinate investigation. Grounded strictly in verified spatial data.
                </p>

                {/* Suggested Question Chips */}
                <div className="flex flex-wrap gap-1.5 pt-0.5">
                  {SUGGESTED_QUESTIONS.map((q, idx) => (
                    <button
                      key={idx}
                      type="button"
                      disabled={isChatLoading}
                      onClick={() => handleChat(q)}
                      className="text-[11px] px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-cyan-950/70 border border-slate-700 hover:border-cyan-500/50 text-slate-300 hover:text-cyan-300 transition-all text-left cursor-pointer"
                    >
                      {q}
                    </button>
                  ))}
                </div>

                {/* Chat Message History */}
                <div className="max-h-72 overflow-y-auto space-y-2.5 pr-1 pt-2">
                  {chatMessages.length === 0 ? (
                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 text-xs text-slate-400 font-mono">
                      No questions yet. Click a suggestion chip above or type any question below.
                    </div>
                  ) : (
                    chatMessages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`p-3 rounded-xl text-xs leading-relaxed ${
                          msg.sender === 'user'
                            ? 'bg-cyan-950/40 border border-cyan-500/40 text-cyan-100 ml-6'
                            : 'bg-slate-900/90 border border-slate-800 text-slate-200 mr-2 font-mono whitespace-pre-line'
                        }`}
                      >
                        <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1 font-sans">
                          <span className="font-semibold text-slate-300">
                            {msg.sender === 'user'
                              ? 'You'
                              : (msg.isLlm ? 'FieryVision AI (Local Qwen LLM)' : 'FieryVision AI (Grounded Intelligence)')}
                          </span>
                          <span>{msg.timestamp}</span>
                        </div>
                        <div>{msg.text}</div>
                      </div>
                    ))
                  )}

                  {isChatLoading && (
                    <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-cyan-400 flex items-center gap-2 font-mono">
                      <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
                      <span>Synthesizing grounded spatial answer...</span>
                    </div>
                  )}
                </div>

                {chatError && (
                  <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-300">
                    {chatError}
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2 pt-2 border-t border-slate-800/60">
                <input
                  type="text"
                  placeholder="e.g. Is this location inside an industrial zone?"
                  value={chatQuery}
                  disabled={isChatLoading}
                  onChange={(e) => setChatQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleChat();
                  }}
                  className="flex-1 px-3 py-2 rounded-lg bg-slate-900/90 border border-slate-700 text-white text-xs focus:outline-none focus:border-cyan-500"
                />
                <button
                  type="button"
                  onClick={() => handleChat()}
                  disabled={isChatLoading || !chatQuery.trim()}
                  className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  {isChatLoading ? (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : (
                    <>
                      <Send className="h-3.5 w-3.5" />
                      <span>Ask</span>
                    </>
                  )}
                </button>
              </div>

            </div>

          </div>

        </div>
      )}

    </div>
  );
};

export default AssistantPage;
