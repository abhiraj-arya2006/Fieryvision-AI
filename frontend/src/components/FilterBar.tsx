import { Search, RotateCcw } from 'lucide-react';
import type { EventFilterState } from '../types';

interface FilterBarProps {
  filters: EventFilterState;
  onChange: (filters: EventFilterState) => void;
  totalFiltered: number;
  totalEvents: number;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onChange,
  totalFiltered,
  totalEvents,
}) => {
  const updateFilter = (key: keyof EventFilterState, value: string) => {
    onChange({
      ...filters,
      [key]: value,
    });
  };

  const handleReset = () => {
    onChange({
      classification: 'all',
      priority: 'all',
      persistence: 'all',
      confidence: 'all',
      anomaly: 'all',
      search: '',
    });
  };

  const hasActiveFilters =
    filters.classification !== 'all' ||
    filters.priority !== 'all' ||
    filters.persistence !== 'all' ||
    filters.confidence !== 'all' ||
    filters.anomaly !== 'all' ||
    filters.search !== '';

  return (
    <div className="glass-panel p-3 sm:p-4 rounded-xl flex flex-wrap items-center justify-between gap-3 text-xs">
      
      {/* Search Bar */}
      <div className="relative flex-1 min-w-[200px] max-w-sm">
        <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
        <input
          type="text"
          placeholder="Search by ID, facility, landcover..."
          value={filters.search}
          onChange={(e) => updateFilter('search', e.target.value)}
          className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700/60 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/40"
        />
      </div>

      {/* Dropdown Filters */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Classification */}
        <div className="flex items-center gap-1.5">
          <label className="text-[11px] font-medium text-slate-400 hidden sm:inline">Type:</label>
          <select
            value={filters.classification}
            onChange={(e) => updateFilter('classification', e.target.value)}
            className="px-2.5 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700/60 text-slate-200 focus:outline-none focus:border-cyan-500/60"
          >
            <option value="all">All Classifications</option>
            <option value="industrial_heat_source">Industrial Heat Source</option>
            <option value="persistent_industrial">Persistent Industrial</option>
            <option value="agricultural_burning">Agricultural Burning</option>
            <option value="natural_fire">Natural Fire</option>
            <option value="unclassified">Unclassified</option>
          </select>
        </div>

        {/* Priority */}
        <div className="flex items-center gap-1.5">
          <label className="text-[11px] font-medium text-slate-400 hidden sm:inline">Priority:</label>
          <select
            value={filters.priority}
            onChange={(e) => updateFilter('priority', e.target.value)}
            className="px-2.5 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700/60 text-slate-200 focus:outline-none focus:border-cyan-500/60"
          >
            <option value="all">All Priorities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="moderate">Moderate</option>
            <option value="low">Low</option>
          </select>
        </div>

        {/* Persistence */}
        <div className="flex items-center gap-1.5">
          <label className="text-[11px] font-medium text-slate-400 hidden sm:inline">Persistence:</label>
          <select
            value={filters.persistence}
            onChange={(e) => updateFilter('persistence', e.target.value)}
            className="px-2.5 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700/60 text-slate-200 focus:outline-none focus:border-cyan-500/60"
          >
            <option value="all">All Persistence</option>
            <option value="persistent">Persistent</option>
            <option value="non-persistent">Transient / Non-persistent</option>
          </select>
        </div>

        {/* Confidence */}
        <div className="flex items-center gap-1.5">
          <label className="text-[11px] font-medium text-slate-400 hidden sm:inline">Confidence:</label>
          <select
            value={filters.confidence}
            onChange={(e) => updateFilter('confidence', e.target.value)}
            className="px-2.5 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700/60 text-slate-200 focus:outline-none focus:border-cyan-500/60"
          >
            <option value="all">All Confidence</option>
            <option value="high">High</option>
            <option value="nominal">Nominal</option>
            <option value="low">Low</option>
          </select>
        </div>

        {/* ML Isolation Forest Anomaly */}
        <div className="flex items-center gap-1.5">
          <label className="text-[11px] font-medium text-slate-400 hidden sm:inline">ML Model:</label>
          <select
            value={filters.anomaly}
            onChange={(e) => updateFilter('anomaly', e.target.value)}
            className="px-2.5 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700/60 text-slate-200 focus:outline-none focus:border-cyan-500/60"
          >
            <option value="all">All ML Status</option>
            <option value="anomaly">Outlier Anomaly</option>
            <option value="normal">Normal Thermal</option>
          </select>
        </div>

        {/* Reset Button */}
        {hasActiveFilters && (
          <button
            type="button"
            onClick={handleReset}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 hover:text-white border border-slate-700/50 transition-colors"
            title="Reset Filters"
          >
            <RotateCcw className="h-3 w-3" />
            <span>Reset</span>
          </button>
        )}
      </div>

      {/* Count pill */}
      <div className="text-[11px] font-mono text-slate-400 ml-auto flex items-center gap-1.5">
        <span className="text-cyan-300 font-semibold">{totalFiltered}</span>
        <span>of</span>
        <span>{totalEvents} events</span>
      </div>

    </div>
  );
};

export default FilterBar;
