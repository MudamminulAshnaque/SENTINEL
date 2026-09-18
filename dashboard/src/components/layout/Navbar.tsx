import React from 'react';
import { 
  LayoutDashboard, 
  SearchCode, 
  Inbox, 
  BarChart3, 
  Settings2, 
  RadioTower
} from 'lucide-react';
import type { BackendConfig } from '../../types/intelligence';

export type ActiveTab = 'dashboard' | 'analyzer' | 'sandbox' | 'tickets' | 'analytics';

interface NavbarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  backendConfig: BackendConfig;
  onOpenBackendModal: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  backendConfig,
  onOpenBackendModal,
}) => {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-[#07090E]/95 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3 cursor-pointer select-none" onClick={() => setActiveTab('dashboard')}>
          <div className="w-10 h-10 rounded-xl overflow-hidden bg-slate-900/90 border border-cyan-500/40 p-0.5 flex items-center justify-center shadow-glow-cyan transition hover:scale-105">
            <img 
              src="/sentinel-logo.png" 
              alt="SENTINEL AI" 
              className="w-full h-full object-contain rounded-lg"
            />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-lg tracking-wider text-white">
                SENTINEL
              </span>
              <span className="text-[11px] font-bold font-mono px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                AI
              </span>
            </div>
            <span className="text-[9px] font-mono text-slate-400 tracking-wider">
              CYBER & CX INTELLIGENCE
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="hidden md:flex items-center gap-1 bg-slate-950/80 p-1 rounded-xl border border-white/10">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'dashboard'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            <span>Command Center</span>
          </button>

          <button
            onClick={() => setActiveTab('analyzer')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'analyzer'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <SearchCode className="w-4 h-4" />
            <span>Analyzer</span>
          </button>

          <button
            onClick={() => setActiveTab('sandbox')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'sandbox'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <RadioTower className="w-4 h-4" />
            <span>URL Sandbox</span>
          </button>

          <button
            onClick={() => setActiveTab('tickets')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'tickets'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <Inbox className="w-4 h-4" />
            <span>Triage Queue</span>
          </button>

          <button
            onClick={() => setActiveTab('analytics')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'analytics'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            <span>Analytics</span>
          </button>
        </nav>

        {/* Backend Connect Pill */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={onOpenBackendModal}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono transition-all ${
              backendConfig.useLiveBackend
                ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300 hover:bg-emerald-900/60'
                : 'bg-slate-900 border-white/10 text-slate-300 hover:text-white'
            }`}
            title="Configure Backend Server"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                backendConfig.useLiveBackend ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
              }`}
            />
            <span className="hidden sm:inline">
              {backendConfig.useLiveBackend ? 'BACKEND CONNECTED' : 'MOCK MODE'}
            </span>
            <span className="sm:hidden">
              {backendConfig.useLiveBackend ? 'LIVE' : 'MOCK'}
            </span>
            <Settings2 className="w-3.5 h-3.5 text-slate-400" />
          </button>
        </div>
      </div>

      {/* Mobile Tab Bar */}
      <div className="md:hidden flex items-center justify-around border-t border-white/5 bg-[#090D16] py-2 px-1 text-[11px]">
        <button
          onClick={() => setActiveTab('dashboard')}
          className={`flex flex-col items-center gap-1 py-1 px-2 rounded ${
            activeTab === 'dashboard' ? 'text-cyan-400 font-semibold' : 'text-slate-400'
          }`}
        >
          <LayoutDashboard className="w-4 h-4" />
          <span>Dashboard</span>
        </button>
        <button
          onClick={() => setActiveTab('analyzer')}
          className={`flex flex-col items-center gap-1 py-1 px-2 rounded ${
            activeTab === 'analyzer' ? 'text-cyan-400 font-semibold' : 'text-slate-400'
          }`}
        >
          <SearchCode className="w-4 h-4" />
          <span>Analyzer</span>
        </button>
        <button
          onClick={() => setActiveTab('sandbox')}
          className={`flex flex-col items-center gap-1 py-1 px-2 rounded ${
            activeTab === 'sandbox' ? 'text-cyan-400 font-semibold' : 'text-slate-400'
          }`}
        >
          <RadioTower className="w-4 h-4" />
          <span>Sandbox</span>
        </button>
        <button
          onClick={() => setActiveTab('tickets')}
          className={`flex flex-col items-center gap-1 py-1 px-2 rounded ${
            activeTab === 'tickets' ? 'text-cyan-400 font-semibold' : 'text-slate-400'
          }`}
        >
          <Inbox className="w-4 h-4" />
          <span>Triage</span>
        </button>
        <button
          onClick={() => setActiveTab('analytics')}
          className={`flex flex-col items-center gap-1 py-1 px-2 rounded ${
            activeTab === 'analytics' ? 'text-cyan-400 font-semibold' : 'text-slate-400'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          <span>Analytics</span>
        </button>
      </div>
    </header>
  );
};
