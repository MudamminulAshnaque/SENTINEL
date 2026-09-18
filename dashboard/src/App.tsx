import React, { useState, useEffect } from 'react';
import { Navbar } from './components/layout/Navbar';
import type { ActiveTab } from './components/layout/Navbar';
import { CommandCenter } from './components/dashboard/CommandCenter';
import { ConversationAnalyzer } from './components/analyzer/ConversationAnalyzer';
import { UrlRadarScanner } from './components/sandbox/UrlRadarScanner';
import { TicketQueue } from './components/tickets/TicketQueue';
import { IntelligenceAnalytics } from './components/analytics/IntelligenceAnalytics';
import { BackendConfigModal } from './components/modals/BackendConfigModal';
import { Footer } from './components/layout/Footer';
import { aegisApi } from './services/api';
import type { BackendConfig, DualAnalysisResult, ExecutiveMetrics, SupportTicketItem } from './types/intelligence';

const EMPTY_METRICS: ExecutiveMetrics = {
  totalScanned: 0,
  totalThreatsBlocked: 0,
  phishingBlockRate: 100,
  socialEngineeringDetected: 0,
  quarantinedCount: 0,
  averageCsatEstimate: 5.0,
  averageFrustrationRate: 0,
  churnRiskDeflectedCount: 0,
  meanTimeToDetectMs: 0,
  defectClusters: [],
  threatVectorDistribution: []
};

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('dashboard');
  const [backendConfig, setBackendConfig] = useState<BackendConfig>(aegisApi.getConfig());
  const [isBackendModalOpen, setIsBackendModalOpen] = useState(false);
  const [currentAnalysis, setCurrentAnalysis] = useState<DualAnalysisResult | null>(null);
  const [tickets, setTickets] = useState<SupportTicketItem[]>([]);
  const [metrics, setMetrics] = useState<ExecutiveMetrics>(EMPTY_METRICS);

  // Load live data from backend API
  useEffect(() => {
    // Ping health check
    aegisApi.pingBackend().then(() => {
      setBackendConfig(aegisApi.getConfig());
    });

    // Fetch initial tickets and metrics from backend
    aegisApi.getTickets().then((loadedTickets) => {
      setTickets(loadedTickets);
    }).catch(() => {
      // Backend not running yet; stays empty
    });

    aegisApi.getMetrics().then((loadedMetrics) => {
      setMetrics(loadedMetrics);
    }).catch(() => {
      // Backend not running yet; stays empty
    });
  }, [backendConfig.baseUrl]);

  const handleSelectTicket = (ticket: SupportTicketItem) => {
    if (ticket.fullAnalysis) {
      setCurrentAnalysis(ticket.fullAnalysis);
      setActiveTab('analyzer');
    }
  };

  const handleUpdateTicketStatus = (ticketId: string, status: SupportTicketItem['status']) => {
    setTickets((prev) =>
      prev.map((t) => (t.id === ticketId ? { ...t, status } : t))
    );
    aegisApi.updateTicketStatus(ticketId, status).catch(console.error);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#07090E] text-slate-100 cyber-grid">
      {/* Top Navigation & Status Ticker */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        backendConfig={backendConfig}
        onOpenBackendModal={() => setIsBackendModalOpen(true)}
      />

      {/* Main Body View Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        {activeTab === 'dashboard' && (
          <CommandCenter
            metrics={metrics}
            recentTickets={tickets}
            onSelectTicket={handleSelectTicket}
            setActiveTab={setActiveTab}
          />
        )}

        {activeTab === 'analyzer' && (
          <ConversationAnalyzer
            currentResult={currentAnalysis}
            onAnalysisUpdate={(updated) => setCurrentAnalysis(updated)}
          />
        )}

        {activeTab === 'sandbox' && <UrlRadarScanner />}

        {activeTab === 'tickets' && (
          <TicketQueue
            tickets={tickets}
            onSelectTicket={handleSelectTicket}
            onUpdateTicketStatus={handleUpdateTicketStatus}
          />
        )}

        {activeTab === 'analytics' && <IntelligenceAnalytics metrics={metrics} />}
      </main>

      {/* Footer */}
      <Footer />

      {/* Teammate Backend Bridge Configuration Modal */}
      <BackendConfigModal
        isOpen={isBackendModalOpen}
        onClose={() => setIsBackendModalOpen(false)}
        config={backendConfig}
        onConfigChange={(updated) => setBackendConfig(updated)}
      />
    </div>
  );
};

export default App;
