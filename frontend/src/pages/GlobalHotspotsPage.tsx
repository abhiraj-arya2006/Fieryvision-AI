import React, { useState, useEffect, useMemo } from 'react';
import { 
  MapContainer, 
  TileLayer, 
  Marker, 
  Popup, 
  Tooltip, 
  Rectangle, 
  useMap 
} from 'react-leaflet';
import L from 'leaflet';
import { 
  Globe, 
  Flame, 
  ShieldAlert, 
  RefreshCw, 
  Layers, 
  Compass, 
  ChevronRight,
  Search,
  Wind,
  Shield
} from 'lucide-react';
import { api } from '../services/api';
import type { 
  HotspotSummary, 
  HotspotAnalytics, 
  HotspotAlert, 
  HotspotFilterState,
  WindData,
  PlumeConeResponse,
  EmergencyContextResponse
} from '../types';
import { HotspotDetailDrawer } from '../components/HotspotDetailDrawer';
import { IncidentMapLayers } from '../components/IncidentMapLayers';

// Preset view centers for major continents & regions
const PRESET_REGIONS: Record<string, { center: [number, number]; zoom: number; name: string; flag: string }> = {
  ALL: { center: [20.0, 0.0], zoom: 2, name: 'Global World View', flag: '🌍' },
  USA: { center: [38.5, -98.0], zoom: 4, name: 'North America (USA)', flag: '🇺🇸' },
  EUROPE: { center: [45.0, 15.0], zoom: 4, name: 'Europe', flag: '🇪🇺' },
  INDIA: { center: [23.5, 78.5], zoom: 5, name: 'India', flag: '🇮🇳' },
  SOUTH_AMERICA: { center: [-15.0, -60.0], zoom: 4, name: 'South America', flag: '🌎' },
  AFRICA: { center: [0.0, 20.0], zoom: 3, name: 'Africa', flag: '🌍' },
  OCEANIA: { center: [-25.0, 135.0], zoom: 4, name: 'Australia & Oceania', flag: '🇦🇺' },
  ASIA: { center: [15.0, 100.0], zoom: 4, name: 'Southeast Asia', flag: '🌏' },
};

