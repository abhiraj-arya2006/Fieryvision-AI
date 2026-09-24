import React from 'react';
import { 
  Flame, 
  Factory, 
  Clock, 
  TreePine, 
  Wheat, 
  AlertTriangle 
} from 'lucide-react';
import type { StatisticsResponse, CanonicalEvent } from '../types';

interface StatsSummaryBarProps {
  stats?: StatisticsResponse | null;
  events?: CanonicalEvent[] | null;
  selectedFilter?: string;
  onSelectFilter?: (filterType: string, value: string) => void;
}

export const StatsSummaryBar: React.FC<StatsSummaryBarProps> = ({
  stats,
  events = [],
  selectedFilter,
  onSelectFilter,
}) => {
  // If stats endpoint not ready, calculate fallbacks from active events
  const total = stats?.total_events ?? events?.length ?? 0;
  
  const industrial = stats?.industrial_events ?? 
    (events || []).filter(e => (e.classification || '').toLowerCase().includes('industrial')).length;

  const persistent = stats?.persistent_events ?? 
    (events || []).filter(e => {
      const p = (e.persistence || '').toLowerCase();
      return p === 'persistent' || p === 'high_persistence' || p === 'recurrent_heat_source' || p === 'true';
    }).length;

  const natural = stats?.natural_events ?? 
    (events || []).filter(e => (e.classification || '').toLowerCase().includes('natural')).length;

  const agricultural = stats?.agricultural_events ?? 
    (events || []).filter(e => (e.classification || '').toLowerCase().includes('agricultural')).length;

  const highPriority = (stats?.critical_priority_events || 0) + (stats?.high_priority_events || 0) || 
    (events || []).filter(e => {
      const p = (e.priority || '').toLowerCase();
      return p === 'critical' || p === 'high';
    }).length;

  const cards = [
    {
      id: 'active',
      label: 'ACTIVE EVENTS',
      value: total,
      icon: Flame,
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10',
      borderColor: 'border-cyan-500/25',
      filterType: 'classification',
      filterVal: 'all',
    },
    {
      id: 'industrial',
      label: 'INDUSTRIAL SOURCES',
      value: industrial,
      icon: Factory,
      color: 'text-red-400',
      bgColor: 'bg-red-500/10',
      borderColor: 'border-red-500/25',
      filterType: 'classification',
      filterVal: 'industrial',
    },
    {
      id: 'persistent',
      label: 'PERSISTENT SOURCES',
      value: persistent,
      icon: Clock,
      color: 'text-orange-400',
      bgColor: 'bg-orange-500/10',
      borderColor: 'border-orange-500/25',
      filterType: 'persistence',
      filterVal: 'persistent',
    },
    {
      id: 'natural',
      label: 'NATURAL FIRES',
      value: natural,
      icon: TreePine,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
      borderColor: 'border-blue-500/25',
      filterType: 'classification',
      filterVal: 'natural',
    },
    {
      id: 'agricultural',
      label: 'AGRICULTURAL',
      value: agricultural,
      icon: Wheat,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
      borderColor: 'border-emerald-500/25',
      filterType: 'classification',
      filterVal: 'agricultural',
    },
    {
      id: 'priority',
      label: 'HIGH / CRITICAL',
      value: highPriority,
      icon: AlertTriangle,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10',
      borderColor: 'border-amber-500/25',
      filterType: 'priority',
      filterVal: 'high',
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 w-full">
      {cards.map((card) => {
        const Icon = card.icon;
        const isSelected = selectedFilter === card.id;

        return (
          <button
            key={card.id}
            type="button"
            onClick={() => onSelectFilter?.(card.filterType, card.filterVal)}
            className={`flex items-center justify-between p-3 rounded-xl border text-left transition-all ${
              card.bgColor
            } ${card.borderColor} ${
              isSelected ? 'ring-2 ring-cyan-400 scale-[1.02]' : 'hover:border-opacity-50 hover:scale-[1.01]'
            }`}
          >
            <div>
              <div className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
                {card.label}
              </div>
              <div className="text-xl font-bold font-mono text-white mt-0.5">
                {card.value}
              </div>
            </div>
            <div className={`p-2 rounded-lg ${card.bgColor} ${card.color}`}>
              <Icon className="h-4 w-4" />
            </div>
          </button>
        );
      })}
    </div>
  );
};

export default StatsSummaryBar;
