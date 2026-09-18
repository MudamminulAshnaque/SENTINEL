import React, { useRef, useState } from 'react';
import { 
  ShieldAlert, 
  CheckCircle2, 
  Copy, 
  Sparkles, 
  Terminal, 
  Zap, 
  Mail, 
  MessageSquare, 
  FileText, 
  Share2, 
  Globe, 
  Check, 
  RefreshCw, 
  Eye, 
  Download
} from 'lucide-react';
import { CyberShield3D } from '../canvas/CyberShield3D';
import { UrlRadarScanner } from '../sandbox/UrlRadarScanner';
import type { ChannelType, DualAnalysisResult } from '../../types/intelligence';
import { aegisApi } from '../../services/api';

interface ConversationAnalyzerProps {
  currentResult: DualAnalysisResult | null;
  onAnalysisUpdate: (result: DualAnalysisResult) => void;
}

export const ConversationAnalyzer: React.FC<ConversationAnalyzerProps> = ({
  currentResult,
  onAnalysisUpdate,
}) => {
  const [activeAnalysisTab, setActiveAnalysisTab] = useState<'threat' | 'support'>('threat');
  const [selectedChannel, setSelectedChannel] = useState<ChannelType>(currentResult?.channel || 'email');
  const [senderInput, setSenderInput] = useState(currentResult?.sender || '');
  const [subjectInput, setSubjectInput] = useState(currentResult?.subject || '');
  const [contentInput, setContentInput] = useState(currentResult?.rawContent || '');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copiedDraft, setCopiedDraft] = useState(false);
  const [copiedIoc, setCopiedIoc] = useState<string | null>(null);
  const [isQuarantined, setIsQuarantined] = useState(currentResult?.threatIntelligence?.secopsActions?.quarantined || false);
  const [isParsingEml, setIsParsingEml] = useState(false);
  const [emlError, setEmlError] = useState<string | null>(null);
  const [emlFileName, setEmlFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Parse an uploaded .eml file and populate the sender/subject/content
  // fields from it. User can still edit before running analysis.
  const handleEmlFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsParsingEml(true);
    setEmlError(null);
    try {
      const parsed = await aegisApi.parseEml(file);
      setSenderInput(parsed.sender);
      setSubjectInput(parsed.subject);
      setContentInput(parsed.text);
      setEmlFileName(file.name);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to parse .eml file.';
      setEmlError(message);
      setEmlFileName(null);
    } finally {
      setIsParsingEml(false);
      // Allow re-selecting the same file name after an error/re-upload.
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Run dynamic analysis
  const handleRunAnalysis = async () => {
    setIsAnalyzing(true);
    setErrorMessage(null);
    try {
      const result = await aegisApi.analyzeConversation({
        channel: selectedChannel,
        text: contentInput,
        subject: subjectInput,
        sender: senderInput,
      });
      setIsQuarantined(result.threatIntelligence.secopsActions.quarantined);
      onAnalysisUpdate(result);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Analysis failed. Check your backend server.';
      setErrorMessage(message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Copy Smart Reply
  const handleCopyReply = () => {
    if (!currentResult) return;
    navigator.clipboard.writeText(currentResult.supportIntelligence.safeSmartReply.body);
    setCopiedDraft(true);
    setTimeout(() => setCopiedDraft(false), 2000);
  };

  // Copy IOC
  const handleCopyIoc = (iocVal: string) => {
    navigator.clipboard.writeText(iocVal);
    setCopiedIoc(iocVal);
    setTimeout(() => setCopiedIoc(null), 2000);
  };

  // Export STIX / JSON
  const handleExportJson = () => {
    if (!currentResult) return;
    const jsonBlob = new Blob([JSON.stringify(currentResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(jsonBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `SENTINEL_ANALYSIS_${currentResult.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const threat = currentResult?.threatIntelligence;
  const support = currentResult?.supportIntelligence;
  const isCriticalThreat = threat ? (threat.threatLevel === 'CRITICAL' || threat.threatLevel === 'HIGH' || threat.threatLevel === 'MALICIOUS') : false;

  return (
    <div className="space-y-6 pb-12">
      {/* Channel Intake Selector Bar */}
      <div className="glass-panel p-3 rounded-2xl flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 bg-[#090D18] p-1 rounded-xl border border-white/5">
          {(
            [
              { id: 'email', label: 'Email (.eml)', icon: <Mail className="w-3.5 h-3.5" /> },
              { id: 'chat', label: 'Live Chat', icon: <MessageSquare className="w-3.5 h-3.5" /> },
              { id: 'ticket', label: 'Support Ticket', icon: <FileText className="w-3.5 h-3.5" /> },
              { id: 'social', label: 'Social DM', icon: <Share2 className="w-3.5 h-3.5" /> },
              { id: 'url_scan', label: 'URL / Link', icon: <Globe className="w-3.5 h-3.5" /> },
            ] as const
          ).map((ch) => (
            <button
              key={ch.id}
              onClick={() => setSelectedChannel(ch.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                selectedChannel === ch.id
                  ? 'bg-gradient-to-r from-cyan-600/30 to-indigo-600/30 text-cyan-300 border border-cyan-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {ch.icon}
              <span>{ch.label}</span>
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
          <span>Channel: <strong className="text-cyan-300 font-semibold">{selectedChannel.toUpperCase()}</strong></span>
        </div>
      </div>

      {/* URL / Link channel routes to the real URL Sandbox Scanner (same
          component and /api/v1/scan-url pipeline used in the Sandbox tab)
          instead of running a bare link through the customer_intelligence
          text pipeline, which was never designed for URL-only input. */}
      {selectedChannel === 'url_scan' ? (
        <UrlRadarScanner />
      ) : (
      /* Main Dual Workspace: Left = Raw / Highlighted Content; Right = Dual Intelligence Output */
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Raw Input & Forensic Highlighter (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="glass-panel p-5 rounded-2xl space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-white/5">
              <span className="text-xs font-mono font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                <Terminal className="w-4 h-4 text-cyan-400" />
                Raw Interaction Payload
              </span>
              <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                Ref: {currentResult?.id || 'AWAITING INPUT'}
              </span>
            </div>

            {/* Error Message Banner if Backend Fails */}
            {errorMessage && (
              <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs font-mono">
                {errorMessage}
              </div>
            )}

            {/* .eml file upload — Email channel only. Parses via the real
                stdlib email parser on the backend and fills the fields
                below, which stay editable before running analysis. */}
            {selectedChannel === 'email' && (
              <div className="space-y-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".eml"
                  onChange={handleEmlFileSelect}
                  className="hidden"
                  id="eml-file-input"
                />
                <label
                  htmlFor="eml-file-input"
                  className={`flex items-center justify-center gap-2 p-3 rounded-xl border border-dashed cursor-pointer transition text-xs font-mono ${
                    isParsingEml
                      ? 'border-cyan-500/40 bg-cyan-950/20 text-cyan-300'
                      : 'border-white/15 bg-[#090D18] text-slate-400 hover:border-cyan-500/40 hover:text-cyan-300'
                  }`}
                >
                  {isParsingEml ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Parsing .eml file...</span>
                    </>
                  ) : emlFileName ? (
                    <>
                      <FileText className="w-3.5 h-3.5 text-emerald-400" />
                      <span>{emlFileName} — fields populated below. Click to replace.</span>
                    </>
                  ) : (
                    <>
                      <Mail className="w-3.5 h-3.5" />
                      <span>Click to upload a .eml file (or paste content manually below)</span>
                    </>
                  )}
                </label>
                {emlError && (
                  <div className="p-2.5 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-300 text-[11px] font-mono">
                    {emlError}
                  </div>
                )}
              </div>
            )}

            {/* Sender & Subject fields */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              <div>
                <label className="text-[10px] font-mono text-slate-400 block mb-1">SENDER ADDRESS / ID</label>
                <input
                  type="text"
                  value={senderInput}
                  onChange={(e) => setSenderInput(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-[#090D18] border border-white/10 text-slate-200 font-mono text-xs focus:outline-none focus:border-cyan-500/50"
                  placeholder="e.g. sender@domain.com"
                />
              </div>
              <div>
                <label className="text-[10px] font-mono text-slate-400 block mb-1">SUBJECT / TOPIC</label>
                <input
                  type="text"
                  value={subjectInput}
                  onChange={(e) => setSubjectInput(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-[#090D18] border border-white/10 text-slate-200 text-xs focus:outline-none focus:border-cyan-500/50"
                  placeholder="e.g. Ticket Subject"
                />
              </div>
            </div>

            {/* Interaction Textarea */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-[10px] font-mono text-slate-400">CONVERSATION / MESSAGE BODY</label>
                <span className="text-[10px] text-slate-500 font-mono">{contentInput.length} chars</span>
              </div>
              <textarea
                rows={9}
                value={contentInput}
                onChange={(e) => setContentInput(e.target.value)}
                className="w-full p-3 rounded-xl bg-[#090D18] border border-white/10 text-slate-200 text-xs font-mono leading-relaxed focus:outline-none focus:border-cyan-500/50 resize-y"
                placeholder="Paste email headers, live chat conversation, customer complaint, or suspicious URL here..."
              />
            </div>

            {/* Execute Deep Analysis Action Bar */}
            <div className="flex items-center gap-2 pt-1">
              <button
                onClick={handleRunAnalysis}
                disabled={isAnalyzing || !contentInput.trim()}
                className="flex-1 flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 disabled:opacity-50 text-white text-xs font-bold shadow-glow-cyan transition active:scale-[0.99]"
              >
                {isAnalyzing ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Inspecting Vector...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    <span>Execute Deep Analysis</span>
                  </>
                )}
              </button>

              <button
                onClick={handleExportJson}
                className="p-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-white/10 text-slate-300 hover:text-white transition"
                title="Export STIX / JSON Telemetry"
              >
                <Download className="w-4 h-4" />
              </button>
            </div>

            {/* Highlighted Forensic Tokens Breakdown */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-mono uppercase tracking-wider text-slate-300 font-semibold flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5 text-cyan-400" />
                  Highlighted Forensic Markers ({currentResult?.highlightedTokens?.length || 0})
                </span>
                <span className="text-[10px] text-slate-500 font-mono">Real-Time Tokens</span>
              </div>

              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {currentResult && currentResult.highlightedTokens.length > 0 ? (
                  currentResult.highlightedTokens.map((token, idx) => (
                    <div
                      key={idx}
                      className={`p-2 rounded-lg border text-xs transition ${
                        token.type === 'threat'
                          ? 'bg-rose-950/30 border-rose-500/30 text-rose-200'
                          : token.type === 'urgency'
                          ? 'bg-amber-950/30 border-amber-500/30 text-amber-200'
                          : token.type === 'url'
                          ? 'bg-rose-900/30 border-rose-500/40 text-rose-300 font-mono'
                          : 'bg-indigo-950/30 border-indigo-500/30 text-indigo-200'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-0.5">
                        <span className="font-semibold truncate max-w-[200px]">{token.text}</span>
                        <span className="text-[9px] font-mono uppercase px-1 rounded bg-black/40">
                          {token.type}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-300">{token.explanation}</p>
                    </div>
                  ))
                ) : (
                  <div className="p-4 rounded-xl bg-[#090D18] border border-white/5 text-center text-slate-500 text-xs font-mono">
                    No tokens flagged yet. Enter text and execute analysis.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Dual Intelligence Breakdown with 3D Hologram (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {/* Top 3D Visualizer & Threat Badge Card */}
          <div
            className={`p-5 rounded-2xl border transition-all ${
              isCriticalThreat ? 'glass-panel-threat' : 'glass-panel-safe'
            }`}
          >
            <div className="grid grid-cols-1 sm:grid-cols-12 gap-4 items-center">
              {/* 3D Core / Hologram Shield */}
              <div className="sm:col-span-5 h-44 flex items-center justify-center">
                <CyberShield3D
                  threatLevel={threat?.threatLevel || 'CLEAN'}
                  phishingScore={threat?.phishingScore || 0}
                />
              </div>

              {/* Threat Severity & Quick Summary */}
              <div className="sm:col-span-7 space-y-2.5">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2.5 py-1 rounded-lg text-xs font-mono font-bold tracking-wide uppercase border ${
                      isCriticalThreat
                        ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                        : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    }`}
                  >
                    STATUS: {threat?.threatLevel || 'READY'} VERDICT
                  </span>
                  <span className="text-xs font-mono text-slate-400">
                    Confidence: {threat?.confidenceScore || 0}%
                  </span>
                </div>

                <h3 className="text-base font-bold text-white leading-snug">
                  {threat?.summaryReasoning || 'Awaiting live interaction analysis from backend API'}
                </h3>

                {threat && (
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {threat.summaryReasoning}
                  </p>
                )}

                {/* SecOps Action Strip */}
                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <button
                    onClick={() => setIsQuarantined(!isQuarantined)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition border ${
                      isQuarantined
                        ? 'bg-rose-600 text-white border-rose-500 shadow-glow-rose'
                        : 'bg-slate-800 text-slate-300 border-white/10 hover:bg-slate-700'
                    }`}
                  >
                    {isQuarantined ? 'ISOLATED IN QUARANTINE' : 'FLAG FOR QUARANTINE'}
                  </button>

                  <span className="text-[11px] text-slate-400 font-mono">
                    Routing: <span className="text-cyan-400">{support?.automatedRouting?.recommendedDepartment || 'Auto Routing Active'}</span>
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Dual Tab Switcher: Threat Intelligence vs Support Intelligence */}
          <div className="glass-panel p-5 rounded-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveAnalysisTab('threat')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold uppercase transition ${
                    activeAnalysisTab === 'threat'
                      ? 'bg-rose-950/60 text-rose-300 border border-rose-500/40 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                  <span>1. Cybersecurity Threat Intelligence</span>
                </button>

                <button
                  onClick={() => setActiveAnalysisTab('support')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold uppercase transition ${
                    activeAnalysisTab === 'support'
                      ? 'bg-cyan-950/60 text-cyan-300 border border-cyan-500/40 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Sparkles className="w-4 h-4 text-cyan-400" />
                  <span>2. Customer Support Intelligence</span>
                </button>
              </div>
            </div>

            {!threat || !support ? (
              <div className="p-12 text-center text-slate-500 font-mono text-xs">
                Awaiting API response... Submit an interaction on the left to display deep threat & support analysis from your backend.
              </div>
            ) : (
              <>
                {/* TAB 1: CYBERSECURITY THREAT INTELLIGENCE */}
                {activeAnalysisTab === 'threat' && (
              <div className="space-y-4">
                {/* Social Engineering Vectors Radar Matrix */}
                <div>
                  <h4 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold mb-2">
                    Social Engineering & Psychological Vectors
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                    <div className="p-2.5 rounded-xl bg-[#090D18] border border-white/5">
                      <span className="text-[10px] font-mono text-slate-400 block">URGENCY COERCION</span>
                      <div className="text-lg font-bold font-mono text-rose-400 mt-0.5">
                        {threat.socialEngineering.urgencyCoercion}%
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full mt-1.5 overflow-hidden">
                        <div
                          className="bg-rose-500 h-full rounded-full"
                          style={{ width: `${threat.socialEngineering.urgencyCoercion}%` }}
                        />
                      </div>
                    </div>

                    <div className="p-2.5 rounded-xl bg-[#090D18] border border-white/5">
                      <span className="text-[10px] font-mono text-slate-400 block">AUTHORITY SPOOFING</span>
                      <div className="text-lg font-bold font-mono text-rose-400 mt-0.5">
                        {threat.socialEngineering.authorityImpersonation}%
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full mt-1.5 overflow-hidden">
                        <div
                          className="bg-rose-500 h-full rounded-full"
                          style={{ width: `${threat.socialEngineering.authorityImpersonation}%` }}
                        />
                      </div>
                    </div>

                    <div className="p-2.5 rounded-xl bg-[#090D18] border border-white/5">
                      <span className="text-[10px] font-mono text-slate-400 block">INTIMIDATION / FEAR</span>
                      <div className="text-lg font-bold font-mono text-amber-400 mt-0.5">
                        {threat.socialEngineering.fearIntimidation}%
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full mt-1.5 overflow-hidden">
                        <div
                          className="bg-amber-500 h-full rounded-full"
                          style={{ width: `${threat.socialEngineering.fearIntimidation}%` }}
                        />
                      </div>
                    </div>

                    <div className="p-2.5 rounded-xl bg-[#090D18] border border-white/5">
                      <span className="text-[10px] font-mono text-slate-400 block">PRETEXT FABRICATION</span>
                      <div className="text-lg font-bold font-mono text-rose-400 mt-0.5">
                        {threat.socialEngineering.pretexting}%
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full mt-1.5 overflow-hidden">
                        <div
                          className="bg-rose-500 h-full rounded-full"
                          style={{ width: `${threat.socialEngineering.pretexting}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* URL & Domain Forensics */}
                {threat.urls.length > 0 && (
                  <div>
                    <h4 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold mb-2">
                      Extracted URL & Domain Forensics ({threat.urls.length})
                    </h4>
                    <div className="space-y-2">
                      {threat.urls.map((u, i) => (
                        <div
                          key={i}
                          className="p-3 rounded-xl bg-[#090D18] border border-rose-500/20 text-xs space-y-2"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="font-mono text-rose-300 font-bold break-all">
                              {u.url}
                            </span>
                            <span className="px-2 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-500/30 font-mono font-bold text-[10px]">
                              {u.sandboxVerdict}
                            </span>
                          </div>

                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono text-slate-400 pt-1 border-t border-white/5">
                            <div>
                              <span className="text-slate-500 block">DOMAIN AGE:</span>
                              <span className="text-slate-200">{u.domainAgeDays} days (Fresh)</span>
                            </div>
                            <div>
                              <span className="text-slate-500 block">TYPOSQUATTING:</span>
                              <span className="text-rose-400">{u.typosquattingTarget || 'N/A'}</span>
                            </div>
                            <div>
                              <span className="text-slate-500 block">IP / LOCATION:</span>
                              <span className="text-slate-200">{u.ipAddress} ({u.serverLocation})</span>
                            </div>
                            <div>
                              <span className="text-slate-500 block">REPUTATION:</span>
                              <span className="text-rose-400 font-bold">{u.reputationScore} / 100</span>
                            </div>
                          </div>

                          {u.redirectHops.length > 0 && (
                            <div className="text-[10px] font-mono bg-black/40 p-2 rounded border border-white/5 text-slate-400">
                              <span className="text-amber-400 font-bold block mb-1">REDIRECT CHAIN:</span>
                              {u.redirectHops.map((hop, hidx) => (
                                <div key={hidx} className="flex items-center gap-1.5 truncate">
                                  <span className="text-slate-600">↳ [{hidx + 1}]</span>
                                  <span className="text-slate-300">{hop}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Indicators of Compromise (IOC) Matrix */}
                <div>
                  <h4 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold mb-2">
                    Extracted IOCs & ATT&CK Signatures ({threat.iocs.length})
                  </h4>
                  <div className="space-y-1.5">
                    {threat.iocs.map((ioc) => (
                      <div
                        key={ioc.id}
                        className="flex items-center justify-between p-2 rounded-lg bg-[#090D18] border border-white/5 text-xs font-mono"
                      >
                        <div className="flex items-center gap-2 overflow-hidden">
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400 text-[10px] font-bold">
                            {ioc.type}
                          </span>
                          <span className="text-slate-200 truncate">{ioc.value}</span>
                          {ioc.mitreTechnique && (
                            <span className="text-[10px] text-slate-500 hidden sm:inline">
                              [{ioc.mitreTechnique}]
                            </span>
                          )}
                        </div>
                        <button
                          onClick={() => handleCopyIoc(ioc.value)}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1 text-[11px] shrink-0 transition"
                        >
                          {copiedIoc === ioc.value ? (
                            <>
                              <Check className="w-3 h-3 text-emerald-400" />
                              <span className="text-emerald-400">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Email Authentication Headers (if present) */}
                {threat.headers && (
                  <div className="p-3 rounded-xl bg-[#090D18] border border-white/5 text-xs font-mono">
                    <span className="text-slate-400 uppercase text-[10px] font-bold block mb-2">
                      Header Security Integrity (SPF / DKIM / DMARC)
                    </span>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="p-2 rounded bg-black/40 border border-white/5">
                        <span className="text-[10px] text-slate-500 block">SPF RECORD</span>
                        <span
                          className={`font-bold ${
                            threat.headers.spfStatus === 'PASS' ? 'text-emerald-400' : 'text-rose-400'
                          }`}
                        >
                          {threat.headers.spfStatus}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-black/40 border border-white/5">
                        <span className="text-[10px] text-slate-500 block">DKIM SIGNATURE</span>
                        <span
                          className={`font-bold ${
                            threat.headers.dkimStatus === 'PASS' ? 'text-emerald-400' : 'text-rose-400'
                          }`}
                        >
                          {threat.headers.dkimStatus}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-black/40 border border-white/5">
                        <span className="text-[10px] text-slate-500 block">DMARC POLICY</span>
                        <span
                          className={`font-bold ${
                            threat.headers.dmarcStatus === 'PASS' ? 'text-emerald-400' : 'text-rose-400'
                          }`}
                        >
                          {threat.headers.dmarcStatus}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: CUSTOMER SUPPORT INTELLIGENCE */}
            {activeAnalysisTab === 'support' && (
              <div className="space-y-4">
                {/* Multi-Dimensional Sentiment Gauges */}
                <div>
                  <h4 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold mb-2">
                    Multi-Dimensional Sentiment & Emotional Spectrum
                  </h4>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3 rounded-xl bg-[#090D18] border border-white/5">
                      <span className="text-[10px] font-mono text-slate-400 block">SATISFACTION</span>
                      <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
                        {support.sentimentScores.satisfaction}%
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                        <div
                          className="bg-emerald-500 h-full rounded-full"
                          style={{ width: `${support.sentimentScores.satisfaction}%` }}
                        />
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-[#090D18] border border-white/5">
                      <span className="text-[10px] font-mono text-slate-400 block">FRUSTRATION</span>
                      <div className="text-xl font-bold font-mono text-rose-400 mt-1">
                        {support.sentimentScores.frustration}%
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                        <div
                          className="bg-rose-500 h-full rounded-full"
                          style={{ width: `${support.sentimentScores.frustration}%` }}
                        />
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-[#090D18] border border-white/5">
                      <span className="text-[10px] font-mono text-slate-400 block">URGENCY LEVEL</span>
                      <div className="text-xl font-bold font-mono text-cyan-400 mt-1">
                        {support.sentimentScores.urgency}%
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                        <div
                          className="bg-cyan-500 h-full rounded-full"
                          style={{ width: `${support.sentimentScores.urgency}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Intent & Root Cause Taxonomy */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="p-3 rounded-xl bg-[#090D18] border border-white/5 text-xs">
                    <span className="text-[10px] font-mono text-slate-400 block">ROOT CAUSE CATEGORY</span>
                    <span className="text-white font-semibold text-sm mt-0.5 block">
                      {support.rootCauseCategory}
                    </span>
                    <span className="text-slate-500 text-[11px] font-mono">Intent: {support.intent}</span>
                  </div>

                  <div className="p-3 rounded-xl bg-[#090D18] border border-white/5 text-xs">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] font-mono text-slate-400">CHURN RISK INDEX</span>
                      <span
                        className={`font-mono text-[10px] font-bold px-1.5 py-0.5 rounded ${
                          support.churnRisk.level === 'CRITICAL' || support.churnRisk.level === 'HIGH'
                            ? 'bg-rose-500/20 text-rose-300'
                            : 'bg-emerald-500/20 text-emerald-300'
                        }`}
                      >
                        {support.churnRisk.level} RISK
                      </span>
                    </div>
                    <span className="text-white font-semibold text-sm mt-0.5 block">
                      {support.churnRisk.score}% Probability
                    </span>
                    {support.churnRisk.retentionWarning && (
                      <span className="text-rose-400 text-[11px] block mt-1">
                        ⚠ {support.churnRisk.retentionWarning}
                      </span>
                    )}
                  </div>
                </div>

                {/* Automated Safe Smart Reply */}
                <div className="p-4 rounded-xl bg-gradient-to-br from-[#0C1220] to-[#080D18] border border-cyan-500/30 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-cyan-400" />
                      <span className="text-xs font-mono font-bold uppercase text-cyan-300">
                        AI-Synthesized Safe Smart Reply (Security-Vetted)
                      </span>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> Safe Guardrails Enforced
                    </span>
                  </div>

                  <div className="bg-[#060911] p-3 rounded-xl border border-white/5 text-xs text-slate-200 font-mono whitespace-pre-wrap leading-relaxed">
                    {support.safeSmartReply.body}
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
                      <span className="text-slate-500">Key Points:</span>
                      {support.safeSmartReply.keyPointsCovered.map((kp, idx) => (
                        <span key={idx} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                          ✓ {kp}
                        </span>
                      ))}
                    </div>

                    <button
                      onClick={handleCopyReply}
                      className="px-3 py-1.5 rounded-lg bg-cyan-600/30 hover:bg-cyan-600/50 border border-cyan-500/40 text-cyan-200 text-xs font-semibold flex items-center gap-1.5 transition"
                    >
                      {copiedDraft ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Draft Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copy Smart Reply</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Auto Routing & Department Handoff */}
                <div className="p-3 rounded-xl bg-[#090D18] border border-white/5 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <span className="text-[10px] font-mono text-slate-400 block">
                      AUTOMATED DEPARTMENT ROUTING
                    </span>
                    <span className="text-cyan-400 font-semibold text-sm">
                      {support.automatedRouting.recommendedDepartment}
                    </span>
                    <span className="text-slate-500 text-[11px] font-mono block">
                      Queue: {support.automatedRouting.suggestedQueue} ({support.automatedRouting.escalationTier})
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {support.automatedRouting.requiredSkillset.map((skill, sidx) => (
                      <span
                        key={sidx}
                        className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-mono"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
        </div>
      </div>
      )}
    </div>
  );
};
