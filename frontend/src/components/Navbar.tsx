import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Flame, 
  Map as MapIcon, 
  Globe,
  Bot, 
  Factory, 
  BarChart3
} from 'lucide-react';
import { useHealth } from '../hooks/useHealth';

export const Navbar: React.FC = () => {
  const { data: health, online, loading } = useHealth(20000);

  return (
    <header className="sticky top-0 z-[1000] w-full border-b border-[#82b4ff]/20 bg-[#050914]/85 backdrop-blur-md">
      <div className="w-full flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        
        {/* Brand / Logo */}
        <div className="flex items-center gap-3">
          <NavLink to="/" className="flex items-center gap-3 group">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-lg overflow-hidden border border-cyan-500/40 bg-slate-900 shadow-md shadow-cyan-500/10 group-hover:border-cyan-400 transition-all">
              <img 
                src="/assets/logo.jpg" 
                alt="FieryVision Logo" 
                className="h-full w-full object-cover"
                onError={(e) => {
                  // Fallback icon if logo image is unavailable
                  (e.target as HTMLElement).style.display = 'none';
                }}
              />
              <Flame className="absolute h-5 w-5 text-cyan-400 hidden" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight text-white group-hover:text-cyan-300 transition-colors">
                FieryVision <span className="text-cyan-400">AI</span>
              </span>
            </div>
          </NavLink>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 sm:gap-2">
          <NavLink
            to="/hotspots"
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-lg px-3 py-2 text-xs sm:text-sm font-medium transition-all ${
                isActive
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/10 font-bold'
                  : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
              }`
            }
          >
            <Globe className="h-4 w-4 text-cyan-400" />
            <span>Global Hotspots</span>
          </NavLink>

          <NavLink
            to="/map"
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-lg px-3 py-2 text-xs sm:text-sm font-medium transition-all ${
                isActive
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/10 font-bold'
                  : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
              }`
            }
          >
            <MapIcon className="h-4 w-4 text-cyan-400" />
            <span>Live Map</span>
          </NavLink>

          <NavLink
            to="/assistant"
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-lg px-3 py-2 text-xs sm:text-sm font-medium transition-all ${
                isActive
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-sm shadow-cyan-500/10'
                  : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
              }`
            }
          >
            <Bot className="h-4 w-4" />
            <span>AI Assistant</span>
          </NavLink>

          <NavLink
            to="/facilities"
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-lg px-3 py-2 text-xs sm:text-sm font-medium transition-all ${
                isActive
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-sm shadow-cyan-500/10'
                  : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
              }`
            }
          >
            <Factory className="h-4 w-4" />
            <span>Facilities</span>
          </NavLink>

          <NavLink
            to="/statistics"
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-lg px-3 py-2 text-xs sm:text-sm font-medium transition-all ${
                isActive
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-sm shadow-cyan-500/10'
                  : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
              }`
            }
          >
            <BarChart3 className="h-4 w-4" />
            <span>Analytics</span>
          </NavLink>
        </nav>

        {/* Status Pill */}
        <div className="hidden md:flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-full border border-slate-700/60 bg-slate-900/80 px-3 py-1 text-xs">
            <span className="relative flex h-2 w-2">
              {online ? (
                <>
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
                </>
              ) : (
                <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500"></span>
              )}
            </span>
            <span className={`font-mono text-[11px] font-semibold tracking-wider ${online ? 'text-emerald-400' : 'text-red-400'}`}>
              {loading ? 'CHECKING...' : online ? 'API ONLINE' : 'API OFFLINE'}
            </span>
            {health?.data_mode && (
              <span className="border-l border-slate-700 pl-2 text-[10px] text-slate-400 uppercase">
                {health.data_mode}
              </span>
            )}
          </div>
        </div>

      </div>
    </header>
  );
};

export default Navbar;
