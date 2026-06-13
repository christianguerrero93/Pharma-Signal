export type AdapterHealth = 'connected' | 'needs_credentials' | 'mocked' | 'not_started';

export type ConnectorResult<T> = {
  source: string;
  health: AdapterHealth;
  syncedAt: string;
  records: T[];
  warnings: string[];
};

export type Ga4Event = {
  campaignId: string;
  eventName: string;
  sessions: number;
  engagedSessions: number;
  keyEvents: number;
};

export type SspDeliveryRecord = {
  partnerId: string;
  dealId: string;
  impressions: number;
  spend: number;
  viewability: number;
  fraudRate: number;
};

export type MeasurementRecord = {
  campaignId: string;
  exposed: number;
  control: number;
  conversionsExposed: number;
  conversionsControl: number;
  lift: number;
};

const syncedAt = new Date().toISOString();

export function mockGa4Sync(): ConnectorResult<Ga4Event> {
  return {
    source: 'GA4 Data API',
    health: 'mocked',
    syncedAt,
    warnings: ['Replace mock connector with OAuth-backed GA4 Data API client before production use.'],
    records: [
      { campaignId: 'tzield-dtc', eventName: 'qualified_site_visit', sessions: 18420, engagedSessions: 11964, keyEvents: 712 },
      { campaignId: 'flu-rsv', eventName: 'pharmacy_locator_click', sessions: 9620, engagedSessions: 6814, keyEvents: 438 },
    ],
  };
}

export function mockSspDeliverySync(): ConnectorResult<SspDeliveryRecord> {
  return {
    source: 'SSP delivery files',
    health: 'mocked',
    syncedAt,
    warnings: ['Normalize partner deal IDs before allowing auto-optimization.'],
    records: [
      { partnerId: 'pubmatic', dealId: 'PM-PHARMA-HCP-001', impressions: 428000, spend: 48600, viewability: 69, fraudRate: 0.8 },
      { partnerId: 'openx', dealId: 'OX-HEALTH-WEB-117', impressions: 311000, spend: 22600, viewability: 72, fraudRate: 1.1 },
      { partnerId: 'magnite', dealId: 'MG-CTV-RSV-902', impressions: 98000, spend: 19200, viewability: 92, fraudRate: 0.4 },
    ],
  };
}

export function mockMeasurementSync(): ConnectorResult<MeasurementRecord> {
  return {
    source: 'Outcome measurement import',
    health: 'mocked',
    syncedAt,
    warnings: ['Read as directional until exposed/control methodology is finalized.'],
    records: [
      { campaignId: 'tzield-dtc', exposed: 820000, control: 196000, conversionsExposed: 1180, conversionsControl: 238, lift: 0.18 },
      { campaignId: 'ms-hcp', exposed: 92000, control: 22000, conversionsExposed: 412, conversionsControl: 79, lift: 0.24 },
    ],
  };
}
