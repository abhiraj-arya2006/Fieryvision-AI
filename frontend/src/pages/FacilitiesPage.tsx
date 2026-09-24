import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useFacilities } from '../hooks/useFacilities';
import { Factory, Search, MapPin, ExternalLink, ShieldCheck, RefreshCw, AlertCircle } from 'lucide-react';
import { GIASPURA_CENTER } from '../components/MapView';

// Haversine calculation helper
function calculateDistanceMeters(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371000;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

export const FacilitiesPage: React.FC = () => {
  const { data, loading, error, refresh } = useFacilities();
  const [search, setSearch] = useState<string>('');
  const navigate = useNavigate();

  const facilities = data?.facilities || [];

  const filtered = useMemo(() => {
    if (!search.trim()) return facilities;
    const q = search.toLowerCase();
    return facilities.filter(
      (f) =>
        f.name.toLowerCase().includes(q) ||
        f.site_type.toLowerCase().includes(q) ||
        (f.address && f.address.toLowerCase().includes(q)) ||
        f.id.toLowerCase().includes(q)
    );
  }, [facilities, search]);

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-6">
      
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
              <Factory className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                Industrial Facilities Directory
              </h1>
              <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
                Critical industrial plants, manufacturing units, and boiler facilities monitored across Giaspura, Ludhiana.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={refresh}
          disabled={loading}
          className="px-3.5 py-1.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-xs font-semibold text-slate-200 flex items-center gap-1.5 transition-colors"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh List</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-3 text-red-200 text-xs">
          <AlertCircle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-red-300">Facilities Unavailable</h4>
            <p className="mt-0.5 text-red-300/80">{error}</p>
          </div>
        </div>
      )}

      {/* Search & Counter Bar */}
      <div className="glass-panel p-4 rounded-xl flex flex-wrap items-center justify-between gap-3">
        <div className="relative flex-1 min-w-[240px] max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search facility by name, type, or address..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-700/80 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div className="text-xs font-mono text-slate-400">
          Showing <span className="text-cyan-300 font-semibold">{filtered.length}</span> of {facilities.length} industrial sites
        </div>
      </div>

      {/* Facilities Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((facility) => {
          const distFromCenter = calculateDistanceMeters(
            GIASPURA_CENTER[0],
            GIASPURA_CENTER[1],
            facility.latitude,
            facility.longitude
          );

          return (
            <div
              key={facility.id}
              className="glass-panel p-5 rounded-2xl border border-slate-800 hover:border-cyan-500/40 transition-all flex flex-col justify-between space-y-4 group"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-[11px] font-bold text-cyan-400">
                    {facility.id}
                  </span>
                  <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-semibold text-emerald-300">
                    <ShieldCheck className="h-3 w-3" />
                    <span>{facility.operating_status.toUpperCase()}</span>
                  </span>
                </div>

                <h3 className="font-bold text-base text-white group-hover:text-cyan-200 transition-colors leading-snug">
                  {facility.name}
                </h3>

                <p className="text-xs text-cyan-300/80 font-medium mt-1">
                  {facility.site_type}
                </p>

                {facility.address && (
                  <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                    {facility.address}
                  </p>
                )}
              </div>

              <div className="pt-3 border-t border-slate-800/80 space-y-3">
                <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                  <span>Coordinates:</span>
                  <span className="text-white">
                    {facility.latitude.toFixed(5)}°N, {facility.longitude.toFixed(5)}°E
                  </span>
                </div>

                <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                  <span>From Giaspura Center:</span>
                  <span className="text-cyan-300">
                    {(distFromCenter / 1000).toFixed(2)} km
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-1">
                  <button
                    onClick={() => navigate(`/?lat=${facility.latitude}&lon=${facility.longitude}`)}
                    className="py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors border border-slate-700"
                  >
                    <MapPin className="h-3 w-3 text-cyan-400" />
                    <span>View on Map</span>
                  </button>

                  <button
                    onClick={() => navigate(`/assistant?lat=${facility.latitude}&lon=${facility.longitude}`)}
                    className="py-1.5 rounded-lg bg-cyan-600/90 hover:bg-cyan-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-sm shadow-cyan-600/20"
                  >
                    <span>Investigate</span>
                    <ExternalLink className="h-3 w-3" />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
};

export default FacilitiesPage;
