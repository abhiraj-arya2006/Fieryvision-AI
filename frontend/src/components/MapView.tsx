import React, { useState, useMemo } from 'react';
import { 
  MapContainer, 
  TileLayer, 
  Marker, 
  Popup, 
  Tooltip, 
  CircleMarker, 
  useMap 
} from 'react-leaflet';
import L from 'leaflet';
import { 
  Factory, 
  Flame,
  Globe
} from 'lucide-react';
import type { CanonicalEvent, Facility } from '../types';
import { getClassificationColor, getPriorityColor } from '../utils/formatters';

// Geographic Coordinates
export const WORLD_CENTER: [number, number] = [20.0, 0.0];
export const WORLD_ZOOM = 2;

export const INDIA_CENTER: [number, number] = [22.5937, 78.9629];
export const INDIA_ZOOM = 5;

interface MapViewProps {
  events: CanonicalEvent[];
  facilities: Facility[];
  selectedEvent: CanonicalEvent | null;
  onSelectEvent: (event: CanonicalEvent) => void;
  investigationCoord?: [number, number] | null;
}

// Controller component: Smoothly flies to requested target coordinates
function MapController({ 
  targetCenter, 
  targetZoom,
}: { 
  targetCenter: [number, number]; 
  targetZoom: number;
  initialAnimate?: boolean;
}) {
  const map = useMap();

  React.useEffect(() => {
    map.flyTo(targetCenter, targetZoom, {
      duration: 1.2,
      easeLinearity: 0.25,
    });
  }, [targetCenter, targetZoom, map]);

  return null;
}

