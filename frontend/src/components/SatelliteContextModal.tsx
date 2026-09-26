import React, { useEffect, useState } from 'react';
import { X, Satellite, Layers, Calendar, Clock, Crosshair, CheckCircle2, AlertCircle } from 'lucide-react';
import api from '../services/api';
import type { SatelliteContextResponse } from '../types';

interface SatelliteContextModalProps {
  eventId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export const SatelliteContextModal: React.FC<SatelliteContextModalProps> = ({
  eventId,
  isOpen,
  onClose,
}) => {
  const [data, setData] = useState<SatelliteContextResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !eventId) {
      setData(null);
      setError(null);
      return;
    }

    let isMounted = true;
    const fetchContext = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.getSatelliteContext(eventId);
        if (isMounted) setData(res);
      } catch (err: any) {
        if (isMounted) setError(err?.message || 'Failed to retrieve satellite context.');
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchContext();

    return () => {
      isMounted = false;
    };
  }, [isOpen, eventId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="glass-panel w-full max-w-lg rounded-2xl overflow-hidden shadow-2xl border border-cyan-500/30 text-slate-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700/50 bg-slate-900/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-cyan-500/15 text-cyan-400 border border-cyan-500/25">
              <Satellite className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-base">Satellite Context Imagery</h3>
              <p className="text-xs text-slate-400 font-mono">Event: {eventId}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-5 space-y-4 max-h-[75vh] overflow-y-auto">
          {loading && (
            <div className="py-12 flex flex-col items-center justify-center gap-3">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent"></div>
              <p className="text-xs text-slate-400">Querying satellite telemetry metadata...</p>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-red-300">Retrieval Failed</h4>
                <p className="text-xs text-red-300/80 mt-1">{error}</p>
              </div>
            </div>
          )}

          {data && !loading && (
            <div className="space-y-4">
              
              {/* Status Banner */}
              <div className={`p-3 rounded-xl border flex items-center justify-between text-xs ${
                data.status === 'available'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                  : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
              }`}>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  <span className="font-semibold uppercase tracking-wider">Status: {data.status}</span>
                </div>
                <span className="font-mono text-[11px] opacity-80">{data.provider || 'NASA FIRMS / MODIS / VIIRS'}</span>
              </div>

              {/* Telemetry Grid */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center gap-1.5 text-slate-400 mb-1">
                    <Satellite className="h-3.5 w-3.5 text-cyan-400" />
                    <span>Satellite Platform</span>
                  </div>
                  <div className="text-sm font-semibold text-white font-mono">{data.satellite || 'NOAA-20 / VIIRS'}</div>
                </div>

                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center gap-1.5 text-slate-400 mb-1">
                    <Crosshair className="h-3.5 w-3.5 text-cyan-400" />
                    <span>Spatial Resolution</span>
                  </div>
                  <div className="text-sm font-semibold text-white font-mono">
                    {data.resolution_m ? `${data.resolution_m} meters` : '375m I-Band'}
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center gap-1.5 text-slate-400 mb-1">
                    <Calendar className="h-3.5 w-3.5 text-cyan-400" />
                    <span>Acquisition Date</span>
                  </div>
                  <div className="text-sm font-semibold text-white font-mono">{data.acquisition_date || 'N/A'}</div>
                </div>

                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center gap-1.5 text-slate-400 mb-1">
                    <Clock className="h-3.5 w-3.5 text-cyan-400" />
                    <span>Acquisition Time</span>
                  </div>
                  <div className="text-sm font-semibold text-white font-mono">{data.acquisition_time || 'N/A'}</div>
                </div>
              </div>

              {/* Spectral Bands */}
              {data.bands_available && data.bands_available.length > 0 && (
                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center gap-1.5 text-slate-400 mb-2 text-xs">
                    <Layers className="h-3.5 w-3.5 text-cyan-400" />
                    <span>Spectral Bands Available</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {data.bands_available.map((band, idx) => (
                      <span key={idx} className="px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/40 text-[11px] font-mono text-cyan-300">
                        {band}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Operational Message */}
              <div className="p-3.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs text-slate-300 leading-relaxed">
                <span className="font-semibold text-cyan-300 block mb-1">Satellite Context Verification:</span>
                {data.message}
              </div>

            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold transition-colors"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
};

export default SatelliteContextModal;
