import type { Campaign, PacingSnapshot, SupplyPartner } from '../types';
import { calculatePacing, scoreSupplyPartner } from './dspEngine';

export type BudgetRecommendation = {
  campaignId: string;
  brand: string;
  currentBudget: number;
  recommendedBudget: number;
  delta: number;
  confidence: number;
  status: 'increase' | 'hold' | 'decrease';
  rationale: string;
  guardrails: string[];
};

export type PortfolioOptimization = {
  totalCurrentBudget: number;
  totalRecommendedBudget: number;
  recommendations: BudgetRecommendation[];
  portfolioNotes: string[];
};

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

function averageSupplyScore(partners: SupplyPartner[]) {
  if (partners.length === 0) return 70;
  return partners.reduce((sum, partner) => sum + scoreSupplyPartner(partner), 0) / partners.length;
}

export function optimizePortfolioBudget(
  campaigns: Campaign[],
  pacingSnapshots: PacingSnapshot[],
  partners: SupplyPartner[],
): PortfolioOptimization {
  const supplyScore = averageSupplyScore(partners);
  const recommendations = campaigns.map((campaign) => {
    const pacing = pacingSnapshots.find((snapshot) => snapshot.campaignId === campaign.id);
    const pacingSignal = pacing ? calculatePacing(campaign, pacing) : undefined;
    const priorityWeight = campaign.priorityScore / 100;
    const supplyWeight = supplyScore / 100;
    const conversionEfficiency = pacing ? clamp((pacing.conversions / Math.max(pacing.spendToDate, 1)) * campaign.expectedCpa, 0.55, 1.45) : 1;
    const pacingWeight = pacingSignal ? clamp(100 / Math.max(pacingSignal.pacingIndex, 1), 0.75, 1.25) : 1;
    const confidence = Math.round(clamp(priorityWeight * 36 + supplyWeight * 28 + conversionEfficiency * 24 + pacingWeight * 12, 42, 96));
    const budgetMultiplier = clamp(0.82 + priorityWeight * 0.28 + (conversionEfficiency - 1) * 0.18 + (pacingWeight - 1) * 0.12, 0.72, 1.24);
    const recommendedBudget = Math.round((campaign.budget * budgetMultiplier) / 1000) * 1000;
    const delta = recommendedBudget - campaign.budget;
    const status = delta > campaign.budget * 0.05 ? 'increase' : delta < campaign.budget * -0.05 ? 'decrease' : 'hold';

    const guardrails = [
      campaign.audienceType === 'HCP' ? 'Protect NPI precision and HCP-only reporting.' : '',
      pacingSignal?.status === 'Overspending' ? 'Do not increase until pacing normalizes.' : '',
      campaign.complianceNotes[0],
    ].filter(Boolean);

    const rationale =
      status === 'increase'
        ? 'Priority, conversion efficiency, and supply quality support additional working media.'
        : status === 'decrease'
          ? 'Reallocate dollars until efficiency, pacing, or measurement depth improves.'
          : 'Budget is directionally right; optimize supply and frequency before changing spend.';

    return {
      campaignId: campaign.id,
      brand: campaign.brand,
      currentBudget: campaign.budget,
      recommendedBudget,
      delta,
      confidence,
      status,
      rationale,
      guardrails,
    };
  });

  return {
    totalCurrentBudget: campaigns.reduce((sum, campaign) => sum + campaign.budget, 0),
    totalRecommendedBudget: recommendations.reduce((sum, recommendation) => sum + recommendation.recommendedBudget, 0),
    recommendations,
    portfolioNotes: [
      'Budget recommendations are constrained by compliance notes and measurement readiness.',
      'Optimizer prefers verified reach and conversion depth over raw impression scale.',
      'Production version should add brand-level caps, payer/geography limits, and approval workflow.',
    ],
  };
}
