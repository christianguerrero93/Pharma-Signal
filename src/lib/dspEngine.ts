import type { BidDecision, BidRequest, Campaign, MeasurementPlan, PacingSnapshot, SupplyPartner } from '../types';

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

export function scoreSupplyPartner(partner: SupplyPartner) {
  const fraudSafety = 100 - partner.fraudRisk;
  const dataCostEfficiency = 100 - partner.dataCost;

  return Math.round(
    partner.quality * 0.24 +
      partner.matchRate * 0.2 +
      partner.viewability * 0.18 +
      dataCostEfficiency * 0.16 +
      partner.winRate * 0.12 +
      fraudSafety * 0.1,
  );
}

export function calculateWorkingMediaRatio(partner: SupplyPartner) {
  const platformFeeRate = 0.14;
  const dataRate = partner.dataCost / 100;
  const verificationRate = partner.fraudRisk > 10 ? 0.04 : 0.025;

  return clamp(1 - platformFeeRate - dataRate - verificationRate, 0.25, 0.92);
}

export function calculateBidDecision(request: BidRequest, campaign: Campaign, partner: SupplyPartner): BidDecision {
  const supplyScore = scoreSupplyPartner(partner);
  const workingMediaRatio = calculateWorkingMediaRatio(partner);
  const frequencyPenalty = request.frequencySeenToday >= campaign.maxFrequencyPerDay ? 0.58 : 1;
  const audienceMultiplier = 0.65 + request.audienceMatch / 100;
  const supplyMultiplier = 0.7 + supplyScore / 130;
  const outcomeMultiplier = 0.7 + request.outcomeSignal / 140;
  const contextMultiplier = 0.78 + request.contextualRelevance / 180;
  const costGuardrail = 0.74 + workingMediaRatio / 2;
  const predictedResponse = 1 + (request.predictedCtr + request.predictedConversionRate) / 100;

  const bidMultiplier = clamp(
    audienceMultiplier * supplyMultiplier * outcomeMultiplier * contextMultiplier * costGuardrail * frequencyPenalty * predictedResponse,
    0.25,
    2.8,
  );

  const maxBidCpm = Number((campaign.baseCpm * bidMultiplier).toFixed(2));
  const confidence = Math.round(
    request.audienceMatch * 0.28 + request.contextualRelevance * 0.18 + request.outcomeSignal * 0.22 + supplyScore * 0.22 + workingMediaRatio * 100 * 0.1,
  );

  const riskFlags = [
    request.frequencySeenToday >= campaign.maxFrequencyPerDay ? 'Frequency cap pressure' : '',
    partner.status === 'QA Required' ? 'Partner QA required before aggressive scaling' : '',
    workingMediaRatio < 0.48 ? 'Working-media ratio under threshold' : '',
    request.floorCpm > maxBidCpm ? 'Floor price exceeds max bid' : '',
  ].filter(Boolean);

  const reasons = [
    `Supply score ${supplyScore}/100`,
    `Audience match ${request.audienceMatch}/100`,
    `Outcome signal ${request.outcomeSignal}/100`,
    `Working media ${(workingMediaRatio * 100).toFixed(0)}%`,
  ];

  const decision = request.floorCpm > maxBidCpm || confidence < 58 ? 'reject' : riskFlags.length > 0 ? 'throttle' : 'bid';

  return {
    requestId: request.id,
    decision,
    maxBidCpm,
    bidMultiplier: Number(bidMultiplier.toFixed(2)),
    supplyScore,
    workingMediaRatio,
    confidence,
    reasons,
    riskFlags,
  };
}

export function buildMeasurementPlan(campaign: Campaign, pacing: PacingSnapshot): MeasurementPlan {
  const expectedConversions = Math.round(campaign.budget / campaign.expectedCpa);
  const observedConversionRate = pacing.conversions / Math.max(pacing.impressions, 1);
  const exposedSample = Math.round(campaign.budget / Math.max(campaign.baseCpm, 1) * 1000 * 0.72);
  const controlSample = Math.round(exposedSample * 0.22);
  const conversionDepthScore = clamp(expectedConversions / 2500, 0.2, 1);
  const sampleBalanceScore = clamp(controlSample / Math.max(exposedSample * 0.2, 1), 0.4, 1.2);
  const observedSignalScore = clamp(observedConversionRate * 1000, 0.3, 1.3);
  const powerScore = Math.round(clamp((conversionDepthScore * 0.45 + sampleBalanceScore * 0.25 + observedSignalScore * 0.3) * 100, 0, 98));
  const minimumDetectableLift = Number(clamp(0.28 - powerScore / 500, 0.04, 0.24).toFixed(2));

  const recommendation =
    powerScore >= 75
      ? 'Measurement-ready. Keep exposed/control design stable and avoid mid-flight audience resets.'
      : powerScore >= 55
        ? 'Promising, but needs more conversion depth or cleaner control sizing before claiming lift.'
        : 'Underpowered. Reframe as directional learning or increase budget, time, or event volume.';

  return {
    campaignId: campaign.id,
    expectedConversions,
    exposedSample,
    controlSample,
    minimumDetectableLift,
    powerScore,
    recommendation,
  };
}

export function calculatePacing(campaign: Campaign, pacing: PacingSnapshot) {
  const expectedSpend = campaign.budget * (pacing.daysElapsed / pacing.totalDays);
  const spendDelta = pacing.spendToDate - expectedSpend;
  const pacingIndex = Math.round((pacing.spendToDate / Math.max(expectedSpend, 1)) * 100);
  const remainingBudget = Math.max(campaign.budget - pacing.spendToDate, 0);
  const remainingDays = Math.max(pacing.totalDays - pacing.daysElapsed, 1);
  const requiredDailySpend = remainingBudget / remainingDays;
  const status = pacingIndex > 112 ? 'Overspending' : pacingIndex < 88 ? 'Underspending' : 'On pace';

  return {
    expectedSpend,
    spendDelta,
    pacingIndex,
    remainingBudget,
    requiredDailySpend,
    status,
  };
}

export function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: value >= 1000 ? 0 : 2,
  }).format(value);
}

export function formatNumber(value: number) {
  return new Intl.NumberFormat('en-US').format(value);
}
