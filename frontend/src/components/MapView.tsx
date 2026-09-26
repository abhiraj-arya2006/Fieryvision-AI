import React, { useState, useMemo } from 'react';
import { 
  MapContainer, 
  TileLayer, 
  Circle, 
  Marker, 
  Popup, 
  Tooltip, 
  CircleMarker, 
  useMap 
} from 'react-leaflet';
import L from 'leaflet';
import { 
  Crosshair, 
  Compass, 
  Factory, 
  Flame,
  Globe
} from 'lucide-react';
import type { CanonicalEvent, Facility } from '../types';
import { getClassificationColor, getPriorityColor } from '../utils/formatters';

// Geographic Coordinates
export const INDIA_CENTER: [number, number] = [22.5937, 78.9629];
export const INDIA_ZOOM = 5;

export const GIASPURA_CENTER: [number, number] = [30.875625, 75.898481];
export const GIASPURA_ZOOM = 13.5;
export const GIASPURA_RADIUS_METERS = 15000; // 15 km buffer

// Haversine distance helper (meters)
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

interface MapViewProps {
  events: CanonicalEvent[];
  facilities: Facility[];
  selectedEvent: CanonicalEvent | null;
  onSelectEvent: (event: CanonicalEvent) => void;
  investigationCoord?: [number, number] | null;
}