function MapController({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
}

// Custom Hotspot Marker Icon Builder
function createHotspotIcon(classification: string, riskTier: string, isSelected: boolean = false) {
  let colorClass = 'marker-industrial';
  let badgeIcon = '🔥';

  if (classification.includes('EMERGING')) {
    colorClass = 'marker-emerging';
    badgeIcon = '⚡';
  } else if (classification.includes('HIGH-INTENSITY') || riskTier === 'CRITICAL') {
    colorClass = 'marker-high-risk';
    badgeIcon = '🚨';
  } else if (classification.includes('PERSISTENT')) {
    colorClass = 'marker-persistent';
    badgeIcon = '⏳';
  } else if (classification.includes('LARGE-AREA')) {
    colorClass = 'marker-large-area';
    badgeIcon = '🌐';
  } else if (classification.includes('WILDFIRE')) {
    colorClass = 'marker-wildfire';
    badgeIcon = '🌲';
  } else if (classification.includes('INDUSTRIAL')) {
    colorClass = 'marker-industrial';
    badgeIcon = '🏭';
  }

  return L.divIcon({
    className: 'fv-hotspot-marker',
    html: `
      <div class="fv-hotspot-beacon ${colorClass} ${isSelected ? 'is-selected scale-125' : ''}">
        <div class="beacon-pulse"></div>
        <div class="beacon-core">
          <span>${badgeIcon}</span>
        </div>
      </div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -18],
  });
}

export const GlobalHotspotsPage: React.FC = () => {
  const [hotspots, setHotspots] = useState<HotspotSummary[]>([]);
  const [analytics, setAnalytics] = useState<HotspotAnalytics | null>(null);
  const [alerts, setAlerts] = useState<HotspotAlert[]>([]);
  const [selectedHotspot, setSelectedHotspot] = useState<HotspotSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Incident & Weather / Emergency State
  const [incidentMode, setIncidentMode] = useState<boolean>(false);
  const [windData, setWindData] = useState<WindData | null>(null);
  const [plumeData, setPlumeData] = useState<PlumeConeResponse | null>(null);
  const [emergencyData, setEmergencyData] = useState<EmergencyContextResponse | null>(null);

  // Map layer visibility toggles
  const [showWindVector, setShowWindVector] = useState<boolean>(true);
  const [showPlumeCone, setShowPlumeCone] = useState<boolean>(true);
  const visiblePlumeHorizons = [1, 3, 6, 12];
  const [showBuffer1km, setShowBuffer1km] = useState<boolean>(true);
  const [showBuffer3km, setShowBuffer3km] = useState<boolean>(true);
  const [showEmergencyLayer, setShowEmergencyLayer] = useState<boolean>(true);

  // Map state
  const [activeRegion, setActiveRegion] = useState<string>('ALL');
  const [mapTarget, setMapTarget] = useState<{ center: [number, number]; zoom: number }>({
    center: PRESET_REGIONS.ALL.center,
    zoom: PRESET_REGIONS.ALL.zoom,
  });
  const [tileMode, setTileMode] = useState<'dark' | 'satellite' | 'street'>('dark');
  const [showPolygons, setShowPolygons] = useState<boolean>(true);
  const [showLegend, setShowLegend] = useState<boolean>(true);

  // Filters
  const [filters, setFilters] = useState<HotspotFilterState>({
    continent: 'all',
    country: 'all',
    classification: 'all',
    riskTier: 'all',
    status: 'all',
    minRisk: 0,
    sortBy: 'risk_score',
    order: 'desc',
    search: '',
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [listRes, statsRes, alertsRes] = await Promise.all([
        api.getHotspots({
          continent: filters.continent,
          country: filters.country,
          classification: filters.classification,
          risk_tier: filters.riskTier,
          status: filters.status,
          min_risk: filters.minRisk > 0 ? filters.minRisk : undefined,
          sort_by: filters.sortBy,
          order: filters.order,
          page_size: 100,
        }),
        api.getHotspotAnalytics(),
        api.getHotspotAlerts(),
      ]);

      setHotspots(listRes.items || []);
      setAnalytics(statsRes);
      setAlerts(alertsRes || []);
    } catch (err) {
      console.error('Error loading global hotspot intelligence:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [filters.continent, filters.country, filters.classification, filters.riskTier, filters.status, filters.minRisk, filters.sortBy, filters.order]);

  // Load telemetry when a hotspot is selected
  useEffect(() => {
    if (!selectedHotspot) {
      setWindData(null);
      setPlumeData(null);
      setEmergencyData(null);
      return;
    }

    Promise.all([
      api.getHotspotWind(selectedHotspot.id).catch(() => null),
      api.getHotspotPlume(selectedHotspot.id).catch(() => null),
      api.getHotspotEmergencyContext(selectedHotspot.id).catch(() => null),
    ]).then(([w, p, em]) => {
      setWindData(w);
      setPlumeData(p);
      setEmergencyData(em);
    });
  }, [selectedHotspot?.id]);

  const handleRegionSelect = (key: string) => {
    setActiveRegion(key);
    const preset = PRESET_REGIONS[key];
    if (preset) {
      setMapTarget({ center: preset.center, zoom: preset.zoom });
      if (key === 'USA') {
        setFilters((prev) => ({ ...prev, continent: 'North America', country: 'all' }));
      } else if (key === 'EUROPE') {
        setFilters((prev) => ({ ...prev, continent: 'Europe', country: 'all' }));
      } else if (key === 'INDIA') {
        setFilters((prev) => ({ ...prev, continent: 'all', country: 'India' }));
      } else if (key === 'SOUTH_AMERICA') {
        setFilters((prev) => ({ ...prev, continent: 'South America', country: 'all' }));
      } else if (key === 'AFRICA') {
        setFilters((prev) => ({ ...prev, continent: 'Africa', country: 'all' }));
      } else if (key === 'OCEANIA') {
        setFilters((prev) => ({ ...prev, continent: 'Oceania', country: 'all' }));
      } else if (key === 'ASIA') {
        setFilters((prev) => ({ ...prev, continent: 'Asia', country: 'all' }));
      } else {
        setFilters((prev) => ({ ...prev, continent: 'all', country: 'all' }));
      }
    }
  };

  const handleFocusHotspot = (lat: number, lon: number) => {
    setMapTarget({ center: [lat, lon], zoom: incidentMode ? 13 : 11 });
  };

  const handleToggleIncidentMode = () => {
    const next = !incidentMode;
    setIncidentMode(next);
    if (next && selectedHotspot) {
      setMapTarget({ center: [selectedHotspot.centroid_lat, selectedHotspot.centroid_lon], zoom: 13 });
    }
  };

  const filteredHotspots = useMemo(() => {
    if (!filters.search.trim()) return hotspots;
    const q = filters.search.toLowerCase().trim();
    return hotspots.filter((h) => 
      h.name.toLowerCase().includes(q) ||
      h.country.toLowerCase().includes(q) ||
      h.classification.toLowerCase().includes(q) ||
      h.id.toLowerCase().includes(q) ||
      (h.nearest_city && h.nearest_city.toLowerCase().includes(q))
    );
  }, [hotspots, filters.search]);

  const tileUrls = {
    dark: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    satellite: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    street: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  };

  return (
    <div className="flex-1 flex flex-col p-3 sm:p-5 lg:p-6 w-full space-y-4">
      
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Globe className="h-6 w-6 text-cyan-400" />
              <span>Global Hotspot & Incident Response Console</span>
            </h1>
            <span className="px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 text-xs font-mono font-medium">
              Worldwide Telemetry
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            Geographically clustered thermal anomalies with Open-Meteo wind vectors, predictive downwind plume screening, and OpenStreetMap emergency response assets.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchData}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg border border-cyan-500/30 bg-cyan-950/40 hover:bg-cyan-900/60 text-xs font-semibold text-cyan-300 flex items-center gap-1.5 transition-colors shadow-sm shadow-cyan-500/10"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Sync Hotspots</span>
          </button>
        </div>
      </div>

      {/* Global Analytics Overview Cards */}
      {analytics && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="glass-panel p-3 rounded-xl border border-slate-800 bg-slate-900/60">
            <div className="text-[10px] font-bold text-slate-400 uppercase">Active Hotspots</div>
            <div className="text-xl font-bold text-white font-mono mt-1">{analytics.total_active_hotspots}</div>
            <div className="text-[10px] text-cyan-400 mt-0.5">Global clusters</div>
          </div>

          <div className="glass-panel p-3 rounded-xl border border-slate-800 bg-slate-900/60">
            <div className="text-[10px] font-bold text-amber-400 uppercase">Emerging</div>
            <div className="text-xl font-bold text-amber-300 font-mono mt-1">{analytics.emerging_hotspots_count}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Rapid surge alerts</div>
          </div>

          <div className="glass-panel p-3 rounded-xl border border-slate-800 bg-slate-900/60">
            <div className="text-[10px] font-bold text-orange-400 uppercase">Persistent</div>
            <div className="text-xl font-bold text-orange-300 font-mono mt-1">{analytics.persistent_hotspots_count}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Multi-pass thermal</div>
          </div>

          <div className="glass-panel p-3 rounded-xl border border-slate-800 bg-slate-900/60">
            <div className="text-[10px] font-bold text-red-400 uppercase">High-Intensity</div>
            <div className="text-xl font-bold text-red-400 font-mono mt-1">{analytics.high_intensity_hotspots_count}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Peak FRP &gt; 250MW</div>
          </div>

          <div className="glass-panel p-3 rounded-xl border border-slate-800 bg-slate-900/60">
            <div className="text-[10px] font-bold text-rose-400 uppercase">High / Critical Risk</div>
            <div className="text-xl font-bold text-rose-300 font-mono mt-1">{analytics.high_risk_hotspots_count}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Composite score &ge;70</div>
          </div>

          <div className="glass-panel p-3 rounded-xl border border-slate-800 bg-slate-900/60">
            <div className="text-[10px] font-bold text-emerald-400 uppercase">New in 24h</div>
            <div className="text-xl font-bold text-emerald-300 font-mono mt-1">{analytics.new_in_last_24h_count}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Recent formations</div>
          </div>
        </div>
      )}

      {/* Real-time Alert Banner */}
      {alerts.length > 0 && (
        <div className="p-3.5 rounded-xl bg-gradient-to-r from-red-950/60 via-slate-900/80 to-slate-900/60 border border-red-500/40 flex items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2.5">
            <span className="p-1.5 rounded-lg bg-red-500/20 text-red-400 border border-red-500/30">
              <ShieldAlert className="h-4 w-4" />
            </span>
            <div>
              <span className="font-bold text-red-300 mr-2 uppercase tracking-wider">
                [{alerts[0].alert_type}] {alerts[0].hotspot_name}:
              </span>
              <span className="text-slate-300">{alerts[0].message}</span>
            </div>
          </div>

          <button
            onClick={() => {
              const target = hotspots.find(h => h.id === alerts[0].hotspot_id);
              if (target) {
                setSelectedHotspot(target);
                handleFocusHotspot(target.centroid_lat, target.centroid_lon);
              }
            }}
            className="shrink-0 px-3 py-1 rounded bg-red-600 hover:bg-red-500 text-white font-semibold text-[11px] transition-colors"
          >
            Investigate Hotspot →
          </button>
        </div>
      )}

      {/* Continent / Region Quick Filter Bar */}
      <div className="glass-panel p-2 rounded-xl flex items-center gap-1.5 overflow-x-auto text-xs">
        <span className="text-slate-400 text-[11px] font-bold px-2 uppercase tracking-wider shrink-0 flex items-center gap-1">
          <Compass className="h-3.5 w-3.5 text-cyan-400" />
          <span>Continent Presets:</span>
        </span>
        {Object.entries(PRESET_REGIONS).map(([key, region]) => (
          <button
            key={key}
            onClick={() => handleRegionSelect(key)}
            className={`px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-all flex items-center gap-1.5 ${
              activeRegion === key
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold shadow-sm shadow-cyan-500/10'
                : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
            }`}
          >
            <span>{region.flag}</span>
            <span>{region.name}</span>
          </button>
        ))}
      </div>

      {/* Main Interactive Map & Split View Container */}
      <div className="grid grid-cols-1 lg:grid-cols-3 xl:grid-cols-4 gap-4 flex-1">
        
        {/* Leaflet Global Hotspot Map View */}
        <div className="lg:col-span-2 xl:col-span-3 min-h-[640px] h-[calc(100vh-320px)] relative rounded-2xl overflow-hidden border border-cyan-500/25 shadow-2xl bg-[#050914]">
          
          {/* Map Layer Controls Overlay */}
          <div className="absolute top-4 left-4 z-[400] flex flex-wrap gap-2 pointer-events-auto">
            {/* Incident Mode Toggle */}
            <button
              onClick={handleToggleIncidentMode}
              className={`px-3 py-1.5 rounded-xl font-bold text-xs flex items-center gap-1.5 transition-all shadow-md ${
                incidentMode
                  ? 'bg-gradient-to-r from-amber-500 to-orange-600 text-slate-950 border border-amber-400 shadow-amber-500/20'
                  : 'glass-panel text-slate-300 hover:text-white border-slate-700'
              }`}
            >
              <Shield className="h-3.5 w-3.5" />
              <span>{incidentMode ? 'Incident Mode Active' : 'Incident Mode'}</span>
            </button>

            {/* Quick Layer Toggles */}
            <div className="glass-panel p-1.5 rounded-xl flex items-center gap-1 text-xs text-slate-300">
              <button
                onClick={() => setShowWindVector(!showWindVector)}
                className={`px-2.5 py-1 rounded-lg transition-colors ${
                  showWindVector ? 'bg-amber-500/20 text-amber-300 font-semibold' : 'text-slate-400 hover:text-white'
                }`}
                title="Toggle Wind Arrow Vector"
              >
                <Wind className="h-3 w-3 inline mr-1" />
                <span>Wind</span>
              </button>

              <button
                onClick={() => setShowPlumeCone(!showPlumeCone)}
                className={`px-2.5 py-1 rounded-lg transition-colors ${
                  showPlumeCone ? 'bg-amber-500/20 text-amber-300 font-semibold' : 'text-slate-400 hover:text-white'
                }`}
                title="Toggle Indicative Plume Cones"
              >
                <Flame className="h-3 w-3 inline mr-1" />
                <span>Plume (1-12h)</span>
              </button>

              <button
                onClick={() => setShowEmergencyLayer(!showEmergencyLayer)}
                className={`px-2.5 py-1 rounded-lg transition-colors ${
                  showEmergencyLayer ? 'bg-red-500/20 text-red-300 font-semibold' : 'text-slate-400 hover:text-white'
                }`}
                title="Toggle Emergency Facilities"
              >
                <span>🚒 Emergency</span>
              </button>

              <button
                onClick={() => setShowPolygons(!showPolygons)}
                className={`px-2.5 py-1 rounded-lg transition-colors ${
                  showPolygons ? 'bg-cyan-500/20 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'
                }`}
                title="Toggle Hotspot Bounding Polygons"
              >
                <Layers className="h-3 w-3 inline mr-1" />
                <span>Extents</span>
              </button>
            </div>

            {/* Basemap Selector */}
            <div className="glass-panel p-1.5 rounded-xl flex items-center gap-1 text-xs text-slate-300">
              <button
                onClick={() => setTileMode('dark')}
                className={`px-2 py-1 rounded-lg transition-colors ${
                  tileMode === 'dark' ? 'bg-cyan-500/25 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'
                }`}
              >
                Dark
              </button>
              <button
                onClick={() => setTileMode('satellite')}
                className={`px-2 py-1 rounded-lg transition-colors ${
                  tileMode === 'satellite' ? 'bg-cyan-500/25 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'
                }`}
              >
                Satellite
              </button>
              <button
                onClick={() => setTileMode('street')}
                className={`px-2 py-1 rounded-lg transition-colors ${
                  tileMode === 'street' ? 'bg-cyan-500/25 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'
                }`}
              >
                Street
              </button>
            </div>
          </div>

          {/* Map Legend Overlay */}
          {showLegend && (
            <div className="absolute bottom-4 left-4 z-[400] glass-panel p-3 rounded-xl text-xs space-y-1.5 hidden md:block max-w-[260px] bg-slate-900/90 border border-slate-800">
              <div className="flex items-center justify-between pb-1 mb-1 border-b border-slate-700/60">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  Incident Map Legend
                </span>
                <button
                  onClick={() => setShowLegend(false)}
                  className="text-[10px] text-slate-400 hover:text-white"
                >
                  Hide
                </button>
              </div>
              <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-red-500"></span>
                  <span className="text-slate-300">Hotspot Beacon</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded bg-amber-400"></span>
                  <span className="text-slate-300">Wind Vector</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded bg-amber-500/50 border border-amber-400"></span>
                  <span className="text-slate-300">Plume Cone (1-12h)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full border border-orange-400"></span>
                  <span className="text-slate-300">1 km Buffer</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full border border-cyan-400"></span>
                  <span className="text-slate-300">3 km Buffer</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span>🚒</span>
                  <span className="text-slate-300">Fire Station</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span>🏥</span>
                  <span className="text-slate-300">Hospital</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span>🩺</span>
                  <span className="text-purple-300">Burn / Trauma</span>
                </div>
              </div>
              <div className="pt-1 border-t border-slate-800 text-[9px] text-slate-500 italic">
                Indicative screening transport only · OpenStreetMap & Open-Meteo
              </div>
            </div>
          )}

          <MapContainer
            center={PRESET_REGIONS.ALL.center}
            zoom={PRESET_REGIONS.ALL.zoom}
            scrollWheelZoom={true}
            className="w-full h-full"
            worldCopyJump={true}
          >
            <MapController center={mapTarget.center} zoom={mapTarget.zoom} />

            <TileLayer
              key={tileMode}
              attribution='&copy; OpenStreetMap contributors'
              url={tileUrls[tileMode]}
              className={tileMode === 'dark' ? 'dark-tiles' : ''}
              maxZoom={18}
            />

            {/* Render Hotspot Bounding Polygons */}
            {showPolygons &&
              filteredHotspots.map((h) => {
                const bounds: [[number, number], [number, number]] = [
                  [h.min_lat, h.min_lon],
                  [h.max_lat, h.max_lon],
                ];
                const isSelected = selectedHotspot?.id === h.id;

                return (
                  <Rectangle
                    key={`poly-${h.id}`}
                    bounds={bounds}
                    pathOptions={{
                      color: isSelected ? '#38bdf8' : h.risk_tier === 'CRITICAL' ? '#ef4444' : '#f97316',
                      weight: isSelected ? 2.5 : 1.2,
                      dashArray: isSelected ? undefined : '4, 4',
                      fillColor: h.risk_tier === 'CRITICAL' ? '#ef4444' : '#f97316',
                      fillOpacity: isSelected ? 0.25 : 0.08,
                    }}
                  />
                );
              })}

            {/* Render Scientific Hotspot Beacon Markers */}
            {filteredHotspots.map((h) => {
              const isSelected = selectedHotspot?.id === h.id;

              return (
                <Marker
                  key={h.id}
                  position={[h.centroid_lat, h.centroid_lon]}
                  icon={createHotspotIcon(h.classification, h.risk_tier, isSelected)}
                  eventHandlers={{
                    click: () => {
                      setSelectedHotspot(h);
                      handleFocusHotspot(h.centroid_lat, h.centroid_lon);
                    },
                  }}
                >
                  <Popup>
                    <div className="p-1 min-w-[220px] text-slate-100">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="font-bold text-xs text-cyan-400 font-mono">
                          {h.id}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          h.risk_tier === 'CRITICAL' ? 'bg-red-500/30 text-red-300' : 'bg-orange-500/30 text-orange-300'
                        }`}>
                          {h.risk_tier} RISK
                        </span>
                      </div>

                      <div className="text-xs font-bold text-white mb-2 leading-snug">
                        {h.name}
                      </div>

                      <div className="space-y-1 text-[11px] text-slate-300 border-t border-slate-700/60 pt-2 font-mono">
                        <div className="flex justify-between">
                          <span className="text-slate-400">Classification:</span>
                          <span className="truncate max-w-[120px] text-cyan-300">{h.classification}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Peak FRP:</span>
                          <span className="text-orange-400 font-bold">{h.max_frp.toFixed(0)} MW</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Detections:</span>
                          <span>{h.event_count} pts ({h.unique_acquisitions} passes)</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Growth:</span>
                          <span className={h.growth_rate > 0 ? 'text-red-400 font-bold' : 'text-emerald-400'}>
                            +{h.growth_rate.toFixed(1)}%
                          </span>
                        </div>
                      </div>

                      <button
                        onClick={() => setSelectedHotspot(h)}
                        className="mt-3 w-full py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-[11px] font-semibold transition-colors flex items-center justify-center gap-1"
                      >
                        <span>Deep Incident Intelligence</span>
                        <ChevronRight className="h-3 w-3" />
                      </button>
                    </div>
                  </Popup>

                  <Tooltip direction="top" offset={[0, -20]} opacity={0.9}>
                    <div className="text-xs">
                      <div className="font-bold text-white">{h.name}</div>
                      <div className="text-[10px] text-cyan-300">{h.classification} · {h.country}</div>
                    </div>
                  </Tooltip>
                </Marker>
              );
            })}

            {/* Dynamic Incident Response Map Layers for Active/Selected Hotspot */}
            <IncidentMapLayers
              hotspot={selectedHotspot}
              windData={windData}
              plumeData={plumeData}
              emergencyData={emergencyData}
              showWindVector={showWindVector}
              showPlumeCone={showPlumeCone}
              visiblePlumeHorizons={visiblePlumeHorizons}
              showBuffer1km={showBuffer1km}
              showBuffer3km={showBuffer3km}
              showEmergencyLayer={showEmergencyLayer}
            />

          </MapContainer>
        </div>

        {/* Global Hotspot Ranking & Intelligence Feed */}
        <div className="glass-panel rounded-2xl p-4 flex flex-col min-h-[640px] h-[calc(100vh-320px)] overflow-hidden bg-[#070d1a]/80 border border-slate-800">
          
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h3 className="font-bold text-sm text-white flex items-center gap-2">
              <Flame className="h-4 w-4 text-cyan-400" />
              <span>Ranked Global Hotspots</span>
              <span className="px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 text-[11px] font-mono">
                {filteredHotspots.length}
              </span>
            </h3>

            {/* Sort selector */}
            <select
              value={filters.sortBy}
              onChange={(e) => setFilters(prev => ({ ...prev, sortBy: e.target.value }))}
              className="px-2 py-1 rounded bg-slate-900 border border-slate-700 text-xs text-slate-300 focus:outline-none focus:border-cyan-500 font-mono"
            >
              <option value="risk_score">Sort: Risk Score</option>
              <option value="max_frp">Sort: Max FRP</option>
              <option value="growth_rate">Sort: Growth Rate</option>
              <option value="area_sq_km">Sort: Area Extent</option>
              <option value="event_count">Sort: Detections</option>
            </select>
          </div>

          {/* Search Box */}
          <div className="relative my-2.5">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search hotspot, country, city, or ID..."
              value={filters.search}
              onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
              className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700/80 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Hotspot Scrollable Feed */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-800/80 pr-1 space-y-1">
            {filteredHotspots.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500">
                No hotspots match the filter parameters.
              </div>
            ) : (
              filteredHotspots.map((h) => {
                const isSelected = selectedHotspot?.id === h.id;

                return (
                  <div
                    key={h.id}
                    onClick={() => {
                      setSelectedHotspot(h);
                      handleFocusHotspot(h.centroid_lat, h.centroid_lon);
                    }}
                    className={`p-3 rounded-xl cursor-pointer transition-all border ${
                      isSelected
                        ? 'bg-cyan-500/15 border-cyan-500/50 shadow-md shadow-cyan-500/10'
                        : 'bg-slate-900/40 border-slate-800/60 hover:bg-slate-800/50 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-xs font-bold text-cyan-300">
                          {h.id}
                        </span>
                        <span className="text-[10px] text-slate-400">· {h.country}</span>
                      </div>
                      
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono ${
                        h.risk_tier === 'CRITICAL'
                          ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                          : h.risk_tier === 'HIGH'
                          ? 'bg-orange-500/20 text-orange-300 border border-orange-500/30'
                          : h.risk_tier === 'MODERATE'
                          ? 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30'
                          : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      }`}>
                        {h.risk_tier} ({h.risk_score.toFixed(0)})
                      </span>
                    </div>

                    <div className="font-bold text-xs text-white truncate">
                      {h.name}
                    </div>

                    <div className="text-[11px] text-cyan-300/80 font-medium truncate mt-0.5">
                      {h.classification}
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2 font-mono">
                      <span>FRP: <b className="text-orange-400">{h.max_frp.toFixed(0)} MW</b></span>
                      <span>Area: {h.area_sq_km.toFixed(1)} km²</span>
                      <span>{h.event_count} pixels</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>

      {/* Sliding Scientific Hotspot Detail Drawer */}
      <HotspotDetailDrawer
        hotspot={selectedHotspot}
        isOpen={Boolean(selectedHotspot)}
        onClose={() => setSelectedHotspot(null)}
        onFocusCoordinates={handleFocusHotspot}
        windData={windData}
        plumeData={plumeData}
        emergencyData={emergencyData}
        incidentMode={incidentMode}
        onToggleIncidentMode={handleToggleIncidentMode}
        showWindVector={showWindVector}
        onToggleWindVector={() => setShowWindVector(!showWindVector)}
        showPlumeCone={showPlumeCone}
        onTogglePlumeCone={() => setShowPlumeCone(!showPlumeCone)}
        showBuffer1km={showBuffer1km}
        onToggleBuffer1km={() => setShowBuffer1km(!showBuffer1km)}
        showBuffer3km={showBuffer3km}
        onToggleBuffer3km={() => setShowBuffer3km(!showBuffer3km)}
        showEmergencyLayer={showEmergencyLayer}
        onToggleEmergencyLayer={() => setShowEmergencyLayer(!showEmergencyLayer)}
      />

    </div>
  );
};

export default GlobalHotspotsPage;
