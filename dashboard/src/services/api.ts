import type { BackendConfig, DualAnalysisResult, ExecutiveMetrics, SupportTicketItem, UrlForensicItem } from '../types/intelligence';

const CONFIG_STORAGE_KEY = 'aegis_cx_backend_config';

export const getDefaultConfig = (): BackendConfig => {
  const saved = localStorage.getItem(CONFIG_STORAGE_KEY);
  if (saved) {
    try {
      return JSON.parse(saved);
    } catch {
      // fallback
    }
  }
  return {
    baseUrl: (import.meta as any).env?.VITE_BACKEND_URL || 'http://localhost:8000',
    apiKey: '',
    useLiveBackend: true,
    timeoutMs: 5000,
    lastPingStatus: 'CHECKING',
  };
};

export const saveConfig = (config: BackendConfig): void => {
  localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(config));
};

export class AegisApiClient {
  private config: BackendConfig;

  constructor() {
    this.config = getDefaultConfig();
  }

  public getConfig(): BackendConfig {
    return { ...this.config };
  }

  public updateConfig(newConfig: Partial<BackendConfig>): BackendConfig {
    this.config = { ...this.config, ...newConfig };
    saveConfig(this.config);
    return this.config;
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (this.config.apiKey) {
      headers['Authorization'] = `Bearer ${this.config.apiKey}`;
    }
    return headers;
  }

  // Ping backend server
  public async pingBackend(urlOverride?: string): Promise<{ success: boolean; latencyMs: number; error?: string }> {
    const targetUrl = (urlOverride || this.config.baseUrl).replace(/\/$/, '');
    const startTime = performance.now();
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);

      const response = await fetch(`${targetUrl}/api/v1/health`, {
        method: 'GET',
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      const latencyMs = Math.round(performance.now() - startTime);
      if (response.ok) {
        this.updateConfig({ lastPingStatus: 'CONNECTED', lastPingLatencyMs: latencyMs });
        return { success: true, latencyMs };
      } else {
        this.updateConfig({ lastPingStatus: 'DISCONNECTED', lastPingLatencyMs: latencyMs });
        return { success: false, latencyMs, error: `HTTP ${response.status}: ${response.statusText}` };
      }
    } catch (err: unknown) {
      const latencyMs = Math.round(performance.now() - startTime);
      this.updateConfig({ lastPingStatus: 'DISCONNECTED', lastPingLatencyMs: latencyMs });
      const message = err instanceof Error ? err.message : 'Server unreachable';
      return { success: false, latencyMs, error: message };
    }
  }

  // POST /api/v1/analyze
  public async analyzeConversation(payload: {
    channel: string;
    text: string;
    subject?: string;
    sender?: string;
    recipient?: string;
  }): Promise<DualAnalysisResult> {
    const response = await fetch(`${this.config.baseUrl}/api/v1/analyze`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Backend Analysis failed: HTTP ${response.status} ${response.statusText}`);
    }

    return await response.json();
  }

  // POST /api/v1/scan-url
  public async scanUrl(url: string): Promise<UrlForensicItem> {
    const response = await fetch(`${this.config.baseUrl}/api/v1/scan-url`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ url }),
    });

    if (!response.ok) {
      throw new Error(`URL Radar scan failed: HTTP ${response.status} ${response.statusText}`);
    }

    return await response.json();
  }

  // POST /api/v1/parse-eml (multipart file upload)
  public async parseEml(file: File): Promise<{ sender: string; subject: string; text: string; used_html_fallback: boolean }> {
    const formData = new FormData();
    formData.append('file', file);

    // Do NOT set Content-Type here — the browser sets the multipart
    // boundary automatically. getHeaders() would force 'application/json'
    // and break the upload, so only the auth header (if any) is included.
    const headers: Record<string, string> = {};
    const configHeaders = this.getHeaders();
    if (configHeaders['Authorization']) {
      headers['Authorization'] = configHeaders['Authorization'];
    }

    const response = await fetch(`${this.config.baseUrl}/api/v1/parse-eml`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      throw new Error(detail?.detail || `Failed to parse .eml file: HTTP ${response.status}`);
    }

    return await response.json();
  }

  // GET /api/v1/tickets
  public async getTickets(): Promise<SupportTicketItem[]> {
    const response = await fetch(`${this.config.baseUrl}/api/v1/tickets`, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error(`Failed to load tickets: HTTP ${response.status}`);
    }

    return await response.json();
  }

  // PATCH /api/v1/tickets/:id
  public async updateTicketStatus(ticketId: string, status: SupportTicketItem['status']): Promise<void> {
    await fetch(`${this.config.baseUrl}/api/v1/tickets/${ticketId}`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: JSON.stringify({ status }),
    });
  }

  // GET /api/v1/metrics
  public async getMetrics(): Promise<ExecutiveMetrics> {
    const response = await fetch(`${this.config.baseUrl}/api/v1/metrics`, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error(`Failed to load metrics: HTTP ${response.status}`);
    }

    return await response.json();
  }
}

export const aegisApi = new AegisApiClient();
