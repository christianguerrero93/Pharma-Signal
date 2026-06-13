export type PharmaRole = 'ceo' | 'admin' | 'trader' | 'analyst' | 'compliance' | 'client' | 'vendor';

const API_BASE = import.meta.env.VITE_ENTERPRISE_API_URL || 'http://localhost:8080';

async function request<T>(path: string, role: PharmaRole = 'ceo', init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'x-pharma-role': role,
      ...(init?.headers || {}),
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Enterprise API ${response.status}: ${text}`);
  }

  return response.json() as Promise<T>;
}

export type ExecutiveDashboard = {
  total_budget: number;
  total_spent: number;
  working_media_ratio: number;
  active_campaigns: number;
  approved_supply_paths: number;
  measurement_ready_campaigns: number;
  compliance_blocks: number;
  avg_outcome_supply_score: number;
  ceo_summary: string;
  next_board_questions: string[];
};

export type BoardNarrative = {
  headline: string;
  what_is_real_now: string[];
  numbers: ExecutiveDashboard;
  next_90_days: string[];
};

export type PortfolioOptimizerResponse = {
  current_budget: number;
  recommended_budget: number;
  recommendations: Array<{
    campaign_id: string;
    campaign_name: string;
    current_budget: number;
    recommended_budget: number;
    delta: number;
    status: string;
    power_score: number;
    rationale: string;
  }>;
};

export type AuctionEvaluateRequest = {
  org_id: string;
  campaign_id: string;
  line_item_id: string;
  audience_id: string;
  supply_path_id: string;
  creative_id: string;
  floor_cpm: number;
  audience_match: number;
  contextual_relevance: number;
  outcome_signal: number;
  frequency_seen_today: number;
  contains_phi?: boolean;
  geo_allowed?: boolean;
  consent_ok?: boolean;
};

export type AuctionEvaluateResponse = {
  request_id: string;
  decision: 'bid' | 'throttle' | 'no_bid' | 'blocked';
  bid_cpm: number;
  clearing_price_cpm: number | null;
  confidence: number;
  creative_id: string | null;
  deal_id: string | null;
  reasons: string[];
  guardrails: string[];
  event_log: string[];
};

export const enterpriseClient = {
  health: (role: PharmaRole = 'ceo') => request<{ status: string; service: string; version: string; modules: string[] }>('/health', role),
  executiveDashboard: (role: PharmaRole = 'ceo') => request<ExecutiveDashboard>('/api/v2/executive-dashboard', role),
  boardNarrative: (role: PharmaRole = 'ceo') => request<BoardNarrative>('/api/v2/board/narrative', role),
  portfolioOptimizer: (role: PharmaRole = 'ceo') => request<PortfolioOptimizerResponse>('/api/v2/optimizer/portfolio', role),
  measurementPlans: (role: PharmaRole = 'ceo') => request('/api/v2/measurement/plans', role),
  audit: (role: PharmaRole = 'ceo') => request('/api/v2/audit', role),
  evaluateAuction: (payload: AuctionEvaluateRequest, role: PharmaRole = 'ceo') =>
    request<AuctionEvaluateResponse>('/api/v2/auction/evaluate', role, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};
