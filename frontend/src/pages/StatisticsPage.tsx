import React from 'react';
import { useStatistics } from '../hooks/useStatistics';
import { useActiveEvents } from '../hooks/useActiveEvents';
import { 
  BarChart, 
  Bar, 
  PieChart, 
  Pie, 
  Cell, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  Legend 
} from 'recharts';
import { BarChart3, PieChart as PieIcon, Cpu, RefreshCw, AlertCircle } from 'lucide-react';

const COLORS = {
  red: '#ff4d4d',
  orange: '#ff9b3d',
  emerald: '#53d88b',
  blue: '#4fa7ff',
  cyan: '#38bdf8',
  slate: '#94a3b8',
  amber: '#f59e0b',
};

export const StatisticsPage: React.FC = () => {
  const { data: stats, loading: statsLoading, error: statsError, refresh: refreshStats } = useStatistics();
  const { data: eventsData, refresh: refreshEvents } = useActiveEvents();

  const events = eventsData?.events || [];

  const handleRefresh = () => {
    refreshStats();
    refreshEvents();
  };

  // Pie chart data for event classification
  const classificationData = [
    { name: 'Industrial Heat', value: stats?.industrial_events || 0, color: COLORS.red },
    { name: 'Persistent Sources', value: stats?.persistent_events || 0, color: COLORS.orange },
    { name: 'Agricultural Burning', value: stats?.agricultural_events || 0, color: COLORS.emerald },
    { name: 'Natural / Forest', value: stats?.natural_events || 0, color: COLORS.blue },
    { name: 'Unclassified', value: stats?.unclassified_events || 0, color: COLORS.slate },
  ].filter((item) => item.value > 0);

  // Bar chart data for risk priorities
  const priorityData = [
    { name: 'Critical', count: stats?.critical_priority_events || 0, fill: COLORS.red },
    { name: 'High', count: stats?.high_priority_events || 0, fill: COLORS.orange },
    { name: 'Moderate', count: stats?.moderate_priority_events || 0, fill: COLORS.amber },
    { name: 'Low', count: stats?.low_priority_events || 0, fill: COLORS.emerald },
  ];

  // ML Isolation Forest Anomaly distribution from active events
  const anomalyCount = events.filter((e) => e.is_anomaly || e.anomaly_flag).length;
  const normalCount = Math.max(0, events.length - anomalyCount);

  const mlData = [
    { name: 'ML Outliers Flagged', value: anomalyCount, fill: COLORS.red },
    { name: 'Baseline Thermal', value: normalCount, fill: COLORS.cyan },
  ];

  return (
    <div className="flex-1 p-3 sm:p-5 lg:p-6 w-full space-y-6">
      
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
              <BarChart3 className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                Fire Intelligence Analytics & Statistics
              </h1>
              <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
                Aggregated telemetry, classification breakdown, and priority statistics for global monitoring.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={handleRefresh}
          className="px-3.5 py-1.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-xs font-semibold text-slate-200 flex items-center gap-1.5 transition-colors"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${statsLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Data</span>
        </button>
      </div>

      {statsError && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-3 text-red-200 text-xs">
          <AlertCircle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-red-300">Statistics Unavailable</h4>
            <p className="mt-0.5 text-red-300/80">{statsError}</p>
          </div>
        </div>
      )}

      {/* Top 4 KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-5 rounded-2xl border border-cyan-500/20">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Total Monitored Events
          </div>
          <div className="text-3xl font-bold font-mono text-white mt-1">
            {stats?.total_events || 0}
          </div>
          <div className="text-[11px] text-cyan-400 mt-2 font-mono">
            Mode: {stats?.classification_mode || 'evidence_based'}
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-red-500/20">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            High / Critical Risk
          </div>
          <div className="text-3xl font-bold font-mono text-red-400 mt-1">
            {(stats?.critical_priority_events || 0) + (stats?.high_priority_events || 0)}
          </div>
          <div className="text-[11px] text-slate-400 mt-2 font-mono">
            {stats?.critical_priority_events || 0} Critical · {stats?.high_priority_events || 0} High
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-orange-500/20">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Persistent Sources
          </div>
          <div className="text-3xl font-bold font-mono text-orange-400 mt-1">
            {stats?.persistent_events || 0}
          </div>
          <div className="text-[11px] text-slate-400 mt-2 font-mono">
            Multi-day recurring thermal signatures
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-emerald-500/20">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Classified vs Unclassified
          </div>
          <div className="text-3xl font-bold font-mono text-emerald-400 mt-1">
            {stats?.classified_events || 0}
            <span className="text-sm text-slate-400 font-normal"> / {stats?.total_events || 0}</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-2 font-mono">
            {stats?.unclassified_events || 0} requiring further satellite review
          </div>
        </div>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Classification Breakdown Pie Chart */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4 flex flex-col">
          <div className="flex items-center gap-2 text-sm font-bold text-white border-b border-slate-800 pb-3">
            <PieIcon className="h-4 w-4 text-cyan-400" />
            <span>Classification Distribution</span>
          </div>

          <div className="h-[280px] w-full flex items-center justify-center">
            {classificationData.length === 0 ? (
              <div className="text-xs text-slate-500">No events data available for distribution.</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={classificationData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={95}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {classificationData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(10, 18, 33, 0.95)',
                      borderColor: 'rgba(130, 180, 255, 0.3)',
                      borderRadius: '8px',
                      color: '#fff',
                      fontSize: '12px',
                    }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    height={36}
                    formatter={(value) => <span className="text-xs text-slate-300">{value}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Priority Breakdown Bar Chart */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4 flex flex-col">
          <div className="flex items-center gap-2 text-sm font-bold text-white border-b border-slate-800 pb-3">
            <BarChart3 className="h-4 w-4 text-cyan-400" />
            <span>Priority Threat Breakdown</span>
          </div>

          <div className="h-[280px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={priorityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(10, 18, 33, 0.95)',
                    borderColor: 'rgba(130, 180, 255, 0.3)',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {priorityData.map((entry, index) => (
                    <Cell key={`bar-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

      {/* ML Isolation Forest Insights Card */}
      <div className="glass-panel p-5 rounded-2xl border border-cyan-500/25 space-y-4">
        <div className="flex items-center gap-2 text-sm font-bold text-white border-b border-slate-800 pb-3">
          <Cpu className="h-4 w-4 text-cyan-400" />
          <span>Machine Learning Isolation Forest Model Performance</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-slate-400">Model Architecture</span>
            <div className="text-sm font-semibold text-white">Isolation Forest (Unsupervised)</div>
            <p className="text-slate-400 text-[11px] mt-1">
              Trained on historical satellite FIRMS detections to evaluate anomalous thermal intensity.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-slate-400">Current Outlier Detections</span>
            <div className="text-sm font-semibold text-red-400">
              {anomalyCount} Events Flagged as Anomalies
            </div>
            <div className="flex gap-2 text-[10px] font-mono text-slate-400 mt-1">
              {mlData.map((d, i) => (
                <span key={i} className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: d.fill }}></span>
                  <span>{d.name}: {d.value}</span>
                </span>
              ))}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-slate-400">Inference Engine</span>
            <div className="text-sm font-semibold text-cyan-300">FastAPI ML Service</div>
            <p className="text-slate-400 text-[11px] mt-1">
              Runs server-side on localhost:8000 via Scikit-Learn joblib pipeline.
            </p>
          </div>
        </div>
      </div>

    </div>
  );
};

export default StatisticsPage;
