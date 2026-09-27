import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useFacilities } from '../hooks/useFacilities';
import { Factory, Search, MapPin, ExternalLink, ShieldCheck, RefreshCw, AlertCircle, Globe, Flame, Building2 } from 'lucide-react';


const REGION_FILTERS = [
  { id: 'all', label: 'All Global Sites' },
  { id: 'Asia', label: 'Asia' },
  { id: 'North America', label: 'North America' },
  { id: 'Europe', label: 'Europe' },
  { id: 'South America', label: 'South America' },
  { id: 'Africa', label: 'Africa' },
  { id: 'Oceania_MiddleEast', label: 'Middle East & Oceania' },
];

export const FacilitiesPage: React.FC = () => {
  const { data, loading, error, refresh } = useFacilities();
  const [search, setSearch] = useState<string>('');
  const [selectedRegion, setSelectedRegion] = useState<string>('all');
  const navigate = useNavigate();

  const facilities = data?.facilities || [];

  const filtered = useMemo(() => {
    let result = facilities;

    // Filter by Region
    if (selectedRegion === 'Oceania_MiddleEast') {
      result = result.filter(
        (f) =>
          f.continent === 'Oceania' ||
          f.continent === 'Middle East' ||
          f.continent === 'Southeast Asia' ||
          f.id.startsWith('HS-MEA') ||
          f.id.startsWith('HS-AUS') ||
          f.id.startsWith('HS-SEA')
      );
    } else if (selectedRegion !== 'all') {
      result = result.filter((f) => f.continent === selectedRegion);
    }

    // Filter by Search Query
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (f) =>
          f.name.toLowerCase().includes(q) ||
          f.site_type.toLowerCase().includes(q) ||
          (f.address && f.address.toLowerCase().includes(q)) ||
          (f.country && f.country.toLowerCase().includes(q)) ||
          (f.continent && f.continent.toLowerCase().includes(q)) ||
          f.id.toLowerCase().includes(q)
      );
    }

    return result;
  }, [facilities, selectedRegion, search]);

  return (
    <div className="flex-1 p-3 sm:p-5 lg:p-6 w-full space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
              <Factory className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                Global Monitored Facilities & Hotspot Directory
              </h1>
              <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
                Industrial plants, thermal complexes, and active hotspots monitored across global regions.
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
          <span>Refresh Directory</span>
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

      {/* Region Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-thin">
        {REGION_FILTERS.map((tab) => {
          const isActive = selectedRegion === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setSelectedRegion(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all border ${
                isActive
                  ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 shadow-sm shadow-cyan-500/10'
                  : 'bg-slate-900/80 text-slate-400 border-slate-800 hover:bg-slate-800 hover:text-slate-200'
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Search & Counter Bar */}
      <div className="glass-panel p-4 rounded-xl flex flex-wrap items-center justify-between gap-3">
        <div className="relative flex-1 min-w-[240px] max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by facility name, country, type, or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-700/80 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div className="text-xs font-mono text-slate-400 flex items-center gap-2">
          <span className="flex items-center gap-1">
            <Globe className="h-3.5 w-3.5 text-cyan-400" />
            Showing <span className="text-cyan-300 font-semibold">{filtered.length}</span> of {facilities.length} active sites
          </span>
        </div>
      </div>

      {/* Facilities Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((facility) => {
          const isHotspot = facility.id.startsWith('HS-');

          return (
            <div
              key={facility.id}
              className="glass-panel p-5 rounded-2xl border border-slate-800 hover:border-cyan-500/40 transition-all flex flex-col justify-between space-y-4 group"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-[11px] font-bold text-cyan-400">
                      {facility.id}
                    </span>
                    {facility.country && (
                      <span className="px-2 py-0.5 rounded-full bg-slate-800 text-[10px] font-mono text-slate-300 border border-slate-700">
                        {facility.country}
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-1.5">
                    {facility.risk_tier && (
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                          facility.risk_tier === 'critical'
                            ? 'bg-purple-500/20 text-purple-300 border-purple-500/30'
                            : facility.risk_tier === 'high'
                            ? 'bg-red-500/20 text-red-300 border-red-500/30'
                            : facility.risk_tier === 'moderate'
                            ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                            : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                        }`}
                      >
                        {facility.risk_tier}
                      </span>
                    )}
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-semibold text-emerald-300">
                      <ShieldCheck className="h-3 w-3" />
                      <span>{facility.operating_status.toUpperCase()}</span>
                    </span>
                  </div>
                </div>

                <div className="flex items-start gap-2">
                  {isHotspot ? (
                    <Flame className="h-4 w-4 text-amber-400 shrink-0 mt-1" />
                  ) : (
                    <Building2 className="h-4 w-4 text-cyan-400 shrink-0 mt-1" />
                  )}
                  <div>
                    <h3 className="font-bold text-base text-white group-hover:text-cyan-200 transition-colors leading-snug">
                      {facility.name}
                    </h3>
                    <p className="text-xs text-cyan-300/80 font-medium mt-0.5">
                      {facility.site_type}
                    </p>
                  </div>
                </div>

                {facility.address && (
                  <p className="text-xs text-slate-400 mt-2 leading-relaxed pl-6">
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
                  <span>Location Context:</span>
                  <span className="text-slate-300">
                    {facility.continent || 'Global'} ({facility.country || 'International'})
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 pt-1">
                  <button
                    onClick={() => navigate(`/?lat=${facility.latitude}&lon=${facility.longitude}`)}
                    className="py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center justify-center gap-1 transition-colors border border-slate-700"
                    title="View on Global Map"
                  >
                    <MapPin className="h-3 w-3 text-cyan-400" />
                    <span>Map</span>
                  </button>

                  <button
                    onClick={() => navigate(`/hotspots?search=${encodeURIComponent(facility.name)}`)}
                    className="py-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 text-xs font-semibold flex items-center justify-center gap-1 transition-colors border border-amber-500/30"
                    title="View Hotspot Intelligence & FIRMS Telemetry"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                    <span>Hotspot</span>
                  </button>

                  <button
                    onClick={() => navigate(`/assistant?lat=${facility.latitude}&lon=${facility.longitude}`)}
                    className="py-1.5 rounded-lg bg-cyan-600/90 hover:bg-cyan-500 text-white text-xs font-semibold flex items-center justify-center gap-1 transition-colors shadow-sm shadow-cyan-600/20"
                    title="Run AI Investigation"
                  >
                    <span>AI Intel</span>
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
