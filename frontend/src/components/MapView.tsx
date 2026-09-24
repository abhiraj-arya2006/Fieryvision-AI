import React, { useState } from 'react';
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
  Flame 
} from 'lucide-react';
import type { CanonicalEvent, Facility } from '../types';
import { getClassificationColor, getPriorityColor } from '../utils/formatters';

// Giaspura, Ludhiana Center Coordinates
export const GIASPURA_CENTER: [number, number] = [30.875625, 75.898481];
export const GIASPURA_RADIUS_METERS = 15000; // 15 km buffer

interface MapViewProps {
  events: CanonicalEvent[];
  facilities: Facility[];
  selectedEvent: CanonicalEvent | null;
  onSelectEvent: (event: CanonicalEvent) => void;
  investigationCoord?: [number, number] | null;
}

// Controller component to smoothly fly/reset map view
function MapController({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  React.useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
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
    <div style="position:relative; width:18px; height:18px; display:flex; align-items:center; justify-content:center;">
      <div style="position:absolute; width:18px; height:18px; border-radius:50%; background:rgba(56,189,248,0.3); animation:markerPing 2s infinite;"></div>
      <div style="width:10px; height:10px; border-radius:50%; background:#38bdf8; border:2px solid #ffffff; box-shadow:0 0 10px #38bdf8;"></div>
    </div>
  `,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
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
    zoom: 13,
  });

  const tileUrls = {
    dark: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    satellite: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    street: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  };

  const handleResetView = () => {
    setMapTarget({ center: GIASPURA_CENTER, zoom: 13 });
  };

  return (
    <div className="relative w-full h-full min-h-[500px] rounded-2xl overflow-hidden border border-cyan-500/25 shadow-2xl bg-[#050914]">
      
      {/* Map Layers & Quick Action Controls Overlay */}
      <div className="absolute top-4 left-4 z-[400] flex flex-wrap gap-2 pointer-events-auto">
        <div className="glass-panel p-1.5 rounded-xl flex items-center gap-1 text-xs text-slate-300">
          <button
            onClick={() => setShowEvents(!showEvents)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-colors ${
              showEvents ? 'bg-cyan-500/20 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'
            }`}
            title="Toggle Fire Events"
          >
            <Flame className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Events ({events.length})</span>
          </button>

          <button
            onClick={() => setShowFacilities(!showFacilities)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-colors ${
              showFacilities ? 'bg-cyan-500/20 text-cyan-300 font-semibold' : 'text-slate-400 hover:text-white'
            }`}
            title="Toggle Industrial Facilities"
          >
            <Factory className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Facilities ({facilities.length})</span>
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

        {/* Center Target Action */}
        <button
          onClick={handleResetView}
          className="glass-panel px-3 py-1.5 rounded-xl flex items-center gap-1.5 text-xs text-slate-300 hover:text-white hover:border-cyan-500/40 transition-all"
          title="Recenter Map on Giaspura Monitoring Center"
        >
          <Compass className="h-3.5 w-3.5 text-cyan-400" />
          <span className="hidden sm:inline">Center Giaspura</span>
        </button>
      </div>

      {/* Map Legend Overlay */}
      <div className="absolute bottom-4 left-4 z-[400] glass-panel p-3 rounded-xl text-xs space-y-1.5 hidden md:block max-w-[220px]">
        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
          Map Legend
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
          <span className="text-slate-300">Industrial Facility</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-cyan-400 shadow-sm shadow-cyan-400"></span>
          <span className="text-slate-300">Giaspura Monitoring Point</span>
        </div>
      </div>

      {/* Leaflet Map Container */}
      <MapContainer
        center={GIASPURA_CENTER}
        zoom={13}
        scrollWheelZoom={true}
        className="w-full h-full"
      >
        <MapController center={mapTarget.center} zoom={mapTarget.zoom} />

        {/* Base Tile Layer - 100% Free & Open (No API key required) */}
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
              weight: 1.5,
              dashArray: '6, 6',
              fillColor: '#0284c7',
              fillOpacity: 0.05,
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

        {/* Facility Markers */}
        {showFacilities &&
          facilities.map((facility) => {
            if (!Number.isFinite(facility.latitude) || !Number.isFinite(facility.longitude)) return null;

            return (
              <CircleMarker
                key={facility.id}
                center={[facility.latitude, facility.longitude]}
                radius={5}
                pathOptions={{
                  color: '#aebdca',
                  weight: 1,
                  fillColor: '#53697c',
                  fillOpacity: 0.85,
                }}
              >
                <Tooltip direction="top" opacity={0.9}>
                  <div>
                    <div className="font-semibold text-white">{facility.name}</div>
                    <div className="text-[10px] text-cyan-300">{facility.site_type}</div>
                  </div>
                </Tooltip>
              </CircleMarker>
            );
          })}

        {/* Active Fire Event Markers */}
        {showEvents &&
          events.map((event) => {
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

        {/* Temporary Investigation Point (if investigating coordinates) */}
        {investigationCoord && (
          <Marker
            position={investigationCoord}
            icon={L.divIcon({
              className: 'fv-investigate-icon',
              html: `
                <div style="position:relative; width:22px; height:22px; display:flex; align-items:center; justify-content:center;">
                  <div style="position:absolute; width:22px; height:22px; border-radius:50%; background:rgba(234,179,8,0.4); animation:markerPing 1.5s infinite;"></div>
                  <div style="width:12px; height:12px; border-radius:50%; background:#eab308; border:2px solid #ffffff; box-shadow:0 0 10px #eab308;"></div>
                </div>
              `,
              iconSize: [22, 22],
              iconAnchor: [11, 11],
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