// Controller component: Starts centered on India and smoothly flies to Giaspura
function MapController({ 
  targetCenter, 
  targetZoom,
  initialAnimate = true
}: { 
  targetCenter: [number, number]; 
  targetZoom: number;
  initialAnimate?: boolean;
}) {
  const map = useMap();
  const animatedRef = React.useRef(false);

  React.useEffect(() => {
    if (initialAnimate && !animatedRef.current) {
      animatedRef.current = true;
      // Start centered on national India overview
      map.setView(INDIA_CENTER, INDIA_ZOOM, { animate: false });
      
      // Smoothly fly in to the Giaspura monitoring zone
      const timer = setTimeout(() => {
        map.flyTo(targetCenter, targetZoom, {
          duration: 2.0,
          easeLinearity: 0.25,
        });
      }, 350);

      return () => clearTimeout(timer);
    } else {
      map.flyTo(targetCenter, targetZoom, {
        duration: 1.2,
        easeLinearity: 0.25,
      });
    }
  }, [targetCenter, targetZoom, map, initialAnimate]);

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

// Center beacon icon for Giaspura
const centerIcon = L.divIcon({
  className: 'fv-center-icon',
  html: `
    <div style="position:relative; width:22px; height:22px; display:flex; align-items:center; justify-content:center;">
      <div style="position:absolute; width:22px; height:22px; border-radius:50%; background:rgba(56,189,248,0.4); animation:markerPing 2s infinite;"></div>
      <div style="width:12px; height:12px; border-radius:50%; background:#38bdf8; border:2px solid #ffffff; box-shadow:0 0 12px #38bdf8;"></div>
    </div>
  `,
  iconSize: [22, 22],
  iconAnchor: [11, 11],
});

export const MapView: React.FC<MapViewProps> = ({
  events,
  facilities,
  selectedEvent,
  onSelectEvent,
  investigationCoord,
}) => {
  const [showEvents, setShowEvents] = useState<boolean>(true);
  const [showFacilities, setShowFacilities] = useState<boolean>(true);
  const [showBuffer, setShowBuffer] = useState<boolean>(true);
  const [tileMode, setTileMode] = useState<'dark' | 'satellite' | 'street'>('dark');
  const [mapTarget, setMapTarget] = useState<{ center: [number, number]; zoom: number }>({
    center: GIASPURA_CENTER,
    zoom: GIASPURA_ZOOM,
  });

  const tileUrls = {
    dark: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    satellite: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    street: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  };

  // Filter facilities strictly to Giaspura / Punjab region (within 35 km)
  const giaspuraFacilities = useMemo(() => {
    return facilities.filter((f) => {
      if (f.id.startsWith('IND-GIAS') || f.id === 'HS-IND-001' || f.id.startsWith('HS-IND')) {
        return true;
      }
      const dist = calculateDistanceMeters(GIASPURA_CENTER[0], GIASPURA_CENTER[1], f.latitude, f.longitude);
      return dist <= 35000;
    });
  }, [facilities]);

  // Filter events strictly to Giaspura study region
  const giaspuraEvents = useMemo(() => {
    return events.filter((ev) => {
      const lat = Number(ev.latitude);
      const lon = Number(ev.longitude);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false;
      const dist = calculateDistanceMeters(GIASPURA_CENTER[0], GIASPURA_CENTER[1], lat, lon);
      return dist <= 35000;
    });
  }, [events]);

  const handleFlyToGiaspura = () => {
    setMapTarget({ center: GIASPURA_CENTER, zoom: GIASPURA_ZOOM });
  };

  const handleFlyToIndia = () => {
    setMapTarget({ center: INDIA_CENTER, zoom: INDIA_ZOOM });
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
            <span className="hidden sm:inline">Events ({giaspuraEvents.length})</span>
          </button>

          <button
            onClick={() => setShowFacilities(!showFacilities)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-colors ${
              showFacilities ? 'bg-cyan-500/20 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'
            }`}
            title="Toggle Industrial Facilities"
          >
            <Factory className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Facilities ({giaspuraFacilities.length})</span>
          </button>

          <button
            onClick={() => setShowBuffer(!showBuffer)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-colors ${
              showBuffer ? 'bg-cyan-500/20 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'
            }`}
            title="Toggle 15km Buffer"
          >
            <Crosshair className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">15km Zone</span>
          </button>
        </div>

        {/* View Zoom Presets */}
        <div className="glass-panel p-1.5 rounded-xl flex items-center gap-1 text-xs text-slate-300">
          <button
            onClick={handleFlyToIndia}
            className="px-2.5 py-1.5 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white flex items-center gap-1 transition-colors"
            title="Zoom out to India National View"
          >
            <Globe className="h-3.5 w-3.5 text-amber-400" />
            <span className="hidden sm:inline">India View</span>
          </button>

          <button
            onClick={handleFlyToGiaspura}
            className="px-2.5 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 font-semibold flex items-center gap-1 border border-cyan-500/30 transition-colors shadow-sm shadow-cyan-500/10"
            title="Focus on Giaspura, Ludhiana Monitoring Zone"
          >
            <Compass className="h-3.5 w-3.5 text-cyan-400" />
            <span className="hidden sm:inline">Focus Giaspura</span>
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
            Giaspura Legend
          </span>
          <span className="text-[10px] text-cyan-400 font-mono">15km Radius</span>
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
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-cyan-400 shadow-sm shadow-cyan-400"></span>
          <span className="text-slate-300">Giaspura Monitoring Point</span>
        </div>
      </div>

      {/* Leaflet Map Container */}
      <MapContainer
        center={INDIA_CENTER}
        zoom={INDIA_ZOOM}
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

        {/* 15 km Regional Monitoring Buffer */}
        {showBuffer && (
          <Circle
            center={GIASPURA_CENTER}
            radius={GIASPURA_RADIUS_METERS}
            pathOptions={{
              color: '#38bdf8',
              weight: 2,
              dashArray: '6, 6',
              fillColor: '#0284c7',
              fillOpacity: 0.08,
            }}
          >
            <Tooltip direction="top" opacity={0.9}>
              15 km Regional Monitoring Buffer (Giaspura Study Area)
            </Tooltip>
          </Circle>
        )}

        {/* Giaspura Monitoring Center Marker */}
        <Marker position={GIASPURA_CENTER} icon={centerIcon}>
          <Tooltip direction="top" permanent={false}>
            GIASPURA MONITORING CENTER (30.8756°N, 75.8985°E)
          </Tooltip>
        </Marker>

        {/* Giaspura Facility Markers */}
        {showFacilities &&
          giaspuraFacilities.map((facility) => {
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

        {/* Giaspura Active Fire Event Markers */}
        {showEvents &&
          giaspuraEvents.map((event) => {
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
