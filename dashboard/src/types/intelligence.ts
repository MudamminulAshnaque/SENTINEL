export type ChannelType = 'email' | 'chat' | 'ticket' | 'social' | 'contact_form' | 'url_scan';

export type ThreatSeverity = 'CLEAN' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'MALICIOUS';
export type SupportPriority = 'P1' | 'P2' | 'P3' | 'P4';

export interface SocialEngineeringVector {
  name: string;
  score: number; // 0 - 100
  detected: boolean;
  explanation: string;
}

export interface UrlForensicItem {
  url: string;
  domain: string;
  domainAgeDays: number;
  typosquattingTarget?: string;
  levenshteinDistance?: number;
  reputationScore: number; // 0 to 100 (100 = safe, 0 = malicious)
  sslValid: boolean;
  ipAddress: string;
  serverLocation: string;
  redirectHops: string[];
  sandboxVerdict: 'CLEAN' | 'SUSPICIOUS' | 'PHISHING' | 'MALWARE';
}

export interface IndicatorOfCompromise {
  id: string;
  type: 'IP' | 'DOMAIN' | 'URL' | 'SHA256' | 'HEADER';
  value: string;
  severity: ThreatSeverity;
  description: string;
  mitreTechnique?: string;
}

export interface EmailHeaderForensics {
  fromAddress: string;
  replyToAddress?: string;
  returnPath?: string;
  spfStatus: 'PASS' | 'FAIL' | 'SOFTFAIL' | 'NONE';
  dkimStatus: 'PASS' | 'FAIL' | 'NONE';
  dmarcStatus: 'PASS' | 'FAIL' | 'NONE';
  spoofingLikelihood: number; // 0 - 100
  flaggedAnomaly?: string;
}

export interface ThreatIntelligence {
  threatLevel: ThreatSeverity;
  phishingScore: number; // 0 - 100
  confidenceScore: number; // 0 - 100
  attackVectors: string[];
  socialEngineering: {
    urgencyCoercion: number;
    authorityImpersonation: number;
    fearIntimidation: number;
    pretexting: number;
    vectors: SocialEngineeringVector[];
  };
  urls: UrlForensicItem[];
  iocs: IndicatorOfCompromise[];
  headers?: EmailHeaderForensics;
  secopsActions: {
    quarantined: boolean;
    linksStripped: boolean;
    domainBlocked: boolean;
    vipEscalation: boolean;
  };
  summaryReasoning: string;
}

export interface SupportIntelligence {
  overallSentiment: 'VERY_POSITIVE' | 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE' | 'EXTREMELY_NEGATIVE';
  sentimentScores: {
    satisfaction: number; // 0 - 100
    frustration: number; // 0 - 100
    urgency: number; // 0 - 100
  };
  rootCauseCategory: string;
  intent: string;
  churnRisk: {
    score: number; // 0 - 100
    level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    retentionWarning?: string;
  };
  customerTier: 'Enterprise VIP' | 'Growth Enterprise' | 'Standard Pro' | 'Free Tier';
  recommendedPriority: SupportPriority;
  automatedRouting: {
    recommendedDepartment: string;
    escalationTier: string;
    requiredSkillset: string[];
    suggestedQueue: string;
  };
  safeSmartReply: {
    subject: string;
    body: string;
    safetyChecksPassed: boolean;
    deescalationTone: string;
    keyPointsCovered: string[];
  };
  detectedKeyEntities: {
    label: string;
    value: string;
  }[];
}

export interface DualAnalysisResult {
  id: string;
  timestamp: string;
  channel: ChannelType;
  sender: string;
  recipient?: string;
  subject?: string;
  rawContent: string;
  highlightedTokens: {
    text: string;
    type: 'threat' | 'url' | 'urgency' | 'sentiment' | 'entity';
    explanation: string;
  }[];
  threatIntelligence: ThreatIntelligence;
  supportIntelligence: SupportIntelligence;
}

export interface SupportTicketItem {
  id: string;
  customerName: string;
  customerEmail: string;
  customerTier: 'Enterprise VIP' | 'Growth Enterprise' | 'Standard Pro' | 'Free Tier';
  channel: ChannelType;
  subject: string;
  snippet: string;
  timestamp: string;
  status: 'OPEN' | 'IN_REVIEW' | 'QUARANTINED' | 'RESOLVED' | 'ESCALATED_SECOPS';
  threatLevel: ThreatSeverity;
  supportPriority: SupportPriority;
  sentiment: 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE';
  fullAnalysis: DualAnalysisResult;
}

export interface ExecutiveMetrics {
  totalScanned: number;
  totalThreatsBlocked: number;
  phishingBlockRate: number; // e.g. 99.6
  socialEngineeringDetected: number;
  quarantinedCount: number;
  averageCsatEstimate: number; // e.g. 4.6 / 5.0
  averageFrustrationRate: number; // e.g. 18.4%
  churnRiskDeflectedCount: number;
  meanTimeToDetectMs: number; // e.g. 140ms
  defectClusters: {
    category: string;
    count: number;
    trend: 'UP' | 'DOWN' | 'STABLE';
    sentimentImpact: number;
  }[];
  threatVectorDistribution: {
    vector: string;
    count: number;
    percentage: number;
  }[];
}

export interface BackendConfig {
  baseUrl: string;
  apiKey?: string;
  useLiveBackend: boolean;
  timeoutMs: number;
  lastPingStatus?: 'CONNECTED' | 'DISCONNECTED' | 'CHECKING';
  lastPingLatencyMs?: number;
}
