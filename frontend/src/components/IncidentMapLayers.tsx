import React from 'react';
import { Circle, Polygon, Polyline, Marker, Popup, Tooltip } from 'react-leaflet';
import L from 'leaflet';
import type { 
  HotspotSummary, 
  HotspotDetail, 
  WindData, 
  PlumeConeResponse, 
  EmergencyContextResponse,
  EmergencyFacility 
} from '../types';

interface IncidentMapLayersProps {
  hotspot: HotspotSummary | HotspotDetail | null;
  windData: WindData | null;
  plumeData: PlumeConeResponse | null;
  emergencyData: EmergencyContextResponse | null;
  showWindVector: boolean;
  showPlumeCone: boolean;
  visiblePlumeHorizons: number[]; // e.g. [1, 3, 6, 12]
  showBuffer1km: boolean;
  showBuffer3km: boolean;
  showEmergencyLayer: boolean;
}

// Colors for the 4 time-horizon plume cones
const PLUME_COLORS: Record<number, { stroke: string; fill: string; fillOpacity: number }> = {
  1: { stroke: '#ef4444', fill: '#ef4444', fillOpacity: 0.28 },
  3: { stroke: '#f59e0b', fill: '#f59e0b', fillOpacity: 0.20 },
  6: { stroke: '#eab308', fill: '#eab308', fillOpacity: 0.14 },
  12: { stroke: '#38bdf8', fill: '#38bdf8', fillOpacity: 0.08 },
};

