export type Channel = 'Display' | 'Video' | 'CTV' | 'Audio' | 'Native' | 'Search Extension';

export type AudienceType = 'HCP' | 'DTC' | 'Hybrid' | 'Contextual';

export type PartnerStatus = 'Ready' | 'QA Required' | 'Scaling' | 'Experimental';

export type Decision = 'bid' | 'throttle' | 'reject';

export type Campaign = {
  id: string;
  brand: string;
  indication: string;
  audienceType: AudienceType;
  audience: string;
  budget: number;
  flightWeeks: number;
  primaryKpi: string;
  outcomeKpi: string;
  baseCpm: number;
  targetFrequencyPerWeek: number;
  maxFrequencyPerDay: number;
  expectedCpa: number;
  priorityScore: number;
  complianceNotes: string[];
  optimizationFocus: string;
};

export type SupplyPartner = {
  id: string;
  name: string;
  channel: Channel;
  type: string;
  quality: number;
  matchRate: number;
  dataCost: number;
  winRate: number;
  viewability: number;
  fraudRisk: number;
  bidFloorCpm: number;
  integrations: string[];
  status: PartnerStatus;
  recommendation: string;
};

export type AudienceSegment = {
  id: string;
  name: string;
  type: AudienceType;
  source: string;
  estimatedReach: number;
  matchRate: number;
  dataCostCpm: number;
  qualityScore: number;
  privacyPosture: string;
  activationRule: string;
};

export type BidRequest = {
  id: string;
  campaignId: string;
  partnerId: string;
  channel: Channel;
  audienceMatch: number;
  contextualRelevance: number;
  outcomeSignal: number;
  frequencySeenToday: number;
  predictedCtr: number;
  predictedConversionRate: number;
  floorCpm: number;
};

export type BidDecision = {
  requestId: string;
  decision: Decision;
  maxBidCpm: number;
  bidMultiplier: number;
  supplyScore: number;
  workingMediaRatio: number;
  confidence: number;
  reasons: string[];
  riskFlags: string[];
};

export type MeasurementPlan = {
  campaignId: string;
  expectedConversions: number;
  exposedSample: number;
  controlSample: number;
  minimumDetectableLift: number;
  powerScore: number;
  recommendation: string;
};

export type PacingSnapshot = {
  campaignId: string;
  spendToDate: number;
  daysElapsed: number;
  totalDays: number;
  impressions: number;
  conversions: number;
};

export type PartnerIntegration = {
  name: string;
  category: 'SSP' | 'Identity' | 'Measurement' | 'Analytics' | 'Verification' | 'Data Warehouse';
  purpose: string;
  connectionPattern: string;
  status: PartnerStatus;
};

export type ComplianceControl = {
  title: string;
  guardrail: string;
  owner: string;
  severity: 'Core' | 'High' | 'Critical';
};
