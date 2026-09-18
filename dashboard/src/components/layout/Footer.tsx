import React from 'react';
import { Terminal, Cpu, Lock } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full border-t border-white/10 bg-[#06080E] py-8 text-xs text-slate-400">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-slate-900 border border-cyan-500/30 overflow-hidden flex items-center justify-center p-0.5">
            <img src="/sentinel-logo.png" alt="SENTINEL AI" className="w-full h-full object-contain" />
          </div>
          <div>
            <span className="font-bold text-slate-200">SENTINEL AI Platform</span>
            <p className="text-[11px] text-slate-500">
              Customer Support Intelligence & Threat Detection System
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 text-[11px] font-mono text-slate-500">
          <span className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" /> WebGL 3D Engine
          </span>
          <span>•</span>
          <span className="flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-emerald-400" /> Zero-Trust NLP Guardrails
          </span>
          <span>•</span>
          <span className="flex items-center gap-1.5">
            <Terminal className="w-3.5 h-3.5 text-rose-400" /> MITRE ATT&CK T1566 / T1583
          </span>
        </div>
      </div>
    </footer>
  );
};
