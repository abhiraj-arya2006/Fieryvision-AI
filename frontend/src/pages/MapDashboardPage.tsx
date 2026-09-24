import React, { useState, useMemo } from 'react';
import { useActiveEvents } from '../hooks/useActiveEvents';
import { useFacilities } from '../hooks/useFacilities';
import { useStatistics } from '../hooks/useStatistics';
import { MapView } from '../components/MapView';
import { StatsSummaryBar } from '../components/StatsSummaryBar';
import { FilterBar } from '../components/FilterBar';
import { EventDetailsDrawer } from '../components/EventDetailsDrawer';
import { SatelliteContextModal } from '../components/SatelliteContextModal';
import type { CanonicalEvent, EventFilterState } from '../types';
import { AlertCircle, RefreshCw, List } from 'lucide-react';

export const MapDashboardPage: React.FC = () => {
  const { data: eventsData, loading: eventsLoading, error: eventsError, refresh: refreshEvents } = useActiveEvents(60000);
  const { data: facilitiesData } = useFacilities();
  const { data: statsData, refresh: refreshStats } = useStatistics();

  const [selectedEvent, setSelectedEvent] = useState<CanonicalEvent | null>(null);
  const [satelliteModalEventId, setSatelliteModalEventId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'map' | 'split'>('map');

  const [filters, setFilters] = useState<EventFilterState>({
    classification: 'all',
    priority: 'all',
    persistence: 'all',
    confidence: 'all',
    anomaly: 'all',
    search: '',
  });

  const allEvents = eventsData?.events || [];
  const facilities = facilitiesData?.facilities || [];

  // Filter logic matching map.html exact rules
  const filteredEvents = useMemo(() => {
    return allEvents.filter((event) => {
      // Classification filter
      if (filters.classification !== 'all') {
        const cls = (event.classification || '').toLowerCase();
        if (filters.classification === 'industrial_heat_source' && !cls.includes('industrial heat')) {
          return false;
        }
        if (filters.classification === 'persistent_industrial' && !cls.includes('persistent industrial')) {
          return false;
        }
        if (filters.classification === 'agricultural_burning' && !cls.includes('agricultural')) {
          return false;
        }
        if (filters.classification === 'natural_fire' && !cls.includes('natural')) {
          return false;
        }
        if (filters.classification === 'unclassified' && !cls.includes('unclassified')) {
          return false;
        }
      }

      // Priority filter
      if (filters.priority !== 'all') {
        const p = (event.priority || '').toLowerCase();
        if (filters.priority === 'moderate') {
          if (p !== 'moderate' && p !== 'medium') return false;
        } else if (p !== filters.priority) {
          return false;
        }
      }

      // Persistence filter
      if (filters.persistence !== 'all') {
        const val = String(event.persistence || '').toLowerCase();
        const isPersistent =
          val === 'true' ||
          val === 'yes' ||
          val === 'persistent' ||
          val === 'high_persistence' ||
          val === 'recurrent_heat_source' ||
          val === '1';

        if (filters.persistence === 'persistent' && !isPersistent) return false;
        if (filters.persistence === 'non-persistent' && isPersistent) return false;
      }

      // Confidence filter
      if (filters.confidence !== 'all') {
        const conf = String(event.confidence || '').toLowerCase();
        if (conf !== filters.confidence) return false;
      }

      // Anomaly filter (Isolation Forest)
      if (filters.anomaly !== 'all') {
        const isAnom = Boolean(event.is_anomaly || event.anomaly_flag);
        if (filters.anomaly === 'anomaly' && !isAnom) return false;
        if (filters.anomaly === 'normal' && isAnom) return false;
      }

      // Search query
      if (filters.search.trim() !== '') {
        const q = filters.search.toLowerCase().trim();
        const matchId = (event.event_id || '').toLowerCase().includes(q);
        const matchFac = (event.nearest_facility_name || '').toLowerCase().includes(q);
        const matchLand = (event.landcover || '').toLowerCase().includes(q);
        const matchCls = (event.classification || '').toLowerCase().includes(q);
        if (!matchId && !matchFac && !matchLand && !matchCls) return false;
      }

      return true;
    });
  }, [allEvents, filters]);

  const handleStatsFilter = (filterType: string, value: string) => {
    if (filterType === 'classification') {
      if (value === 'all') {
        setFilters((prev) => ({ ...prev, classification: 'all' }));
      } else if (value === 'industrial') {
        setFilters((prev) => ({ ...prev, classification: 'industrial_heat_source' }));
      } else if (value === 'agricultural') {
        setFilters((prev) => ({ ...prev, classification: 'agricultural_burning' }));
      } else if (value === 'natural') {
        setFilters((prev) => ({ ...prev, classification: 'natural_fire' }));
      }
    } else if (filterType === 'persistence') {
      setFilters((prev) => ({ ...prev, persistence: value }));
    } else if (filterType === 'priority') {
      setFilters((prev) => ({ ...prev, priority: value }));
    }
  };

  const handleRefreshAll = () => {
    refreshEvents();
    refreshStats();
  };

  return (
    <div className="flex-1 flex flex-col p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-4">
      
      {/* Top Header / Status bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
              Giaspura Geospatial Monitoring Console
            </h1>
            <span className="px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 text-xs font-mono font-medium">
              30.8756°N, 75.8985°E · 15km Zone
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            Active satellite thermal anomalies combined with industrial footprint telemetry and ML anomaly scoring.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode(viewMode === 'map' ? 'split' : 'map')}
            className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-xs font-medium text-slate-200 flex items-center gap-1.5 transition-colors"
          >
            <List className="h-3.5 w-3.5" />
            <span>{viewMode === 'map' ? 'Show Events List' : 'Hide Events List'}</span>
          </button>

          <button
            onClick={handleRefreshAll}
            disabled={eventsLoading}
            className="px-3 py-1.5 rounded-lg border border-cyan-500/30 bg-cyan-950/40 hover:bg-cyan-900/60 text-xs font-semibold text-cyan-300 flex items-center gap-1.5 transition-colors shadow-sm shadow-cyan-500/10"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${eventsLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Stats Summary Bar */}
      <StatsSummaryBar
        stats={statsData}
        events={allEvents}
        onSelectFilter={handleStatsFilter}
      />

      {/* Filter Bar */}
      <FilterBar
        filters={filters}
        onChange={setFilters}
        totalFiltered={filteredEvents.length}
        totalEvents={allEvents.length}
      />

      {/* Error state if backend unreachable */}
      {eventsError && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-3 text-red-200">
          <AlertCircle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
          <div className="text-xs">
            <h4 className="font-semibold text-red-300">Monitoring API Unavailable</h4>
            <p className="mt-0.5 text-red-300/80">
              Unable to connect to the FieryVision backend ({eventsError}). No synthetic events have been added. Check if FastAPI is running on port 8000.
            </p>
          </div>
        </div>
      )}

      {/* Main Map & Split View Container */}
      <div className={`grid gap-4 flex-1 ${viewMode === 'split' ? 'lg:grid-cols-3' : 'grid-cols-1'}`}>
        
        {/* Map View */}
        <div className={`w-full min-h-[550px] sm:min-h-[620px] ${viewMode === 'split' ? 'lg:col-span-2' : ''}`}>
          <MapView
            events={filteredEvents}
            facilities={facilities}
            selectedEvent={selectedEvent}
            onSelectEvent={(ev) => setSelectedEvent(ev)}
          />
        </div>

        {/* Side Event Table/List if in Split View */}
        {viewMode === 'split' && (
          <div className="glass-panel rounded-2xl p-4 flex flex-col h-[620px] overflow-hidden">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="font-bold text-sm text-white flex items-center gap-2">
                <span>Active Anomalies</span>
                <span className="px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 text-[11px] font-mono">
                  {filteredEvents.length}
                </span>
              </h3>
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-slate-800/80 mt-2 pr-1">
              {filteredEvents.length === 0 ? (
                <div className="py-12 text-center text-xs text-slate-500">
                  No thermal events match the current filter criteria.
                </div>
              ) : (
                filteredEvents.map((event) => (
                  <button
                    key={event.event_id}
                    onClick={() => setSelectedEvent(event)}
                    className={`w-full text-left p-3 rounded-xl transition-all my-1 border ${
                      selectedEvent?.event_id === event.event_id
                        ? 'bg-cyan-500/15 border-cyan-500/40'
                        : 'bg-slate-900/40 border-slate-800/60 hover:bg-slate-800/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-[11px] font-bold text-cyan-300">
                        {event.event_id}
                      </span>
                      <span className={`px-2 py-0.2 rounded text-[10px] font-bold uppercase ${
                        (event.priority || '').toLowerCase() === 'high' || (event.priority || '').toLowerCase() === 'critical'
                          ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                          : 'bg-slate-800 text-slate-300'
                      }`}>
                        {event.priority || 'LOW'}
                      </span>
                    </div>

                    <div className="text-xs font-semibold text-white truncate">
                      {event.classification}
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2 font-mono">
                      <span>Risk: {event.risk_score}/100</span>
                      {event.frp != null && <span>FRP: {event.frp} MW</span>}
                      {event.is_anomaly && <span className="text-red-400 font-semibold">🚨 Outlier</span>}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        )}

      </div>

      {/* Sliding Event Drawer */}
      <EventDetailsDrawer
        event={selectedEvent}
        isOpen={Boolean(selectedEvent)}
        onClose={() => setSelectedEvent(null)}
        onOpenSatelliteContext={(id) => setSatelliteModalEventId(id)}
      />

      {/* Satellite Context Modal */}
      <SatelliteContextModal
        eventId={satelliteModalEventId}
        isOpen={Boolean(satelliteModalEventId)}
        onClose={() => setSatelliteModalEventId(null)}
      />

    </div>
  );
};

export default MapDashboardPage;
