import React from 'react';
import { 
  HeartHandshake, 
  ShieldAlert, 
  ChevronRight, 
  Mail, 
  MessageSquare, 
  FileText, 
  Share2, 
  Globe, 
  Activity, 
  Zap
} from 'lucide-react';
import { ThreatGlobe3D } from '../canvas/ThreatGlobe3D';
import type { ExecutiveMetrics, SupportTicketItem } from '../../types/intelligence';
import type { ActiveTab } from '../layout/Navbar';

interface CommandCenterProps {
  metrics: ExecutiveMetrics;
  recentTickets: SupportTicketItem[];
  onSelectTicket: (ticket: SupportTicketItem) => void;
  setActiveTab: (tab: ActiveTab) => void;
}

export const CommandCenter: React.FC<CommandCenterProps> = ({
  metrics,
  recentTickets,
  onSelectTicket,
  setActiveTab,
}) => {
  // Derived from real ticket data (not hardcoded): a quarantined/escalated
  // ticket in the current queue means CRITICAL; any blocked threat at all
  // (without quarantine) is HIGH; otherwise CLEAN. Drives the globe's ring
  // color for real, instead of the fixed 'CLEAN' string it used before.
  const activeThreatLevel: 'CLEAN' | 'HIGH' | 'CRITICAL' =
    metrics.quarantinedCount > 0 ? 'CRITICAL'
    : metrics.totalThreatsBlocked > 0 ? 'HIGH'
    : 'CLEAN';

  return (
    <div className="space-y-6 pb-12">
      {/* Clean Minimal Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Command Center</h1>
          <p className="text-xs text-slate-400 mt-0.5">Real-time support intelligence and security threat overview</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('analyzer')}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-cyan-600/30 hover:bg-cyan-600/50 border border-cyan-500/40 text-cyan-200 text-xs font-semibold transition"
          >
            <Zap className="w-3.5 h-3.5" />
            <span>Analyze Interaction</span>
          </button>
          <button
            onClick={() => setActiveTab('sandbox')}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-white/10 text-slate-300 text-xs font-semibold transition"
          >
            <Globe className="w-3.5 h-3.5 text-cyan-400" />
            <span>URL Sandbox</span>
          </button>
        </div>
      </div>

      {/* Dual Telemetry Metric Ribbons */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Left Column: Customer Support Intelligence */}
        <div className="glass-panel p-5 rounded-2xl">
          <div className="flex items-center gap-2 pb-3 border-b border-white/5 mb-4">
            <HeartHandshake className="w-4 h-4 text-cyan-400" />
            <h2 className="text-xs font-mono uppercase tracking-wider font-bold text-cyan-300">
              Customer Support Intelligence
            </h2>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-[#0A0E18] p-3 rounded-xl border border-white/5">
              <span className="text-[10px] text-slate-400 block font-mono">ESTIMATED CSAT</span>
              <div className="text-xl font-bold text-white font-mono mt-1">
                {metrics.averageCsatEstimate ? `${metrics.averageCsatEstimate} / 5.0` : '--'}
              </div>
            </div>

            <div className="bg-[#0A0E18] p-3 rounded-xl border border-white/5">
              <span className="text-[10px] text-slate-400 block font-mono">FRUSTRATION RATE</span>
              <div className="text-xl font-bold text-amber-400 font-mono mt-1">
                {metrics.averageFrustrationRate}%
              </div>
            </div>

            <div className="bg-[#0A0E18] p-3 rounded-xl border border-white/5">
              <span className="text-[10px] text-slate-400 block font-mono">CHURN DEFLECTED</span>
              <div className="text-xl font-bold text-emerald-400 font-mono mt-1">
                {metrics.churnRiskDeflectedCount}
              </div>
            </div>

            <div className="bg-[#0A0E18] p-3 rounded-xl border border-white/5">
              <span className="text-[10px] text-slate-400 block font-mono">TOTAL PROCESSED</span>
              <div className="text-xl font-bold text-white font-mono mt-1">
                {metrics.totalScanned}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Cybersecurity Threat Intelligence */}
        <div className="glass-panel p-5 rounded-2xl">
          <div className="flex items-center gap-2 pb-3 border-b border-white/5 mb-4">
            <ShieldAlert className="w-4 h-4 text-rose-400" />
            <h2 className="text-xs font-mono uppercase tracking-wider font-bold text-rose-300">
              Cybersecurity Threat Intelligence
            </h2>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-[#0A0E18] p-3 rounded-xl border border-white/5">
              <span className="text-[10px] text-slate-400 block font-mono">BLOCK RATE</span>
              <div className="text-xl font-bold text-emerald-400 font-mono mt-1">
                {metrics.phishingBlockRate}%
              </div>
            </div>

            <div className="bg-[#0A0E18] p-3 rounded-xl border border-white/5">
              <span className="text-[10px] text-slate-400 block font-mono">THREATS BLOCKED</span>
              <div className="text-xl font-bold text-rose-400 font-mono mt-1">
                {metrics.totalThreatsBlocked}
              </div>
            </div>

            <div className="bg-[#0A0E18] p-3 rounded-xl border border-white/5">
              <span className="text-[10px] text-slate-400 block font-mono">SOCIAL ENGR.</span>
              <div className="text-xl font-bold text-amber-400 font-mono mt-1">
                {metrics.socialEngineeringDetected}
              </div>
            </div>

            <div className="bg-[#0A0E18] p-3 rounded-xl border border-white/5">
              <span className="text-[10px] text-slate-400 block font-mono">INSPECTION SPEED</span>
              <div className="text-xl font-bold text-cyan-400 font-mono mt-1">
                {metrics.meanTimeToDetectMs} ms
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 3D Interactive Telemetry Globe & Live Channel Feed Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* 3D Threat Globe visualizer (7 cols) */}
        <div className="lg:col-span-7">
          <ThreatGlobe3D threatCount={metrics.totalThreatsBlocked} activeThreatLevel={activeThreatLevel} />
        </div>

        {/* Live Multi-Channel Inbound Queue Feed (5 cols) */}
        <div className="lg:col-span-5 glass-panel p-5 rounded-2xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-4">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />
                <h3 className="text-xs font-mono uppercase tracking-wider font-bold text-slate-200">
                  Live Inbound Stream
                </h3>
              </div>
              <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-700/40">
                LIVE
              </span>
            </div>

            <div className="space-y-3 overflow-y-auto max-h-[320px] pr-1">
              {recentTickets.length === 0 ? (
                <div className="p-8 text-center text-slate-500 font-mono text-xs">
                  Awaiting inbound interactions from backend...
                </div>
              ) : (
                recentTickets.slice(0, 4).map((ticket) => {
                  const isThreat = ticket.threatLevel === 'CRITICAL' || ticket.threatLevel === 'HIGH' || ticket.threatLevel === 'MALICIOUS';
                  const channelIcon = {
                    email: <Mail className="w-3.5 h-3.5" />,
                    chat: <MessageSquare className="w-3.5 h-3.5" />,
                    ticket: <FileText className="w-3.5 h-3.5" />,
                    social: <Share2 className="w-3.5 h-3.5" />,
                    contact_form: <FileText className="w-3.5 h-3.5" />,
                    url_scan: <Globe className="w-3.5 h-3.5" />,
                  }[ticket.channel];

                  return (
                    <div
                      key={ticket.id}
                      onClick={() => {
                        onSelectTicket(ticket);
                        setActiveTab('analyzer');
                      }}
                      className={`p-3 rounded-xl border transition cursor-pointer ${
                        isThreat
                          ? 'bg-rose-950/20 hover:bg-rose-950/35 border-rose-500/25'
                          : 'bg-[#0E131F]/80 hover:bg-slate-800/60 border-white/5'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className="p-1 rounded bg-slate-800 text-slate-300">
                            {channelIcon}
                          </span>
                          <span className="text-xs font-semibold text-white truncate max-w-[140px]">
                            {ticket.customerName}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                              isThreat
                                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                                : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            }`}
                          >
                            {ticket.threatLevel}
                          </span>
                          <span className="text-[10px] font-mono px-1 rounded bg-slate-800 text-slate-400">
                            {ticket.supportPriority}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-slate-300 font-medium line-clamp-1">
                        {ticket.subject}
                      </p>
                      <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2 font-mono">
                        <span>{ticket.timestamp}</span>
                        <span className="text-cyan-400 flex items-center gap-1 hover:underline">
                          Inspect <ChevronRight className="w-3 h-3" />
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <button
            onClick={() => setActiveTab('tickets')}
            className="w-full mt-4 py-2 px-3 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-white/5 text-xs text-slate-300 flex items-center justify-center gap-2 transition"
          >
            <span>View All Incidents</span>
          </button>
        </div>
      </div>
    </div>
  );
};
