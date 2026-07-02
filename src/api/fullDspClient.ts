// Typed client for the Pharma Signal Full DSP API (backend/full_dsp_server.py).

export const API_BASE = import.meta.env.VITE_FULL_DSP_API_URL || 'http://localhost:8090';
export const DEFAULT_PASSWORD = import.meta.env.VITE_FULL_DSP_DEV_PASSWORD || 'pharma-signal-local';

export type User = { id: string; email: string; name: string; role: string; created_at?: string };

export type BidFactors = {
  audience_quality_weight: number;
  supply_quality_weight: number;
  outcome_signal_weight: number;
  contextual_relevance_weight: number;
  working_media_weight: number;
  frequency_penalty_weight: number;
  bid_shading_pct: number;
  max_bid_multiplier: number;
  data_cost_guardrail: number;
};

export type LineItem = {
  id: string;
  campaign_id: string;
  name: string;
  channel: string;
  budget: number;
  max_bid_cpm: number;
  pacing_mode: string;
  status: string;
  frequency_cap: number;
  bid_factors?: (BidFactors & { line_item_id: string }) | null;
};

export type Campaign = {
  id: string;
  name: string;
  brand: string;
  indication: string;
  audience_type: string;
  objective: string;
  budget: number;
  status: string;
  flight_start: string;
  flight_end: string;
  line_items: LineItem[];
};

export type SupplyPath = {
  id: string;
  partner: string;
  channel: string;
  deal_id: string;
  seller_type: string;
  bid_floor_cpm: number;
  viewability: number;
  fraud_risk: number;
  match_rate: number;
  working_media_ratio: number;
  outcome_score: number;
  status: string;
};

export type AuditEvent = { id: string; ts: string; actor: string; action: string; entity_type: string; entity_id: string; metadata_json: string };

export type Workbench = {
  user: User;
  campaigns: Campaign[];
  supply_paths: SupplyPath[];
  audit: AuditEvent[];
  summary: { campaigns: number; line_items: number; total_budget: number; active_campaigns: number };
};

export type Audience = {
  id: string;
  name: string;
  audience_type: string;
  description: string;
  npi_count: number;
  reach: number;
  match_rate: number;
  data_cpm: number;
  refresh_cadence: string;
  contains_phi: number;
  status: string;
};

export type Forecast = {
  audience: { id: string; name: string; type: string; addressable: number; npi_count: number; match_rate: number };
  impressions: number;
  daily_impressions: number;
  unique_reach: number;
  pct_of_audience_reached: number;
  achieved_frequency: number;
  frequency_cap: number;
  data_spend: number;
  media_spend: number;
  working_media_ratio: number;
  data_cpm: number;
  effective_cpm: number;
};

export type Creative = {
  id: string;
  campaign_id: string;
  name: string;
  fmt: string;
  channel: string;
  claims: string;
  isi_included: number;
  landing_url: string;
  mlr_status: string;
  version: number;
  reviewer: string | null;
  review_notes: string | null;
  submitted_at: string;
  decided_at: string | null;
};

export type Deal = { id: string; partner: string; deal_id: string; deal_type: string; channel: string; floor_cpm: number; audience_match: number; status: string };

export type MeasurementPlan = {
  id: string;
  campaign_id: string;
  study_type: string;
  baseline_rate: number;
  expected_lift_pct: number;
  exposed_size: number;
  control_size: number;
  power: number;
  minimum_detectable_lift_pct?: number;
  mdl?: number;
  expected_exposed_conversions?: number;
  expected_control_conversions?: number;
  readiness?: string;
  status?: string;
  interpretation?: string;
};

export type OptimizerRec = {
  line_item_id: string;
  name: string;
  channel: string;
  campaign: string;
  current_budget: number;
  recommended_budget: number;
  delta_pct: number;
  efficiency_score: number;
  action: 'increase' | 'decrease' | 'hold';
};

export type Optimizer = { recommendations: OptimizerRec[]; total_budget: number; reallocated: number; avg_efficiency?: number };

export type RankedSupply = SupplyPath & { spo_score: number; recommendation: string };
export type SupplyOptimize = { supply_paths: RankedSupply[]; prioritized: string[]; reduce: string[] };

