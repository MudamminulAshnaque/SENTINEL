import React, { useState } from 'react';
import { 
  Inbox, 
  Search, 
  Mail, 
  MessageSquare, 
  FileText, 
  Share2, 
  Globe, 
  ChevronRight, 
  Check
} from 'lucide-react';
import type { SupportTicketItem } from '../../types/intelligence';

interface TicketQueueProps {
  tickets: SupportTicketItem[];
  onSelectTicket: (ticket: SupportTicketItem) => void;
  onUpdateTicketStatus: (ticketId: string, status: SupportTicketItem['status']) => void;
}

export const TicketQueue: React.FC<TicketQueueProps> = ({
  tickets,
  onSelectTicket,
  onUpdateTicketStatus,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedThreatFilter, setSelectedThreatFilter] = useState<string>('ALL');
  const [selectedPriorityFilter, setSelectedPriorityFilter] = useState<string>('ALL');
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>('ALL');
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const filteredTickets = tickets.filter((t) => {
    const matchesSearch =
      t.customerName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.customerEmail.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.id.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesThreat =
      selectedThreatFilter === 'ALL' || t.threatLevel === selectedThreatFilter;

    const matchesPriority =
      selectedPriorityFilter === 'ALL' || t.supportPriority === selectedPriorityFilter;

    const matchesStatus =
      selectedStatusFilter === 'ALL' || t.status === selectedStatusFilter;

    return matchesSearch && matchesThreat && matchesPriority && matchesStatus;
  });

  const handleStatusChange = (ticketId: string, newStatus: SupportTicketItem['status'], e: React.MouseEvent) => {
    e.stopPropagation();
    onUpdateTicketStatus(ticketId, newStatus);
    setActionNotice(`Ticket ${ticketId} updated to ${newStatus}`);
    setTimeout(() => setActionNotice(null), 2500);
  };

  const getChannelIcon = (channel: string) => {
    switch (channel) {
      case 'email': return <Mail className="w-3.5 h-3.5" />;
      case 'chat': return <MessageSquare className="w-3.5 h-3.5" />;
      case 'ticket': return <FileText className="w-3.5 h-3.5" />;
      case 'social': return <Share2 className="w-3.5 h-3.5" />;
      default: return <Globe className="w-3.5 h-3.5" />;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Action Toast Notice */}
      {actionNotice && (
        <div className="fixed bottom-6 right-6 z-50 bg-emerald-950 border border-emerald-500/50 text-emerald-300 px-4 py-2.5 rounded-xl shadow-2xl flex items-center gap-2 font-mono text-xs">
          <Check className="w-4 h-4 text-emerald-400" />
          <span>{actionNotice}</span>
        </div>
      )}

      {/* Header & Stats Banner */}
      <div className="glass-panel p-6 rounded-2xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Inbox className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-mono uppercase tracking-wider font-bold text-cyan-300">
              Triage Queue
            </h2>
          </div>

          <div className="flex items-center gap-3">
            <div className="px-3 py-1.5 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs font-mono">
              <span className="font-bold">
                {tickets.filter((t) => t.status === 'QUARANTINED').length}
              </span>{' '}
              Quarantined
            </div>
            <div className="px-3 py-1.5 rounded-xl bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 text-xs font-mono">
              <span className="font-bold">
                {tickets.filter((t) => t.status === 'OPEN').length}
              </span>{' '}
              Active Inbound
            </div>
          </div>
        </div>

        {/* Filter Controls Bar */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pt-4">
          {/* Search Box */}
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by customer name, email, subject, or ticket ID..."
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-[#090D18] border border-white/10 text-slate-200 text-xs font-mono focus:outline-none focus:border-cyan-500/50"
            />
          </div>

          {/* Dropdown Filters */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {/* Threat Filter */}
            <div className="flex items-center gap-1.5 bg-[#090D18] px-2.5 py-1.5 rounded-xl border border-white/5">
              <span className="text-[10px] font-mono text-slate-400">THREAT:</span>
              <select
                value={selectedThreatFilter}
                onChange={(e) => setSelectedThreatFilter(e.target.value)}
                className="bg-transparent text-slate-200 text-xs font-mono focus:outline-none cursor-pointer"
              >
                <option value="ALL">All Threats</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MALICIOUS">Malicious</option>
                <option value="CLEAN">Clean Only</option>
              </select>
            </div>

            {/* Support Priority Filter */}
            <div className="flex items-center gap-1.5 bg-[#090D18] px-2.5 py-1.5 rounded-xl border border-white/5">
              <span className="text-[10px] font-mono text-slate-400">PRIORITY:</span>
              <select
                value={selectedPriorityFilter}
                onChange={(e) => setSelectedPriorityFilter(e.target.value)}
                className="bg-transparent text-slate-200 text-xs font-mono focus:outline-none cursor-pointer"
              >
                <option value="ALL">All Priorities</option>
                <option value="P1">P1 (Urgent)</option>
                <option value="P2">P2 (High)</option>
                <option value="P3">P3 (Medium)</option>
                <option value="P4">P4 (Low)</option>
              </select>
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-1.5 bg-[#090D18] px-2.5 py-1.5 rounded-xl border border-white/5">
              <span className="text-[10px] font-mono text-slate-400">STATUS:</span>
              <select
                value={selectedStatusFilter}
                onChange={(e) => setSelectedStatusFilter(e.target.value)}
                className="bg-transparent text-slate-200 text-xs font-mono focus:outline-none cursor-pointer"
              >
                <option value="ALL">All Statuses</option>
                <option value="QUARANTINED">Quarantined</option>
                <option value="OPEN">Open</option>
                <option value="IN_REVIEW">In Review</option>
                <option value="ESCALATED_SECOPS">SecOps Escalated</option>
                <option value="RESOLVED">Resolved</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Ticket Table / Card List */}
      <div className="space-y-3">
        {filteredTickets.length === 0 ? (
          <div className="glass-panel p-12 rounded-2xl text-center">
            <Inbox className="w-8 h-8 text-slate-500 mx-auto mb-2" />
            <p className="text-slate-300 text-sm font-semibold">No tickets match the selected filters</p>
            <p className="text-slate-500 text-xs mt-1">Try resetting the search or filter criteria</p>
          </div>
        ) : (
          filteredTickets.map((ticket) => {
            const isCriticalThreat =
              ticket.threatLevel === 'CRITICAL' ||
              ticket.threatLevel === 'HIGH' ||
              ticket.threatLevel === 'MALICIOUS';

            return (
              <div
                key={ticket.id}
                onClick={() => onSelectTicket(ticket)}
                className={`p-4 rounded-2xl border transition-all cursor-pointer group ${
                  isCriticalThreat
                    ? 'bg-[#120B13]/90 hover:bg-[#180E1A] border-rose-500/30 shadow-sm'
                    : 'bg-[#0A0E18]/80 hover:bg-[#0E1424] border-white/5'
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  {/* Left block: Channel, ID, Customer, Subject */}
                  <div className="flex items-start gap-3.5 flex-1 min-w-0">
                    <div className="p-2 rounded-xl bg-slate-900 border border-white/10 text-cyan-400 shrink-0 mt-0.5">
                      {getChannelIcon(ticket.channel)}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span className="text-xs font-mono font-bold text-slate-300">
                          {ticket.id}
                        </span>
                        <span className="text-xs font-bold text-white truncate max-w-[180px]">
                          {ticket.customerName}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400 truncate max-w-[200px]">
                          &lt;{ticket.customerEmail}&gt;
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-cyan-300">
                          {ticket.customerTier}
                        </span>
                      </div>

                      <h3 className="text-sm font-semibold text-slate-100 group-hover:text-cyan-300 transition truncate">
                        {ticket.subject}
                      </h3>

                      <p className="text-xs text-slate-400 line-clamp-1 mt-0.5">
                        {ticket.snippet}
                      </p>
                    </div>
                  </div>

                  {/* Middle / Right Badges & Actions */}
                  <div className="flex flex-wrap items-center gap-3 shrink-0">
                    {/* Threat Badge */}
                    <div className="text-right">
                      <span
                        className={`text-[10px] font-mono font-bold px-2 py-1 rounded-md border uppercase inline-block ${
                          isCriticalThreat
                            ? 'bg-rose-950/80 text-rose-300 border-rose-500/40 shadow-glow-rose'
                            : 'bg-emerald-950/80 text-emerald-300 border-emerald-500/30'
                        }`}
                      >
                        {ticket.threatLevel}
                      </span>
                    </div>

                    {/* Support Priority Badge */}
                    <span
                      className={`text-[11px] font-mono font-bold px-2 py-1 rounded-md ${
                        ticket.supportPriority === 'P1'
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          : ticket.supportPriority === 'P2'
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : 'bg-slate-800 text-slate-300'
                      }`}
                    >
                      {ticket.supportPriority}
                    </span>

                    {/* Status Pill */}
                    <span
                      className={`text-[10px] font-mono uppercase px-2 py-1 rounded-md border ${
                        ticket.status === 'QUARANTINED'
                          ? 'bg-rose-900/40 text-rose-300 border-rose-600/50'
                          : ticket.status === 'RESOLVED'
                          ? 'bg-emerald-900/40 text-emerald-300 border-emerald-500/30'
                          : 'bg-slate-900 text-slate-300 border-white/10'
                      }`}
                    >
                      {ticket.status}
                    </span>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                      {ticket.status === 'QUARANTINED' ? (
                        <button
                          onClick={(e) => handleStatusChange(ticket.id, 'RESOLVED', e)}
                          className="px-2.5 py-1 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/40 border border-emerald-500/40 text-emerald-300 text-xs font-mono transition"
                          title="Neutralize & Resolve"
                        >
                          Resolve
                        </button>
                      ) : (
                        <button
                          onClick={(e) => handleStatusChange(ticket.id, 'QUARANTINED', e)}
                          className="px-2.5 py-1 rounded-lg bg-rose-600/20 hover:bg-rose-600/40 border border-rose-500/40 text-rose-300 text-xs font-mono transition"
                          title="Isolate Threat"
                        >
                          Quarantine
                        </button>
                      )}

                      <button
                        onClick={() => onSelectTicket(ticket)}
                        className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-400 transition"
                        title="Open in Deep Analyzer"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
