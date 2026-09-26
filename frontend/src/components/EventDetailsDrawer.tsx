import React from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  X, 
  Flame, 
  Clock, 
  Cpu, 
  Factory, 
  Satellite, 
  CheckCircle2, 
  ArrowRight
} from 'lucide-react';
import type { CanonicalEvent } from '../types';
import { getClassificationColor, getPriorityColor, formatDistance, formatDateTime } from '../utils/formatters';

interface EventDetailsDrawerProps {
  event: CanonicalEvent | null;
  isOpen: boolean;
  onClose: () => void;
  onOpenSatelliteContext: (eventId: string) => void;
}

export const EventDetailsDrawer: React.FC<EventDetailsDrawerProps> = ({
  event,
  isOpen,
  onClose,
  onOpenSatelliteContext,
}) => {
  const navigate = useNavigate();

  if (!isOpen || !event) return null;

  const colorType = getClassificationColor(event.classification);
  const priorityStyle = getPriorityColor(event.priority);
  const isAnomaly = Boolean(event.is_anomaly || event.anomaly_flag);

  const handleNavigateToAnalysis = () => {
    navigate(`/assistant?lat=${event.latitude}&lon=${event.longitude}`);
  };

  return (
    <aside 
      className="fixed inset-y-0 right-0 z-[9999] w-full sm:w-[480px] glass-panel border-l border-cyan-500/30 shadow-2xl flex flex-col animate-in slide-in-from-right duration-300 bg-[#080f1c]/95"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700/60 bg-slate-900/60">
        <div className="flex items-center gap-2.5">
          <div className={`p-2 rounded-lg bg-${colorType === 'red' ? 'red-500/20 text-red-400' : colorType === 'orange' ? 'orange-500/20 text-orange-400' : 'cyan-500/20 text-cyan-400'}`}>
            <Flame className="h-5 w-5" />
          </div>
          <div>
            <div className="text-[11px] font-mono text-cyan-400 uppercase tracking-wider">
              {event.event_id}
            </div>
            <h2 className="text-base font-bold text-white leading-tight">
              {event.classification || 'Thermal Anomaly'}
            </h2>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 text-xs">
        
        {/* Risk Score & Priority Gauge */}
        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 font-medium">Risk Priority</span>
            <span className={`px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider text-[11px] border ${priorityStyle.bg} ${priorityStyle.text} ${priorityStyle.border}`}>
              {event.priority || 'LOW'} PRIORITY
            </span>
          </div>

          <div className="flex items-end justify-between">
            <div>
              <span className="text-2xl font-bold font-mono text-white">
                {event.risk_score != null ? event.risk_score : 0}
              </span>
              <span className="text-slate-400 text-xs ml-1">/ 100</span>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">
              Method: {event.classification_method || 'evidence_based'}
            </span>
          </div>

          {/* Progress bar */}
          <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 ${
                event.risk_score >= 70 ? 'bg-red-500' : event.risk_score >= 40 ? 'bg-orange-500' : 'bg-cyan-500'
              }`}
              style={{ width: `${Math.min(100, Math.max(5, event.risk_score || 0))}%` }}
            />
          </div>
        </div>

        {/* ML Anomaly Status Box */}
        <div className={`p-3 rounded-xl border flex items-start gap-3 ${
          isAnomaly 
            ? 'bg-red-500/10 border-red-500/30 text-red-300' 
            : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
        }`}>
          <Cpu className="h-5 w-5 mt-0.5 shrink-0" />
          <div className="space-y-0.5 flex-1">
            <div className="font-semibold text-xs flex items-center justify-between">
              <span>{isAnomaly ? 'ML Isolation Forest: OUTLIER ANOMALY' : 'ML Model: Normal Thermal Pattern'}</span>
              <span className="font-mono text-[11px] font-bold">
                {event.anomaly_score != null ? `${event.anomaly_score} / 1.0` : '0.00'}
              </span>
            </div>
            <p className="text-[11px] opacity-80 leading-relaxed">
              {isAnomaly 
                ? 'High-confidence thermal signature deviating significantly from standard background signatures.'
                : 'Consistent with baseline seasonal or background thermal characteristics.'}
            </p>
          </div>
        </div>

        {/* Core Telemetry Details Table */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
          <div className="px-3.5 py-2 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-cyan-400" />
            <span>Detection Telemetry</span>
          </div>
          
          <div className="divide-y divide-slate-800/80">
            <div className="px-3.5 py-2 flex items-center justify-between">
              <span className="text-slate-400">Coordinates</span>
              <span className="font-mono text-white font-medium">
                {event.latitude.toFixed(5)}°N, {event.longitude.toFixed(5)}°E
              </span>
            </div>

            <div className="px-3.5 py-2 flex items-center justify-between">
              <span className="text-slate-400">Detection Time</span>
              <span className="font-mono text-white">
                {formatDateTime(event.acq_date, event.acq_time)}
              </span>
            </div>

            <div className="px-3.5 py-2 flex items-center justify-between">
              <span className="text-slate-400">Fire Radiative Power (FRP)</span>
              <span className="font-mono text-cyan-300 font-semibold">
                {event.frp != null ? `${event.frp} MW` : 'N/A'}
              </span>
            </div>

            <div className="px-3.5 py-2 flex items-center justify-between">
              <span className="text-slate-400">Brightness Temperature</span>
              <span className="font-mono text-white">
                {event.brightness != null ? `${event.brightness} K` : 'N/A'}
              </span>
            </div>

            <div className="px-3.5 py-2 flex items-center justify-between">
              <span className="text-slate-400">Satellite Platform</span>
              <span className="font-mono text-white">
                {event.satellite || 'VIIRS / NOAA'}
              </span>
            </div>

            <div className="px-3.5 py-2 flex items-center justify-between">
              <span className="text-slate-400">Confidence</span>
              <span className="font-mono text-white capitalize">
                {event.confidence || 'Nominal'}
              </span>
            </div>
          </div>
        </div>

        {/* Industrial & Geospatial Context */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
          <div className="px-3.5 py-2 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Factory className="h-3.5 w-3.5 text-cyan-400" />
            <span>Industrial & Land Context</span>
          </div>

          <div className="divide-y divide-slate-800/80">
            <div className="px-3.5 py-2 flex items-center justify-between">
              <span className="text-slate-400">Nearest Facility</span>
              <span className="text-white font-medium text-right max-w-[200px] truncate" title={event.nearest_facility_name || 'None'}>
                {event.nearest_facility_name || 'None within 15km'}
              </span>
            </div>

            {event.nearest_facility_type && (
              <div className="px-3.5 py-2 flex items-center justify-between">
                <span className="text-slate-400">Facility Type</span>
                <span className="text-slate-300 text-right">{event.nearest_facility_type}</span>
              </div>
            )}

            <div className="px-3.5 py-2 flex items-center justify-between">
              <span className="text-slate-400">Distance to Facility</span>
              <span className="font-mono text-cyan-300">
                {formatDistance(event.distance_to_facility_m)}
              </span>
            </div>

            <div className="px-3.5 py-2 flex items-center justify-between">
              <span className="text-slate-400">Inside Industrial Zone</span>
              <span className={`font-semibold ${event.inside_industrial_zone ? 'text-emerald-400' : 'text-slate-400'}`}>
                {event.inside_industrial_zone ? 'Yes (Giaspura Zone)' : 'No'}
              </span>
            </div>

            <div className="px-3.5 py-2 flex items-center justify-between">
              <span className="text-slate-400">Land Cover</span>
              <span className="text-slate-300 font-medium">{event.landcover || 'Built-up / Industrial'}</span>
            </div>

            <div className="px-3.5 py-2 flex items-center justify-between">
              <span className="text-slate-400">Persistence Classification</span>
              <span className="text-white capitalize">{event.persistence || 'Transient'}</span>
            </div>

            <div className="px-3.5 py-2 flex items-center justify-between">
              <span className="text-slate-400">Detections (7d / 30d)</span>
              <span className="font-mono text-white">
                {event.detections_7d} / {event.detections_30d}
              </span>
            </div>
          </div>
        </div>

        {/* Evidence Section */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 space-y-2">
          <div className="text-[11px] font-semibold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>Why was this event flagged?</span>
          </div>

          {event.evidence && event.evidence.length > 0 ? (
            <ul className="space-y-1.5 pl-1">
              {event.evidence.map((item, idx) => (
                <li key={idx} className="flex items-start gap-2 text-slate-300 text-xs">
                  <span className="text-cyan-400 font-bold">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500 text-xs">No specific evidence points recorded for this thermal event.</p>
          )}
        </div>

        {/* AI Explanation if available */}
        {event.explanation && (
          <div className="rounded-xl border border-cyan-500/25 bg-cyan-950/20 p-3.5 space-y-1.5">
            <span className="text-[10px] font-bold tracking-wider text-cyan-300 uppercase block">
              AI INTELLIGENCE SUMMARY
            </span>
            <p className="text-slate-300 text-xs leading-relaxed">
              {event.explanation}
            </p>
          </div>
        )}

      </div>

      {/* Action Footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/80 space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => onOpenSatelliteContext(event.event_id)}
            className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
          >
            <Satellite className="h-3.5 w-3.5 text-cyan-400" />
            <span>Satellite Context</span>
          </button>

          <button
            onClick={handleNavigateToAnalysis}
            className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-md shadow-cyan-600/20 transition-colors"
          >
            <span>AI Investigation</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

    </aside>
  );
};

export default EventDetailsDrawer;