export type Bidstream = {
  requests: number;
  decisions: { bid: number; throttle: number; no_bid: number; blocked: number };
  bid_rate: number;
  win_rate: number;
  impressions_won: number;
  avg_clearing_cpm: number;
  avg_second_price_cpm: number;
  est_spend: number;
  sim_budget: number;
  budget_utilization: number;
  avg_weighted_score: number;
  phi_blocked: number;
  frequency_capped: number;
  pace_throttled: number;
  targeting_filtered: number;
  ivt_filtered: number;
  givt: number;
  sivt: number;
  brand_safety_blocked: number;
  unique_reach: number;
  avg_frequency: number;
  carried_over_users: number;
  persisted_users: number;
  by_partner: { partner: string; requests: number; wins: number; win_rate: number; est_spend: number }[];
};

export type FrequencyState = {
  line_item_id: string;
  frequency_cap: number;
  unique_users: number;
  total_impressions: number;
  avg_frequency: number;
  over_cap_users: number;
  top: { user_key: number; impressions: number }[];
};

export type ReportSeriesPoint = { date: string; spend: number; impressions: number; clicks: number; conversions: number };
export type CampaignReport = {
  campaign_id: string;
  name: string;
  brand: string;
  status: string;
  budget: number;
  spend: number;
  pacing: number;
  pacing_status: string;
  source: string;
  impressions: number;
  clicks: number;
  conversions: number;
  ctr: number;
  cvr: number;
  cpa: number;
  ecpm: number;
  series: ReportSeriesPoint[];
};
export type Reporting = {
  days: number;
  source: string;
  live_campaigns: number;
  portfolio: { impressions: number; clicks: number; conversions: number; spend: number; ctr: number; cpa: number };
  campaigns: CampaignReport[];
};

export type RtbBid = { id: string; impid: string; price: number; nurl: string; burl: string; adm: string; crid: string; w?: number | null; h?: number | null };
export type RtbBidResponse = { id: string; bidid: string; cur: string; seatbid: { seat: string; bid: RtbBid[] }[] };
export type RtbWin = { id: string; line_item_id: string; request_id: string; imp_id: string; partner: string; bid_price_cpm: number; clear_price_cpm: number | null; status: string; ts: string };

export type Connector = { id: string; name: string; kind: string; status: string; config_json: string; last_sync: string | null; created_at: string; fact_count: number };
export type ConnectorFacts = { by_source: { source: string; n: number; impressions: number; clicks: number; conversions: number; spend: number }[] };

export type MeasurementResultDetail = {
  id: string;
  plan_id: string;
  campaign_id: string;
  study_type: string;
  exposed_rate: number;
  control_rate: number;
  observed_relative_lift_pct: number;
  absolute_lift_pp: number;
  ci_95_pp: [number, number];
  p_value: number;
  significant: boolean;
  incremental_conversions: number;
  cost_per_incremental_conversion: number | null;
  roas: number | null;
  media_spend: number;
  planned_lift_pct: number;
  planned_power: number;
  verdict: string;
};

export type StoredResult = {
  id: string;
  plan_id: string;
  campaign_id: string;
  campaign_name: string;
  observed_lift_pct: number;
  absolute_lift_pp: number;
  p_value: number;
  significant: boolean;
  incremental_conversions: number;
  cpic: number | null;
  roas: number | null;
  created_at: string;
};

export type AudienceOverlap = {
  audiences: { id: string; name: string; type: string; reach: number; npi_count: number; match_rate: number }[];
  combined_reach: number;
  deduplicated_unique_reach: number;
  overlap: number;
  overlap_pct: number;
  addressable_npis: number;
  avg_match_rate: number;
  pairs: { a: string; b: string; overlap: number }[];
  note: string;
};

export type ComplianceFinding = { severity: string; area: string; entity: string; issue: string };
export type Compliance = {
  compliance_score: number;
  checks: Record<string, boolean>;
  findings: ComplianceFinding[];
  creatives_blocked_from_serving: number;
  scanned_at: string;
};

export type FrequencyGovernance = {
  by_channel: { channel: string; lines: number; min_cap: number; max_cap: number; avg_cap: number; audiences: string[] }[];
  recommended_global_weekly_cap: number;
  uncoordinated_cap_pressure: number;
  channels_over_recommended: string[];
  note: string;
};

export type Overview = { kpis: Record<string, number>; narrative: string; storage_backend?: string };

