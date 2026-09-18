import React, { useState } from 'react';
import { 
  X, 
  Server, 
  CheckCircle2, 
  AlertCircle, 
  RefreshCw, 
  Copy, 
  Check
} from 'lucide-react';
import type { BackendConfig } from '../../types/intelligence';
import { aegisApi } from '../../services/api';

interface BackendConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: BackendConfig;
  onConfigChange: (config: BackendConfig) => void;
}

export const BackendConfigModal: React.FC<BackendConfigModalProps> = ({
  isOpen,
  onClose,
  config,
  onConfigChange,
}) => {
  const [baseUrlInput, setBaseUrlInput] = useState(config.baseUrl);
  const [apiKeyInput, setApiKeyInput] = useState(config.apiKey || '');
  const [useLiveBackend, setUseLiveBackend] = useState(config.useLiveBackend);
  const [isTesting, setIsTesting] = useState(false);
  const [pingResult, setPingResult] = useState<{ success: boolean; latencyMs: number; error?: string } | null>(null);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'settings' | 'endpoints' | 'fastapi'>('settings');

  if (!isOpen) return null;

  const handleTestConnection = async () => {
    setIsTesting(true);
    setPingResult(null);
    try {
      const res = await aegisApi.pingBackend(baseUrlInput);
      setPingResult(res);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown network error';
      setPingResult({ success: false, latencyMs: 0, error: message });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = () => {
    const updated = aegisApi.updateConfig({
      baseUrl: baseUrlInput.trim().replace(/\/$/, ''),
      apiKey: apiKeyInput.trim(),
      useLiveBackend,
    });
    onConfigChange(updated);
    onClose();
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(id);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const FASTAPI_SAMPLE = `from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="SENTINEL Intelligence Backend")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    channel: str
    text: str
    subject: Optional[str] = None
    sender: Optional[str] = None

@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "service": "SENTINEL ML Pipeline", "version": "1.0.0"}

@app.post("/api/v1/analyze")
def analyze_conversation(req: AnalyzeRequest):
    # Your ML / LLM / NLP model code runs here!
    # Return DualAnalysisResult JSON matching the schema
    return {
        "id": "ANL-LIVE-001",
        "timestamp": "Just now",
        "channel": req.channel,
        "sender": req.sender or "unknown@domain.com",
        "subject": req.subject or "Inbound Message",
        "rawContent": req.text,
        "highlightedTokens": [],
        "threatIntelligence": {
            "threatLevel": "CRITICAL" if "urgent" in req.text.lower() else "CLEAN",
            "phishingScore": 92 if "urgent" in req.text.lower() else 4,
            "confidenceScore": 96,
            "attackVectors": ["Credential Harvesting Heuristic"],
            "socialEngineering": {
                "urgencyCoercion": 85,
                "authorityImpersonation": 80,
                "fearIntimidation": 75,
                "pretexting": 90,
                "vectors": []
            },
            "urls": [],
            "iocs": [],
            "secopsActions": {"quarantined": True, "linksStripped": True, "domainBlocked": True, "vipEscalation": True},
            "summaryReasoning": "Analyzed by custom backend ML pipeline."
        },
        "supportIntelligence": {
            "overallSentiment": "NEGATIVE",
            "sentimentScores": {"satisfaction": 12, "frustration": 88, "urgency": 90},
            "rootCauseCategory": "Security Incident",
            "intent": "Account Recovery",
            "churnRisk": {"score": 75, "level": "HIGH"},
            "customerTier": "Enterprise VIP",
            "recommendedPriority": "P1",
            "automatedRouting": {
                "recommendedDepartment": "SecOps Incident Response",
                "escalationTier": "Tier 3",
                "requiredSkillset": ["Security Triage"],
                "suggestedQueue": "SecOps-Priority"
            },
            "safeSmartReply": {
                "subject": "Automated Response",
                "body": "Your request has been routed to our security team.",
                "safetyChecksPassed": True,
                "deescalationTone": "Professional",
                "keyPointsCovered": ["Incident logged"]
            },
            "detectedKeyEntities": []
        }
    }
`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <div className="bg-[#0C101A] border border-white/10 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-5 border-b border-white/10 flex items-center justify-between bg-[#080B12]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-cyan-500/20 text-cyan-400">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                Backend Integration Bridge
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                  Ready for FastAPI / Flask / Express
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Connect this UI directly to your teammate's backend server or use standalone mock mode.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Nav Tabs */}
        <div className="px-5 pt-3 border-b border-white/5 flex items-center gap-4 text-xs font-mono">
          <button
            onClick={() => setActiveTab('settings')}
            className={`pb-2.5 border-b-2 font-semibold transition ${
              activeTab === 'settings'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Connection Settings
          </button>
          <button
            onClick={() => setActiveTab('endpoints')}
            className={`pb-2.5 border-b-2 font-semibold transition ${
              activeTab === 'endpoints'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            REST API Schemas (for Teammate)
          </button>
          <button
            onClick={() => setActiveTab('fastapi')}
            className={`pb-2.5 border-b-2 font-semibold transition ${
              activeTab === 'fastapi'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Python Backend Starter Code
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1">
          {activeTab === 'settings' && (
            <div className="space-y-4 text-xs">
              {/* Mode Toggle */}
              <div className="p-4 rounded-xl bg-[#080B12] border border-white/5 flex items-center justify-between">
                <div>
                  <span className="text-sm font-bold text-white block">Routing Mode</span>
                  <span className="text-slate-400 text-xs">
                    {useLiveBackend
                      ? 'Sending live HTTP calls to your teammate\'s backend server'
                      : 'Using high-fidelity client heuristic engine (instant, zero setup needed)'}
                  </span>
                </div>
                <button
                  onClick={() => setUseLiveBackend(!useLiveBackend)}
                  className={`px-4 py-2 rounded-xl font-mono font-bold transition border ${
                    useLiveBackend
                      ? 'bg-emerald-600 text-white border-emerald-400 shadow-glow-emerald'
                      : 'bg-slate-800 text-slate-300 border-white/10'
                  }`}
                >
                  {useLiveBackend ? 'LIVE BACKEND ENABLED' : 'STANDALONE MOCK MODE'}
                </button>
              </div>

              {/* Base URL */}
              <div>
                <label className="font-mono text-slate-300 block mb-1">
                  BACKEND BASE URL (FastAPI / Flask / Node)
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={baseUrlInput}
                    onChange={(e) => setBaseUrlInput(e.target.value)}
                    placeholder="http://localhost:8000"
                    className="flex-1 px-3 py-2 rounded-xl bg-[#080B12] border border-white/10 text-slate-200 font-mono focus:outline-none focus:border-cyan-500/50"
                  />
                  <button
                    onClick={handleTestConnection}
                    disabled={isTesting || !baseUrlInput}
                    className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-slate-200 font-mono flex items-center gap-1.5 transition"
                  >
                    {isTesting ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Testing...</span>
                      </>
                    ) : (
                      <>
                        <Server className="w-3.5 h-3.5 text-cyan-400" />
                        <span>Ping /health</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Ping Result Banner */}
              {pingResult && (
                <div
                  className={`p-3 rounded-xl border font-mono text-xs flex items-center justify-between ${
                    pingResult.success
                      ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300'
                      : 'bg-rose-950/60 border-rose-500/40 text-rose-300'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {pingResult.success ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-rose-400" />
                    )}
                    <span>
                      {pingResult.success
                        ? `Connected successfully! Response latency: ${pingResult.latencyMs}ms`
                        : `Ping failed: ${pingResult.error || 'Server not reachable at ' + baseUrlInput}`}
                    </span>
                  </div>
                </div>
              )}

              {/* Optional API Key */}
              <div>
                <label className="font-mono text-slate-300 block mb-1">
                  OPTIONAL BEARER AUTH TOKEN
                </label>
                <input
                  type="password"
                  value={apiKeyInput}
                  onChange={(e) => setApiKeyInput(e.target.value)}
                  placeholder="Bearer token or API Secret key (optional)"
                  className="w-full px-3 py-2 rounded-xl bg-[#080B12] border border-white/10 text-slate-200 font-mono focus:outline-none focus:border-cyan-500/50"
                />
              </div>
            </div>
          )}

          {activeTab === 'endpoints' && (
            <div className="space-y-4 text-xs font-mono">
              <p className="text-slate-400">
                Your backend teammate can implement any or all of the following standard REST endpoints:
              </p>

              <div className="p-3.5 rounded-xl bg-[#080B12] border border-white/5 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-cyan-400 font-bold">POST /api/v1/analyze</span>
                  <span className="text-slate-500 text-[10px]">Dual Intelligence Endpoint</span>
                </div>
                <p className="text-slate-400 text-[11px]">
                  Accepts raw conversation text, sender, subject, and channel. Returns threat and support analysis JSON.
                </p>
                <div className="bg-black/50 p-2.5 rounded-lg text-slate-300 text-[11px] overflow-x-auto">
                  {`// Request Payload:\n{\n  "channel": "email" | "chat" | "ticket" | "social" | "url_scan",\n  "text": "Dear support, please verify...",\n  "subject": "Urgent ticket",\n  "sender": "user@domain.com"\n}`}
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-[#080B12] border border-white/5 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-cyan-400 font-bold">POST /api/v1/scan-url</span>
                  <span className="text-slate-500 text-[10px]">URL Radar Endpoint</span>
                </div>
                <p className="text-slate-400 text-[11px]">
                  Accepts a target URL or domain. Returns sandbox verdict, domain age, typosquatting check.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-[#080B12] border border-white/5 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-cyan-400 font-bold">GET /api/v1/health</span>
                  <span className="text-slate-500 text-[10px]">Health Check</span>
                </div>
                <p className="text-slate-400 text-[11px]">
                  Returns status: "ok" so the UI displays the green connected pill.
                </p>
              </div>
            </div>
          )}

          {activeTab === 'fastapi' && (
            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-mono">
                  Copy and give this template to your backend teammate (FastAPI):
                </span>
                <button
                  onClick={() => handleCopy(FASTAPI_SAMPLE, 'fastapi')}
                  className="px-3 py-1 rounded-lg bg-cyan-600/30 hover:bg-cyan-600/50 text-cyan-300 font-mono text-xs flex items-center gap-1.5 transition"
                >
                  {copiedCode === 'fastapi' ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-emerald-400">Copied Python Code</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy Boilerplate</span>
                    </>
                  )}
                </button>
              </div>
              <pre className="p-4 rounded-xl bg-[#080B12] border border-white/5 text-slate-300 font-mono text-[11px] overflow-x-auto max-h-72 leading-relaxed">
                {FASTAPI_SAMPLE}
              </pre>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-white/10 bg-[#080B12] flex items-center justify-between">
          <span className="text-[11px] font-mono text-slate-500">
            Settings persist in browser localStorage
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white text-xs font-semibold shadow-glow-cyan transition"
            >
              Save Configuration
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
