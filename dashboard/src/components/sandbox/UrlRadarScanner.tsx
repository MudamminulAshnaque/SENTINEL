import React, { useState } from 'react';
import { 
  Globe, 
  ShieldAlert, 
  ShieldCheck, 
  RefreshCw, 
  RadioTower, 
  Lock, 
  Layers, 
  Copy, 
  Check, 
  Ban
} from 'lucide-react';
import type { UrlForensicItem } from '../../types/intelligence';
import { aegisApi } from '../../services/api';

export const UrlRadarScanner: React.FC = () => {
  const [inputUrl, setInputUrl] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copiedDefanged, setCopiedDefanged] = useState(false);
  const [domainBlocked, setDomainBlocked] = useState(false);
  const [scanResult, setScanResult] = useState<UrlForensicItem | null>(null);

  const handleScan = async (targetOverride?: string) => {
    const target = targetOverride || inputUrl.trim();
    if (!target) return;
    setIsScanning(true);
    setErrorMessage(null);
    setDomainBlocked(false);
    try {
      const result = await aegisApi.scanUrl(target);
      setScanResult(result);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Scan request failed. Check backend API.';
      setErrorMessage(message);
    } finally {
      setIsScanning(false);
    }
  };

  const defangUrl = (u: string) => {
    return u.replace('http://', 'hxxp://').replace('https://', 'hxxps://').replace(/\./g, '[.]');
  };

  const handleCopyDefanged = () => {
    if (!scanResult) return;
    navigator.clipboard.writeText(defangUrl(scanResult.url));
    setCopiedDefanged(true);
    setTimeout(() => setCopiedDefanged(false), 2000);
  };

  const isPhishing = scanResult ? (scanResult.sandboxVerdict === 'PHISHING' || scanResult.sandboxVerdict === 'MALWARE') : false;

  return (
    <div className="space-y-6 pb-12">
      {/* Header & Input */}
      <div className="glass-panel p-5 rounded-2xl">
        <div className="flex items-center gap-2 mb-3">
          <RadioTower className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-mono uppercase tracking-wider font-bold text-cyan-300">
            URL Sandbox Scanner
          </h2>
        </div>

        {/* Input Bar */}
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
              <Globe className="w-4 h-4" />
            </div>
            <input
              type="text"
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              placeholder="Enter URL to inspect (e.g. https://domain.com/login)"
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#090D18] border border-white/10 text-slate-200 text-xs font-mono focus:outline-none focus:border-cyan-500/50"
            />
          </div>
          <button
            onClick={() => handleScan()}
            disabled={isScanning || !inputUrl.trim()}
            className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:opacity-90 disabled:opacity-50 text-white text-xs font-semibold transition"
          >
            {isScanning ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Scanning...</span>
              </>
            ) : (
              <>
                <RadioTower className="w-4 h-4" />
                <span>Scan URL</span>
              </>
            )}
          </button>
        </div>

        {errorMessage && (
          <div className="mt-3 p-3 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs font-mono">
            {errorMessage}
          </div>
        )}
      </div>

      {/* Results View */}
      {scanResult ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Metrics & Verdict (6 cols) */}
          <div className="lg:col-span-6 space-y-4">
            <div className={`p-5 rounded-2xl border ${isPhishing ? 'glass-panel-threat' : 'glass-panel-safe'}`}>
              <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-4">
                <div className="flex items-center gap-2">
                  {isPhishing ? (
                    <ShieldAlert className="w-5 h-5 text-rose-400" />
                  ) : (
                    <ShieldCheck className="w-5 h-5 text-emerald-400" />
                  )}
                  <span className="font-mono text-xs font-bold uppercase text-white tracking-wider">
                    VERDICT: {scanResult.sandboxVerdict}
                  </span>
                </div>
                <span className="text-xs font-mono text-slate-400">
                  Score: <span className="font-bold text-white">{scanResult.reputationScore} / 100</span>
                </span>
              </div>

              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-[10px] font-mono text-slate-400 block">TARGET:</span>
                  <span className="font-mono text-xs font-semibold text-rose-300 break-all">
                    {scanResult.url}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-2">
                  <div className="p-3 rounded-xl bg-[#090D18] border border-white/5 font-mono">
                    <span className="text-slate-500 text-[10px] block">DOMAIN AGE</span>
                    <span className="text-white font-bold text-sm">{scanResult.domainAgeDays} days</span>
                  </div>

                  <div className="p-3 rounded-xl bg-[#090D18] border border-white/5 font-mono">
                    <span className="text-slate-500 text-[10px] block">TYPOSQUATTING</span>
                    <span className="text-rose-400 font-bold text-sm">
                      {scanResult.levenshteinDistance !== undefined ? `Dist = ${scanResult.levenshteinDistance}` : 'None'}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-xl bg-[#090D18] border border-white/5 font-mono">
                    <span className="text-slate-500 text-[10px] block">SERVER IP</span>
                    <span className="text-white font-bold text-xs">{scanResult.ipAddress}</span>
                  </div>

                  <div className="p-3 rounded-xl bg-[#090D18] border border-white/5 font-mono">
                    <span className="text-slate-500 text-[10px] block">TLS / SSL</span>
                    <span className="text-emerald-400 font-bold text-xs">
                      {scanResult.sslValid ? 'Valid SSL' : 'Invalid'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-2 pt-4 mt-2 border-t border-white/10">
                <button
                  onClick={handleCopyDefanged}
                  className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-white/10 text-xs font-mono text-slate-200 flex items-center gap-1.5 transition"
                >
                  {copiedDefanged ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedDefanged ? 'Copied' : 'Copy Defanged'}</span>
                </button>

                <button
                  onClick={() => setDomainBlocked(!domainBlocked)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition flex items-center gap-1.5 ${
                    domainBlocked
                      ? 'bg-rose-950 text-rose-300 border border-rose-500/40'
                      : 'bg-rose-600/30 hover:bg-rose-600/50 border border-rose-500/40 text-rose-200'
                  }`}
                >
                  <Ban className="w-3.5 h-3.5" />
                  <span>{domainBlocked ? 'Blocked' : 'Block Domain'}</span>
                </button>
              </div>
            </div>

            {/* Redirect Hops if any */}
            {scanResult.redirectHops && scanResult.redirectHops.length > 0 && (
              <div className="glass-panel p-5 rounded-2xl">
                <div className="flex items-center gap-2 mb-3">
                  <Layers className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-xs font-mono uppercase tracking-wider font-bold text-slate-200">
                    HTTP Redirect Hops ({scanResult.redirectHops.length})
                  </h3>
                </div>
                <div className="space-y-2">
                  {scanResult.redirectHops.map((hop, i) => (
                    <div key={i} className="p-2.5 rounded-lg bg-[#090D18] border border-white/5 text-xs font-mono truncate text-slate-300">
                      ↳ [{i + 1}] {hop}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Sandbox Preview Simulation (6 cols) */}
          <div className="lg:col-span-6 glass-panel rounded-2xl overflow-hidden border border-white/10">
            <div className="bg-[#0A0E18] px-4 py-3 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 inline-block" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 inline-block" />
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 inline-block" />
                <span className="text-[11px] font-mono text-slate-400 ml-2">Isolated Sandbox Container</span>
              </div>
            </div>
            <div className="bg-[#07090E] px-4 py-2 border-b border-white/5 flex items-center gap-2 text-xs font-mono text-slate-400 truncate">
              <Lock className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
              <span className="truncate text-slate-300">{scanResult.url}</span>
            </div>
            <div className="p-8 bg-[#04060A] min-h-[300px] flex flex-col items-center justify-center text-center">
              <div className="w-32 h-32 rounded-full border border-cyan-500/20 relative flex items-center justify-center mb-4">
                <div className="w-20 h-20 rounded-full border border-dashed border-cyan-500/30" />
                <div className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              </div>
              <h4 className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                Detonation Complete
              </h4>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                Verdict: {scanResult.sandboxVerdict} (Score: {scanResult.reputationScore}/100)
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="glass-panel p-12 rounded-2xl text-center text-slate-500 font-mono text-xs">
          Enter a URL above and click Scan URL to inspect domain age, typosquatting, and threat verdict.
        </div>
      )}
    </div>
  );
};