export type VastTag = { id: string; name: string; vast_url: string; channel: string; duration: number; skippable: number; status: string; created_at: string };
export type VastValidate = { valid: boolean; reasons: string[]; version: string | null; media_files: string[] };
export type BlocklistItem = { id: string; value: string; kind: string; reason: string; created_at: string };
export type BrandSafety = { config: { blocked_categories: string[]; sensitivity: string }; categories: string[]; sensitivity_tiers: string[]; blocklist: BlocklistItem[] };
export type IvtRow = { partner: string; channel: string; givt_rate: number; sivt_rate: number; valid_rate: number; status: string };
export type IvtReport = { by_partner: IvtRow[]; avg_valid_rate: number; note: string };

export type Advertiser = { id: string | null; name: string; kind: string; status: string; created_at?: string; campaigns: number; total_budget: number };
export type PacingAdjustment = { line_item_id: string; name: string; campaign: string; pacing: number; action: 'raise_bid' | 'lower_bid' | 'hold'; old_bid_cpm: number; new_bid_cpm: number; reason: string; applied: boolean };
export type PacingAuto = { apply: boolean; adjustments: PacingAdjustment[]; adjusted: number; generated_at: string };
export type ReportView = { id: string; name: string; config: { days?: number }; created_at?: string };

export type Alert = { severity: 'critical' | 'warning' | 'info'; category: string; message: string; metric: string; value: number };
export type AlertsData = { alerts: Alert[]; counts: { critical: number; warning: number; info: number }; total: number; generated_at: string };

export type Recommendation = { priority: 'high' | 'medium' | 'low'; category: string; title: string; detail: string; tab: string };
export type Insights = { recommendations: Recommendation[]; counts: { high: number; medium: number; low: number }; generated_at: string };

export type Channel = { id: string; label: string; typical_cpm: [number, number]; devices: string[]; note: string };
export type Channels = { channels: Channel[]; devices: string[]; brand_safety_tiers: string[] };
export type Targeting = { line_item_id: string; devices: string[]; geos: string[]; dayparts: number[]; brand_safety: string; viewability_target: number; updated_at: string | null };

export type PlannerRow = { channel: string; pct: number; spend: number; cpm: number; impressions: number; est_reach: number };
export type Planner = { budget: number; frequency: number; channels: PlannerRow[]; totals: { spend: number; impressions: number; blended_cpm: number; est_unique_reach: number } };

export function friendlyError(err: unknown, fallback: string): string {
  const message = err instanceof Error ? err.message : String(err || fallback);
  if (message.toLowerCase().includes('failed to fetch') || message.toLowerCase().includes('networkerror')) {
    return `Cannot reach the Full DSP API at ${API_BASE}. Start the backend with: cd backend && uvicorn full_dsp_server:app --reload --port 8090. If this frontend is deployed, set VITE_FULL_DSP_API_URL to the hosted backend URL instead of localhost.`;
  }
  return message || fallback;
}

export const TOKEN_KEY = 'pharma_signal_full_token';
export const REFRESH_KEY = 'pharma_signal_refresh_token';

// Exchange the stored refresh token for a fresh access token. Returns the new
// access token, or null if refresh is impossible (no/expired refresh token).
async function tryRefresh(): Promise<string | null> {
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  if (!refreshToken) return null;
  try {
    const resp = await fetch(`${API_BASE}/api/full/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!resp.ok) return null;
    const data = await resp.json();
    localStorage.setItem(TOKEN_KEY, data.access_token);
    if (data.refresh_token) localStorage.setItem(REFRESH_KEY, data.refresh_token);
    return data.access_token as string;
  } catch {
    return null;
  }
}

export function createClient(getToken: () => string) {
  async function rawRequest<T>(path: string, init: RequestInit, token: string): Promise<Response> {
    return fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...(init.headers || {}) },
    });
  }
  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    let response = await rawRequest<T>(path, init, getToken());
    if (response.status === 401) {
      // Access token likely expired — silently refresh and retry once.
      const newToken = await tryRefresh();
      if (newToken) response = await rawRequest<T>(path, init, newToken);
    }
    if (!response.ok) throw new Error(await response.text());
    return response.json() as Promise<T>;
  }
  return {
    request,
    get: <T>(path: string) => request<T>(path),
    post: <T>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
    put: <T>(path: string, body: unknown) => request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  };
}

export async function loginRequest(email: string, password: string): Promise<{ access_token: string; refresh_token?: string; user: User }> {
  const response = await fetch(`${API_BASE}/api/full/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}
