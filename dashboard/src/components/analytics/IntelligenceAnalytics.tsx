import React from 'react';
import { 
  BarChart3, 
  ShieldAlert, 
  HeartHandshake, 
  Layers, 
  FileSpreadsheet
} from 'lucide-react';
import type { ExecutiveMetrics } from '../../types/intelligence';

interface IntelligenceAnalyticsProps {
  metrics: ExecutiveMetrics;
}

export const IntelligenceAnalytics: React.FC<IntelligenceAnalyticsProps> = ({ metrics }) => {
  const handleExportCsv = () => {
    const csvContent = `Metric,Value\nCSAT Estimate,${metrics.averageCsatEstimate}\nFrustration Rate,${metrics.averageFrustrationRate}%\nChurn Deflected,${metrics.churnRiskDeflectedCount}\nTotal Scanned,${metrics.totalScanned}\nThreats Blocked,${metrics.totalThreatsBlocked}\nBlock Rate,${metrics.phishingBlockRate}%\nMean Time to Detect,${metrics.meanTimeToDetectMs}ms`;
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `SENTINEL_METRICS.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="glass-panel p-5 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-mono uppercase tracking-wider font-bold text-cyan-300">
            Analytics & Reports
          </h2>
        </div>

        <button
          onClick={handleExportCsv}
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-xs font-mono text-slate-200 transition shrink-0"
        >
          <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
          <span>Export CSV</span>
        </button>
      </div>

      {/* Row 1: Support vs Security Telemetry */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Support Sentiment Breakdown */}
        <div className="glass-panel p-5 rounded-2xl space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-white/5">
            <HeartHandshake className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-mono uppercase tracking-wider font-bold text-slate-200">
              Customer Experience Metrics
            </h3>
          </div>

          <div className="grid grid-cols-2 gap-3 font-mono text-xs">
            <div className="p-3 rounded-xl bg-[#090D18] border border-white/5">
              <span className="text-slate-500 text-[10px] block">CSAT FORECAST</span>
              <span className="text-xl font-bold text-white mt-1 block">
                {metrics.averageCsatEstimate ? `${metrics.averageCsatEstimate} / 5.0` : '--'}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-[#090D18] border border-white/5">
              <span className="text-slate-500 text-[10px] block">FRUSTRATION RATE</span>
              <span className="text-xl font-bold text-amber-400 mt-1 block">
                {metrics.averageFrustrationRate}%
              </span>
            </div>

            <div className="p-3 rounded-xl bg-[#090D18] border border-white/5">
              <span className="text-slate-500 text-[10px] block">CHURN MITIGATED</span>
              <span className="text-xl font-bold text-emerald-400 mt-1 block">
                {metrics.churnRiskDeflectedCount}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-[#090D18] border border-white/5">
              <span className="text-slate-500 text-[10px] block">TOTAL CONVERSATIONS</span>
              <span className="text-xl font-bold text-white mt-1 block">
                {metrics.totalScanned}
              </span>
            </div>
          </div>
        </div>

        {/* Threat Detection Breakdown */}
        <div className="glass-panel p-5 rounded-2xl space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-white/5">
            <ShieldAlert className="w-4 h-4 text-rose-400" />
            <h3 className="text-xs font-mono uppercase tracking-wider font-bold text-slate-200">
              Cyber Threat Metrics
            </h3>
          </div>

          <div className="grid grid-cols-2 gap-3 font-mono text-xs">
            <div className="p-3 rounded-xl bg-[#090D18] border border-white/5">
              <span className="text-slate-500 text-[10px] block">PHISHING BLOCK RATE</span>
              <span className="text-xl font-bold text-emerald-400 mt-1 block">
                {metrics.phishingBlockRate}%
              </span>
            </div>

            <div className="p-3 rounded-xl bg-[#090D18] border border-white/5">
              <span className="text-slate-500 text-[10px] block">THREATS ISOLATED</span>
              <span className="text-xl font-bold text-rose-400 mt-1 block">
                {metrics.totalThreatsBlocked}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-[#090D18] border border-white/5">
              <span className="text-slate-500 text-[10px] block">SOCIAL ENGINEERING</span>
              <span className="text-xl font-bold text-amber-400 mt-1 block">
                {metrics.socialEngineeringDetected}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-[#090D18] border border-white/5">
              <span className="text-slate-500 text-[10px] block">MEAN TIME TO DETECT</span>
              <span className="text-xl font-bold text-cyan-400 mt-1 block">
                {metrics.meanTimeToDetectMs} ms
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Row 2: Live Defect Clusters (if any returned from backend) */}
      {metrics.defectClusters && metrics.defectClusters.length > 0 && (
        <div className="glass-panel p-5 rounded-2xl">
          <div className="flex items-center gap-2 pb-3 border-b border-white/5 mb-4">
            <Layers className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-mono uppercase tracking-wider font-bold text-slate-200">
              Recurring Defect Taxonomy
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {metrics.defectClusters.map((cluster, i) => (
              <div key={i} className="p-3.5 rounded-xl bg-[#090D18] border border-white/5 space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-white">{cluster.category}</span>
                  <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                    {cluster.count}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