// Custom DivIcon creator for events
function createEventIcon(classification: string, isAnomaly: boolean, isSelected: boolean = false) {
  const colorType = getClassificationColor(classification);
  return L.divIcon({
    className: 'fv-leaflet-div-icon',
    html: `
      <div class="fv-marker-wrapper marker-${colorType} ${isAnomaly ? 'ring-2 ring-red-400 rounded-full' : ''} ${isSelected ? 'scale-125 ring-4 ring-cyan-400 rounded-full' : ''}">
        <div class="fv-marker-pulse"></div>
        <div class="fv-marker-dot"></div>
      </div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12],
  });
}

export const MapView: React.FC<MapViewProps> = ({
  events,
  facilities,
  selectedEvent,
  onSelectEvent,
  investigationCoord,
}) => {
  const [showEvents, setShowEvents] = useState<boolean>(true);
  const [showFacilities, setShowFacilities] = useState<boolean>(true);
  const [tileMode, setTileMode] = useState<'dark' | 'satellite' | 'street'>('dark');
  const [mapTarget, setMapTarget] = useState<{ center: [number, number]; zoom: number }>({
    center: WORLD_CENTER,
    zoom: WORLD_ZOOM,
  });

  const tileUrls = {
    dark: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    satellite: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    street: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  };

  // Support global facilities across the entire world
  const validFacilities = useMemo(() => {
    return facilities.filter((f) => {
      const lat = Number(f.latitude);
      const lon = Number(f.longitude);
      return Number.isFinite(lat) && Number.isFinite(lon);
    });
  }, [facilities]);

  // Support global events across the entire world
  const validEvents = useMemo(() => {
    return events.filter((ev) => {
      const lat = Number(ev.latitude);
      const lon = Number(ev.longitude);
      return Number.isFinite(lat) && Number.isFinite(lon);
    });
  }, [events]);

  const handleFlyToWorld = () => {
    setMapTarget({ center: WORLD_CENTER, zoom: WORLD_ZOOM });
  };

  const handleFlyToIndia = () => {
    setMapTarget({ center: INDIA_CENTER, zoom: INDIA_ZOOM });
  };

  const handleFlyToUS = () => {
    setMapTarget({ center: [39.5, -98.35], zoom: 4 });
  };

  return (
    <div className="relative w-full h-full min-h-[500px] rounded-2xl overflow-hidden border border-cyan-500/25 shadow-2xl bg-[#050914]">
      
      {/* Map Layers & Quick Action Controls Overlay */}
      <div className="absolute top-4 left-4 z-[400] flex flex-wrap gap-2 pointer-events-auto">
        {/* Layer Toggles */}
        <div className="glass-panel p-1.5 rounded-xl flex items-center gap-1 text-xs text-slate-300">
          <button
            onClick={() => setShowEvents(!showEvents)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-colors ${
              showEvents ? 'bg-cyan-500/20 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'
            }`}
            title="Toggle Fire Events"
          >
            <Flame className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Events ({validEvents.length})</span>
          </button>

          <button
            onClick={() => setShowFacilities(!showFacilities)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-colors ${
              showFacilities ? 'bg-cyan-500/20 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'
            }`}
            title="Toggle Industrial Facilities"
          >
            <Factory className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Facilities ({validFacilities.length})</span>
          </button>
        </div>

        {/* View Zoom Presets */}
        <div className="glass-panel p-1.5 rounded-xl flex items-center gap-1 text-xs text-slate-300">
          <button
            onClick={handleFlyToWorld}
            className="px-2.5 py-1.5 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white flex items-center gap-1 transition-colors"
            title="Zoom out to Global World View"
          >
            <Globe className="h-3.5 w-3.5 text-cyan-400" />
            <span className="hidden sm:inline">World View</span>
          </button>

          <button
            onClick={handleFlyToIndia}
            className="px-2.5 py-1.5 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white flex items-center gap-1 transition-colors"
            title="Zoom to India View"
          >
            <Globe className="h-3.5 w-3.5 text-amber-400" />
            <span className="hidden sm:inline">India View</span>
          </button>

          <button
            onClick={handleFlyToUS}
            className="px-2.5 py-1.5 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white flex items-center gap-1 transition-colors"
            title="Zoom to North America View"
          >
            <Globe className="h-3.5 w-3.5 text-emerald-400" />
            <span className="hidden sm:inline">Americas</span>
          </button>
        </div>

        {/* Tile Basemap Selector */}
        <div className="glass-panel p-1.5 rounded-xl flex items-center gap-1 text-xs text-slate-300">
          <button
            onClick={() => setTileMode('dark')}
            className={`px-2.5 py-1.5 rounded-lg transition-colors ${
              tileMode === 'dark' ? 'bg-cyan-500/25 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Dark
          </button>
          <button
            onClick={() => setTileMode('satellite')}
            className={`px-2.5 py-1.5 rounded-lg transition-colors ${
              tileMode === 'satellite' ? 'bg-cyan-500/25 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Satellite
          </button>
          <button
            onClick={() => setTileMode('street')}
            className={`px-2.5 py-1.5 rounded-lg transition-colors ${
              tileMode === 'street' ? 'bg-cyan-500/25 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Street
          </button>
        </div>
      </div>

      {/* Map Legend Overlay */}
      <div className="absolute bottom-4 left-4 z-[400] glass-panel p-3 rounded-xl text-xs space-y-1.5 hidden md:block max-w-[240px]">
        <div className="flex items-center justify-between pb-1 mb-1 border-b border-slate-700/60">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            Map Legend
          </span>
          <span className="text-[10px] text-cyan-400 font-mono">Global</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-red-500 shadow-sm shadow-red-500"></span>
          <span className="text-slate-300">Industrial Fire / Heat</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-orange-500 shadow-sm shadow-orange-500"></span>
          <span className="text-slate-300">Persistent Industrial</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400"></span>
          <span className="text-slate-300">Agricultural Burning</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-blue-400 shadow-sm shadow-blue-400"></span>
          <span className="text-slate-300">Natural / Forest Fire</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-slate-400 border border-slate-300"></span>
          <span className="text-slate-300">Monitored Industrial Site</span>
        </div>
      </div>

      {/* Leaflet Map Container */}
      <MapContainer
        center={WORLD_CENTER}
        zoom={WORLD_ZOOM}
        scrollWheelZoom={true}
        className="w-full h-full"
      >
        <MapController targetCenter={mapTarget.center} targetZoom={mapTarget.zoom} />

        {/* Base Tile Layer */}
        <TileLayer
          key={tileMode}
          attribution={
            tileMode === 'satellite'
              ? '&copy; <a href="https://www.esri.com/">Esri</a>, USGS, NOAA'
              : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          }
          url={tileUrls[tileMode]}
          className={tileMode === 'dark' ? 'dark-tiles' : ''}
          maxZoom={19}
        />

        {/* Industrial Facility Markers */}
        {showFacilities &&
          validFacilities.map((facility) => {
            if (!Number.isFinite(facility.latitude) || !Number.isFinite(facility.longitude)) return null;

            return (
              <CircleMarker
                key={facility.id}
                center={[facility.latitude, facility.longitude]}
                radius={6}
                pathOptions={{
                  color: '#38bdf8',
                  weight: 1.5,
                  fillColor: '#0f766e',
                  fillOpacity: 0.9,
                }}
              >
                <Tooltip direction="top" opacity={0.95}>
                  <div className="p-1">
                    <div className="font-bold text-white text-xs">{facility.name}</div>
                    <div className="text-[10px] text-cyan-300 font-medium">{facility.site_type}</div>
                    <div className="text-[10px] text-slate-300 mt-0.5">{facility.address}</div>
                  </div>
                </Tooltip>
              </CircleMarker>
            );
          })}

        {/* Active Fire Event Markers (Global & Fallback) */}
        {showEvents &&
          validEvents.map((event) => {
            const lat = Number(event.latitude);
            const lon = Number(event.longitude);
            if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;

            const isAnomaly = Boolean(event.is_anomaly || event.anomaly_flag);
            const priorityStyle = getPriorityColor(event.priority);

            return (
              <Marker
                key={event.event_id}
                position={[lat, lon]}
                icon={createEventIcon(event.classification, isAnomaly, selectedEvent?.event_id === event.event_id)}
                eventHandlers={{
                  click: () => onSelectEvent(event),
                }}
              >
                <Popup>
                  <div className="p-1 min-w-[200px] text-slate-100">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-bold text-sm text-cyan-400 font-mono">
                        {event.event_id}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${priorityStyle.bg} ${priorityStyle.text}`}>
                        {event.priority || 'LOW'}
                      </span>
                    </div>

                    <div className="text-xs font-semibold text-white mb-2">
                      {event.classification}
                    </div>

                    <div className="space-y-1 text-[11px] text-slate-300 border-t border-slate-700/60 pt-2 font-mono">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">Source:</span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          event.source === 'NASA_FIRMS'
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : 'bg-amber-500/20 text-amber-300'
                        }`}>
                          {event.source === 'NASA_FIRMS' ? 'NASA FIRMS' : event.source}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">ML Status:</span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          event.ml_status === 'evaluated'
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : event.ml_status === 'not_evaluated'
                            ? 'bg-slate-500/20 text-slate-300'
                            : 'bg-amber-500/20 text-amber-300'
                        }`}>
                          {(event.ml_status || 'not_evaluated').toUpperCase()}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Risk Score:</span>
                        <span className="font-bold text-cyan-300">{event.risk_score}/100</span>
                      </div>
                      {event.frp != null && (
                        <div className="flex justify-between">
                          <span className="text-slate-400">FRP:</span>
                          <span>{event.frp} MW</span>
                        </div>
                      )}
                      {event.nearest_facility_name && (
                        <div className="flex justify-between">
                          <span className="text-slate-400">Nearest:</span>
                          <span className="truncate max-w-[120px]">{event.nearest_facility_name}</span>
                        </div>
                      )}
                    </div>

                    <button
                      onClick={() => onSelectEvent(event)}
                      className="mt-3 w-full py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-[11px] font-semibold transition-colors"
                    >
                      View Event Intelligence →
                    </button>
                  </div>
                </Popup>
              </Marker>
            );
          })}

        {/* Temporary Investigation Point */}
        {investigationCoord && (
          <Marker
            position={investigationCoord}
            icon={L.divIcon({
              className: 'fv-investigate-icon',
              html: `
                <div style="position:relative; width:24px; height:24px; display:flex; align-items:center; justify-content:center;">
                  <div style="position:absolute; width:24px; height:24px; border-radius:50%; background:rgba(234,179,8,0.4); animation:markerPing 1.5s infinite;"></div>
                  <div style="width:14px; height:14px; border-radius:50%; background:#eab308; border:2px solid #ffffff; box-shadow:0 0 12px #eab308;"></div>
                </div>
              `,
              iconSize: [24, 24],
              iconAnchor: [12, 12],
            })}
          >
            <Tooltip direction="top" permanent>
              INVESTIGATION COORDINATE ({investigationCoord[0].toFixed(4)}, {investigationCoord[1].toFixed(4)})
            </Tooltip>
          </Marker>
        )}

      </MapContainer>
    </div>
  );
};

export default MapView;