// Create custom icons for emergency resources
function createEmergencyIcon(type: string, isVerifiedSpecialty: boolean = false) {
  let symbol = '🚒';
  let bgColor = 'bg-red-500/90';
  let borderColor = 'border-red-400';

  if (type === 'hospital') {
    if (isVerifiedSpecialty) {
      symbol = '🩺';
      bgColor = 'bg-purple-600/95';
      borderColor = 'border-purple-300';
    } else {
      symbol = '🏥';
      bgColor = 'bg-blue-600/90';
      borderColor = 'border-blue-400';
    }
  } else if (type === 'fire_hydrant') {
    symbol = '🚰';
    bgColor = 'bg-cyan-600/90';
    borderColor = 'border-cyan-300';
  }

  return L.divIcon({
    className: 'fv-emergency-marker',
    html: `
      <div class="flex items-center justify-center w-7 h-7 rounded-full ${bgColor} border-2 ${borderColor} shadow-lg text-white text-xs font-bold transform hover:scale-110 transition-transform">
        <span>${symbol}</span>
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14],
  });
}

// Create rotating wind arrow vector icon
function createWindVectorIcon(wind: WindData) {
  const rotation = wind.downwind_bearing_deg;
  return L.divIcon({
    className: 'fv-wind-vector-icon',
    html: `
      <div style="position: relative; width: 64px; height: 64px; display: flex; align-items: center; justify-content: center;">
        <div style="transform: rotate(${rotation}deg); transform-origin: center; transition: transform 0.5s ease;">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Arrow shaft -->
            <path d="M24 40V12" stroke="#FBBF24" stroke-width="3" stroke-linecap="round" stroke-dasharray="4 2"/>
            <!-- Arrow head pointing up, then rotated downwind -->
            <path d="M16 18L24 8L32 18" stroke="#FBBF24" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div style="position: absolute; bottom: -2px; background: rgba(15,23,42,0.88); border: 1px solid rgba(251,191,36,0.5); padding: 1px 4px; border-radius: 4px; font-family: monospace; font-size: 9px; font-weight: bold; color: #FBBF24; white-space: nowrap;">
          ${wind.wind_speed_kmh} km/h ${wind.cardinal_direction}
        </div>
      </div>
    `,
    iconSize: [64, 64],
    iconAnchor: [32, 32],
  });
}

export const IncidentMapLayers: React.FC<IncidentMapLayersProps> = ({
  hotspot,
  windData,
  plumeData,
  emergencyData,
  showWindVector,
  showPlumeCone,
  visiblePlumeHorizons,
  showBuffer1km,
  showBuffer3km,
  showEmergencyLayer,
}) => {
  if (!hotspot) return null;

  const lat = hotspot.centroid_lat;
  const lon = hotspot.centroid_lon;

  return (
    <>
      {/* 1. Planning Buffer Zones (1 km & 3 km) */}
      {showBuffer3km && (
        <Circle
          center={[lat, lon]}
          radius={3000}
          pathOptions={{
            color: '#0284c7',
            weight: 1.5,
            dashArray: '6, 6',
            fillColor: '#0284c7',
            fillOpacity: 0.07,
          }}
        >
          <Tooltip direction="top" opacity={0.95}>
            <div className="text-xs p-0.5">
              <span className="font-bold text-cyan-300">3 km Evacuation Planning Buffer</span>
              <div className="text-[10px] text-slate-300">Situational planning & resource staging zone</div>
            </div>
          </Tooltip>
        </Circle>
      )}

      {showBuffer1km && (
        <Circle
          center={[lat, lon]}
          radius={1000}
          pathOptions={{
            color: '#f97316',
            weight: 2,
            dashArray: '4, 4',
            fillColor: '#f97316',
            fillOpacity: 0.12,
          }}
        >
          <Tooltip direction="top" opacity={0.95}>
            <div className="text-xs p-0.5">
              <span className="font-bold text-amber-300">1 km Immediate Planning Buffer</span>
              <div className="text-[10px] text-slate-300">Immediate hazard awareness & alert perimeter</div>
            </div>
          </Tooltip>
        </Circle>
      )}

      {/* 2. Indicative Plume Transport Cones (1h, 3h, 6h, 12h) */}
      {showPlumeCone &&
        plumeData &&
        plumeData.horizons
          .filter((hz) => visiblePlumeHorizons.includes(hz.horizon_hours))
          // Render largest horizon first so smaller ones layer on top
          .sort((a, b) => b.horizon_hours - a.horizon_hours)
          .map((horizon) => {
            const style = PLUME_COLORS[horizon.horizon_hours] || PLUME_COLORS[12];
            return (
              <React.Fragment key={`plume-${horizon.horizon_hours}h`}>
                {/* Transport polygon */}
                <Polygon
                  positions={horizon.polygon_coordinates}
                  pathOptions={{
                    color: style.stroke,
                    weight: 1.5,
                    dashArray: horizon.horizon_hours > 3 ? '5, 5' : undefined,
                    fillColor: style.fill,
                    fillOpacity: style.fillOpacity,
                  }}
                >
                  <Tooltip direction="top" opacity={0.95}>
                    <div className="text-xs p-1 space-y-0.5">
                      <div className="font-bold text-amber-300">
                        Indicative {horizon.horizon_hours}h Wind Transport Zone
                      </div>
                      <div className="text-[11px] font-mono text-white">
                        Distance: ~{horizon.projected_distance_km} km · Bearing: {horizon.bearing_deg}°
                      </div>
                      <div className="text-[9px] text-slate-400 italic">
                        Screening indicator only · Not certified fire perimeter
                      </div>
                    </div>
                  </Tooltip>
                </Polygon>

                {/* Curved centerline vector */}
                <Polyline
                  positions={horizon.centerline_coordinates}
                  pathOptions={{
                    color: style.stroke,
                    weight: 2,
                    dashArray: '3, 3',
                  }}
                />
              </React.Fragment>
            );
          })}

      {/* 3. Wind Vector Arrow Overlay */}
      {showWindVector && windData && (
        <Marker position={[lat, lon]} icon={createWindVectorIcon(windData)} zIndexOffset={500}>
          <Tooltip direction="top" opacity={0.95}>
            <div className="text-xs p-1 font-mono">
              <span className="font-bold text-amber-300">Current 10m Wind:</span> {windData.wind_speed_kmh} km/h from {windData.cardinal_direction} ({windData.wind_direction_deg}°)
              <div className="text-[10px] text-slate-400 mt-0.5">
                Downwind Transport Bearing: {windData.downwind_bearing_deg}° · Source: {windData.source}
              </div>
            </div>
          </Tooltip>
        </Marker>
      )}

      {/* 4. Emergency Infrastructure Layer */}
      {showEmergencyLayer &&
        emergencyData &&
        emergencyData.nearby_facilities.map((facility: EmergencyFacility) => (
          <Marker
            key={facility.id}
            position={[facility.latitude, facility.longitude]}
            icon={createEmergencyIcon(facility.facility_type, facility.specialty_verified)}
          >
            <Popup>
              <div className="p-1 min-w-[220px] text-slate-100 space-y-2">
                <div className="flex items-center justify-between gap-2 border-b border-slate-700/60 pb-1.5">
                  <span className="font-bold text-xs text-white">
                    {facility.name}
                  </span>
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold uppercase bg-slate-800 text-cyan-300 border border-slate-700">
                    {facility.facility_type.replace('_', ' ')}
                  </span>
                </div>

                <div className="space-y-1 text-[11px] font-mono text-slate-300">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Distance from Hotspot:</span>
                    <span className="font-bold text-cyan-300">{(facility.distance_m / 1000).toFixed(2)} km</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Compass Bearing:</span>
                    <span className="text-white">{facility.bearing_deg}°</span>
                  </div>
                  {facility.phone && (
                    <div className="flex justify-between">
                      <span className="text-slate-400">Contact:</span>
                      <span className="text-emerald-300 font-semibold">{facility.phone}</span>
                    </div>
                  )}
                  {facility.address && (
                    <div className="text-[10px] text-slate-400 pt-1">
                      {facility.address}
                    </div>
                  )}
                </div>

                {facility.specialty_verified && (
                  <div className="px-2 py-1 rounded bg-purple-950/80 border border-purple-500/40 text-[10px] text-purple-200 font-medium">
                    {facility.specialty_note || 'Verified Emergency Specialty Unit'}
                  </div>
                )}

                <div className="text-[9px] text-slate-500 pt-1 border-t border-slate-800 flex justify-between">
                  <span>Source: {facility.source}</span>
                  <span className="text-cyan-400 font-semibold">{facility.data_quality}</span>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
    </>
  );
};

export default IncidentMapLayers;
