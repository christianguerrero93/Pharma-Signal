import type { Campaign, PartnerIntegration, SupplyPartner } from '../types';

export type UserRole = 'admin' | 'trader' | 'analyst' | 'client_viewer' | 'compliance';

export type ControlPlaneAction = {
  id: string;
  actor: string;
  role: UserRole;
  action: string;
  entity: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  requiresApproval: boolean;
  createdAt: string;
};

export type ActivationApproval = {
  entity: string;
  status: 'approved' | 'blocked' | 'needs_review';
  checks: string[];
  approvers: UserRole[];
};

export function buildAuditTrail(campaigns: Campaign[], partners: SupplyPartner[]): ControlPlaneAction[] {
  const now = new Date().toISOString();
  const campaignActions: ControlPlaneAction[] = campaigns.map((campaign, index) => ({
    id: `audit-campaign-${index + 1}`,
    actor: 'platform@pharmasignal.local',
    role: 'trader',
    action: `Updated pacing and bid guardrails for ${campaign.brand}`,
    entity: campaign.id,
    riskLevel: campaign.complianceNotes.length > 2 ? 'high' : 'medium',
    requiresApproval: campaign.complianceNotes.length > 0,
    createdAt: now,
  }));

  const partnerActions: ControlPlaneAction[] = partners.map((partner, index) => ({
    id: `audit-partner-${index + 1}`,
    actor: 'supply-ops@pharmasignal.local',
    role: 'admin',
    action: `Validated ${partner.name} supply configuration and deal QA status`,
    entity: partner.id,
    riskLevel: partner.status === 'QA Required' ? 'high' : 'low',
    requiresApproval: partner.status === 'QA Required',
    createdAt: now,
  }));

  return [...campaignActions, ...partnerActions];
}

export function evaluateActivationApproval(campaign: Campaign, partner: SupplyPartner, integration: PartnerIntegration): ActivationApproval {
  const checks = [
    campaign.complianceNotes.length > 0 ? 'Campaign compliance notes attached.' : 'Campaign missing compliance notes.',
    partner.status === 'Ready' || partner.status === 'Scaling' ? 'Supply route is allowed for activation.' : 'Supply route needs QA before scale.',
    integration.status === 'Ready' || integration.status === 'QA Required' ? 'Integration path exists.' : 'Integration remains experimental.',
    campaign.audienceType === 'HCP' ? 'HCP reporting must stay aggregated and role-limited.' : 'Consumer activation must avoid sensitive health inference.',
  ];

  const blocked = partner.status === 'Experimental' || integration.status === 'Experimental';
  const needsReview = partner.status === 'QA Required' || integration.status === 'QA Required';

  return {
    entity: `${campaign.id}:${partner.id}:${integration.name}`,
    status: blocked ? 'blocked' : needsReview ? 'needs_review' : 'approved',
    checks,
    approvers: blocked || needsReview ? ['admin', 'compliance'] : ['trader'],
  };
}
