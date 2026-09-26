import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { GlobalHotspotsPage } from './pages/GlobalHotspotsPage';
import { MapDashboardPage } from './pages/MapDashboardPage';
import { AssistantPage } from './pages/AssistantPage';
import { FacilitiesPage } from './pages/FacilitiesPage';
import { StatisticsPage } from './pages/StatisticsPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col bg-[#050914] text-[#edf6ff]">
        {/* Navigation Bar */}
        <Navbar />

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col">
          <Routes>
            <Route path="/" element={<GlobalHotspotsPage />} />
            <Route path="/hotspots" element={<GlobalHotspotsPage />} />
            <Route path="/map" element={<MapDashboardPage />} />
            <Route path="/giaspura" element={<MapDashboardPage />} />
            <Route path="/assistant" element={<AssistantPage />} />
            <Route path="/analysis" element={<AssistantPage />} />
            <Route path="/facilities" element={<FacilitiesPage />} />
            <Route path="/statistics" element={<StatisticsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>

        {/* Modern Command-Center Footer */}
        <footer className="border-t border-[#82b4ff]/15 bg-[#050914]/90 py-4 px-4 sm:px-6 lg:px-8 text-xs text-slate-500">
          <div className="w-full flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-400">FieryVision AI</span>
              <span>·</span>
              <span>Industrial Fire Risk Intelligence & Satellite Monitoring</span>
            </div>
            <div className="flex items-center gap-4 text-[11px] font-mono">
              <span>Study Area: Giaspura, Ludhiana, Punjab</span>
              <span>·</span>
              <a 
                href="http://localhost:8000/docs" 
                target="_blank" 
                rel="noreferrer"
                className="hover:text-cyan-400 transition-colors"
              >
                FastAPI Swagger Docs ↗
              </a>
            </div>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
};

export default App;
