import type { BidDecision, BidRequest, Campaign, SupplyPartner } from '../types';
import { calculateBidDecision, formatCurrency } from './dspEngine';

export type OpenRtbInventory = {
  id: string;
  channel: BidRequest['channel'];
  domainOrApp: string;
  placement: string;
  bidFloorCpm: number;
  dealId?: string;
};

export type PharmaComplianceEnvelope = {
  audienceType: Campaign['audienceType'];
  creativeApproved: boolean;
  containsPhi: boolean;
  geoAllowed: boolean;
  minAudienceSize: number;
  mlrNotes: string[];
};

export type PharmaOpenRtbRequest = {
  id: string;
  campaignId: string;
  partnerId: string;
  inventory: OpenRtbInventory;
  audienceMatch: number;
  contextualRelevance: number;
  outcomeSignal: number;
  frequencySeenToday: number;
  predictedCtr: number;
  predictedConversionRate: number;
  compliance: PharmaComplianceEnvelope;
};

export type PharmaBidResponse = {
  id: string;
  bidId: string;
  campaignId: string;
  partnerId: string;
  dealId?: string;
  clearingPriceCpm: number;
  maxBidCpm: number;
  creativeId: string;
  adomain: string[];
  nurl: string;
  adm: string;
};

export type AuctionResult = {
  requestId: string;
  decision: BidDecision['decision'] | 'no_bid';
  decisionLabel: string;
  latencyBudgetMs: number;
  bidDecision?: BidDecision;
  response?: PharmaBidResponse;
  guardrails: string[];
  eventLog: string[];
};

function evaluateCompliance(request: PharmaOpenRtbRequest, campaign: Campaign) {
  const guardrails = [
    request.compliance.containsPhi ? 'Blocked: PHI-like data cannot enter the bidder.' : '',
    !request.compliance.creativeApproved ? 'Blocked: creative is not MLR approved.' : '',
    !request.compliance.geoAllowed ? 'Blocked: geo is outside approved activation footprint.' : '',
    request.compliance.minAudienceSize < 1000 ? 'Blocked: audience size is below aggregation threshold.' : '',
    request.compliance.audienceType !== campaign.audienceType && campaign.audienceType !== 'Hybrid'
      ? 'Blocked: request audience type does not match campaign partition.'
      : '',
  ].filter(Boolean);

  return guardrails;
}

export function runPharmaAuction(request: PharmaOpenRtbRequest, campaigns: Campaign[], partners: SupplyPartner[]): AuctionResult {
  const campaign = campaigns.find((item) => item.id === request.campaignId);
  const partner = partners.find((item) => item.id === request.partnerId);

  if (!campaign || !partner) {
    return {
      requestId: request.id,
      decision: 'no_bid',
      decisionLabel: 'No bid',
      latencyBudgetMs: 120,
      guardrails: ['Unknown campaign or partner.'],
      eventLog: ['auction.received', 'auction.rejected.unknown_entity'],
    };
  }

  const complianceBlocks = evaluateCompliance(request, campaign);
  if (complianceBlocks.length > 0) {
    return {
      requestId: request.id,
      decision: 'no_bid',
      decisionLabel: 'Compliance block',
      latencyBudgetMs: 120,
      guardrails: complianceBlocks,
      eventLog: ['auction.received', 'compliance.evaluated', 'auction.no_bid.compliance'],
    };
  }

  const bidRequest: BidRequest = {
    id: request.id,
    campaignId: request.campaignId,
    partnerId: request.partnerId,
    channel: request.inventory.channel,
    audienceMatch: request.audienceMatch,
    contextualRelevance: request.contextualRelevance,
    outcomeSignal: request.outcomeSignal,
    frequencySeenToday: request.frequencySeenToday,
    predictedCtr: request.predictedCtr,
    predictedConversionRate: request.predictedConversionRate,
    floorCpm: request.inventory.bidFloorCpm,
  };

  const bidDecision = calculateBidDecision(bidRequest, campaign, partner);
  const shouldBid = bidDecision.decision === 'bid' || bidDecision.decision === 'throttle';
  const clearingPriceCpm = Number(Math.min(Math.max(request.inventory.bidFloorCpm, bidDecision.maxBidCpm * 0.86), bidDecision.maxBidCpm).toFixed(2));

  const response: PharmaBidResponse | undefined = shouldBid
    ? {
        id: `resp-${request.id}`,
        bidId: `bid-${request.id}`,
        campaignId: campaign.id,
        partnerId: partner.id,
        dealId: request.inventory.dealId,
        clearingPriceCpm,
        maxBidCpm: bidDecision.maxBidCpm,
        creativeId: `${campaign.id}-education-safe-001`,
        adomain: ['pharmasignal.local'],
        nurl: `https://pharmasignal.local/win/${request.id}?price=${clearingPriceCpm}`,
        adm: `<div data-campaign="${campaign.id}" data-partner="${partner.id}">MLR-approved education creative</div>`,
      }
    : undefined;

  return {
    requestId: request.id,
    decision: shouldBid ? bidDecision.decision : 'no_bid',
    decisionLabel: shouldBid ? `${bidDecision.decision.toUpperCase()} at ${formatCurrency(clearingPriceCpm)} CPM` : 'No bid',
    latencyBudgetMs: 120,
    bidDecision,
    response,
    guardrails: [
      'No PHI payload accepted.',
      'Audience partition validated.',
      'Creative approval validated.',
      ...bidDecision.riskFlags,
    ],
    eventLog: [
      'auction.received',
      'compliance.evaluated',
      'bid.price_calculated',
      shouldBid ? 'auction.bid_response.created' : 'auction.no_bid.economics',
      'event_stream.queued',
    ],
  };
}

export function summarizeAuction(result: AuctionResult) {
  return {
    status: result.decisionLabel,
    risks: result.guardrails.length,
    events: result.eventLog.length,
    maxBid: result.response ? formatCurrency(result.response.maxBidCpm) : 'No bid',
  };
}
