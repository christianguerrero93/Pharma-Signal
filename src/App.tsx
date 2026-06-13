import { Activity, BadgeCheck, BarChart3, BrainCircuit, ClipboardCheck, DatabaseZap, LineChart, Network, ShieldCheck, Target, Zap } from 'lucide-react';

type SupplyPartner = {
  name: string;
  type: string;
  quality: number;
  matchRate: number;
  dataCost: number;
  winRate: number;
  recommendation: string;
};

type CampaignSignal = {
  brand: string;
  audience: string;
  budget: string;
  primaryKpi: string;
  signal: string;
  action: string;
};

const supplyPartners: SupplyPartner[] = [
  {
    name: 'PubMatic',
    type: 'Curated PMP / in-app scale',
    quality: 82,
    matchRate: 71,
    dataCost: 38,
    winRate: 46,
    recommendation: 'Increase bids on verified HCP and high-attention mobile supply.',
  },
  {
    name: 'Magnite',
    type: 'CTV / premium video',
    quality: 88,
    matchRate: 62,
    dataCost: 29,
    winRate: 34,
    recommendation: 'Use for high-frequency CTV reach when outcome signal is stable.',
  },
  {
    name: 'OpenX',
    type: 'Open web / curated health inventory',
    quality: 79,
    matchRate: 68,
    dataCost: 24,
    winRate: 52,
    recommendation: 'Scale cautiously after seat and deal ID validation.',
  },
  {
    name: 'Index Exchange',
    type: 'Premium web supply',
    quality: 84,
    matchRate: 58,
    dataCost: 21,
    winRate: 31,
    recommendation: 'Prioritize for low-fraud, higher-viewability placements.',
  },
];

const campaignSignals: CampaignSignal[] = [
  {
    brand: 'TZIELD DTC',
    audience: 'At-risk diabetes / autoimmune context',
    budget: '$1.71M',
    primaryKpi: 'Quality reach + new patient starts',
    signal: 'Frequency pressure rising while qualified reach remains constrained.',
    action: 'Hold 7-10x weekly frequency and shift excess bids to contextual + CTV extensions.',
  },
  {
    brand: 'MS HCP',
    audience: 'Neurologists + ICD-10 G35 signal',
    budget: '$645K',
    primaryKpi: 'Verified HCP engagement',
    signal: 'Target list alone cannot absorb full budget efficiently.',
    action: 'Layer Swoop predictive and endemic supply while protecting NPI precision.',
  },
  {
    brand: 'Flu / RSV',
    audience: 'Retail pharmacists + vaccine intenders',
    budget: 'Seasonal',
    primaryKpi: 'Reach, sustained frequency, vaccination intent',
    signal: 'Retail footprint targeting requires budget support to preserve frequency.',
    action: 'Model budget required by audience count, weeks live, and impression frequency.',
  },
];

const modules = [
  {
    title: 'Audience Intelligence',
    icon: Target,
    body: 'Unifies HCP lists, predictive patient segments, contextual health signals, GA4 engagement, and geography into one planning view.',
  },
  {
    title: 'Outcome-Aware Bid Logic',
    icon: Zap,
    body: 'Weights bid multipliers by audience quality, supply quality, data cost, frequency, engagement, and expected Rx or business impact.',
  },
  {
    title: 'Supply Path Optimization',
    icon: Network,
    body: 'Scores PubMatic, Magnite, OpenX, Index Exchange, curated PMPs, CTV, endemic, and open web routes before budget is wasted.',
  },
  {
    title: 'Measurement Planner',
    icon: LineChart,
    body: 'Forecasts whether a campaign can reach statistical confidence based on spend, conversions, exposed volume, and control size.',
  },
  {
    title: 'Compliance Guardrails',
    icon: ShieldCheck,
    body: 'Designed around no-PHI storage, audit logs, role access, MLR-safe language, and privacy-conscious outcome measurement.',
  },
  {
    title: 'Partner Integrations',
    icon: DatabaseZap,
    body: 'Roadmap includes GA4, CSV/XLSX upload, Swoop, Crossix, DeepIntent-style Rx reporting, SSP adapters, and verification partners.',
  },
];

function scorePartner(partner: SupplyPartner) {
  const dataCostPenalty = 100 - partner.dataCost;
  return Math.round(partner.quality * 0.35 + partner.matchRate * 0.25 + dataCostPenalty * 0.2 + partner.winRate * 0.2);
}

function App() {
  const averageSupplyScore = Math.round(
    supplyPartners.reduce((total, partner) => total + scorePartner(partner), 0) / supplyPartners.length,
  );

  return (
    <main>
      <section className="hero">
        <nav className="nav">
          <div className="brand-lockup">
            <div className="brand-mark">PS</div>
            <div>
              <p className="eyebrow">Pharma Signal</p>
              <strong>Healthcare DSP Command Center</strong>
            </div>
          </div>
          <a className="nav-cta" href="#roadmap">Roadmap</a>
        </nav>

        <div className="hero-grid">
          <div>
            <p className="eyebrow">Pharma-native buying intelligence</p>
            <h1>Build the DSP layer pharma teams actually need.</h1>
            <p className="hero-copy">
              Pharma Signal connects audience strategy, supply path quality, bid logic, data costs, pacing, and outcome measurement before launch — so teams can answer why this partner, why this budget, and what business impact should be expected.
            </p>
            <div className="hero-actions">
              <a href="#dashboard" className="primary-button">View command center</a>
              <a href="#architecture" className="secondary-button">See architecture</a>
            </div>
          </div>

          <div className="signal-card hero-card">
            <div className="card-header">
              <div>
                <p className="eyebrow">Live planning score</p>
                <h2>{averageSupplyScore}/100</h2>
              </div>
              <Activity />
            </div>
            <p>
              Supply quality is strong, but the platform is flagging data-cost pressure and audience precision risk before bid scaling.
            </p>
            <div className="meter"><span style={{ width: `${averageSupplyScore}%` }} /></div>
            <div className="metric-row">
              <span>Verified reach</span>
              <strong>High</strong>
            </div>
            <div className="metric-row">
              <span>Data-cost pressure</span>
              <strong>Medium</strong>
            </div>
            <div className="metric-row">
              <span>Outcome readiness</span>
              <strong>Improving</strong>
            </div>
          </div>
        </div>
      </section>

      <section id="dashboard" className="section dashboard-section">
        <div className="section-heading">
          <p className="eyebrow">MVP dashboard</p>
          <h2>Signals that make the DSP commercially useful.</h2>
          <p>
            This turns the project from a generic ad-tech UI into a pharma-specific planning layer: audience, supply, cost, measurement, and compliance all in one story.
          </p>
        </div>

        <div className="kpi-grid">
          <div className="kpi-card">
            <BadgeCheck />
            <span>Verified HCP / DTC logic</span>
            <strong>Built into planning</strong>
          </div>
          <div className="kpi-card">
            <BarChart3 />
            <span>Outcome measurement</span>
            <strong>Rx + conversion ready</strong>
          </div>
          <div className="kpi-card">
            <BrainCircuit />
            <span>Optimization engine</span>
            <strong>Signal weighted</strong>
          </div>
          <div className="kpi-card">
            <ClipboardCheck />
            <span>MLR / privacy posture</span>
            <strong>No PHI by design</strong>
          </div>
        </div>

        <div className="panel-grid">
          <div className="panel wide-panel">
            <div className="panel-title">
              <h3>Campaign intelligence</h3>
              <span>Planning + optimization</span>
            </div>
            <div className="campaign-list">
              {campaignSignals.map((campaign) => (
                <article key={campaign.brand} className="campaign-card">
                  <div>
                    <p className="eyebrow">{campaign.audience}</p>
                    <h4>{campaign.brand}</h4>
                  </div>
                  <div className="campaign-meta">
                    <span>{campaign.budget}</span>
                    <span>{campaign.primaryKpi}</span>
                  </div>
                  <p>{campaign.signal}</p>
                  <strong>{campaign.action}</strong>
                </article>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-title">
              <h3>Bid decision formula</h3>
              <span>Prototype logic</span>
            </div>
            <code className="formula">
              Bid = BaseCPM × AudienceValue × SupplyQuality × OutcomeSignal × FrequencyControl × DataCostGuardrail
            </code>
            <p>
              The early product direction is not to outbid everyone. It is to bid smarter where verified audience, quality supply, and downstream value line up.
            </p>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <p className="eyebrow">Supply path scorecard</p>
          <h2>Know where the working media is actually creating value.</h2>
        </div>
        <div className="supply-table">
          <div className="table-row table-head">
            <span>Partner</span>
            <span>Type</span>
            <span>Score</span>
            <span>Recommendation</span>
          </div>
          {supplyPartners.map((partner) => (
            <div className="table-row" key={partner.name}>
              <strong>{partner.name}</strong>
              <span>{partner.type}</span>
              <span className="score-pill">{scorePartner(partner)}</span>
              <span>{partner.recommendation}</span>
            </div>
          ))}
        </div>
      </section>

      <section id="architecture" className="section">
        <div className="section-heading">
          <p className="eyebrow">Architecture</p>
          <h2>Designed as a real DSP roadmap, delivered first as a hostable MVP.</h2>
        </div>
        <div className="module-grid">
          {modules.map((module) => {
            const Icon = module.icon;
            return (
              <article className="module-card" key={module.title}>
                <Icon />
                <h3>{module.title}</h3>
                <p>{module.body}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section id="roadmap" className="section roadmap">
        <div className="section-heading">
          <p className="eyebrow">Build roadmap</p>
          <h2>Next features to turn the MVP into a fuller platform.</h2>
        </div>
        <div className="roadmap-grid">
          <div>
            <span>01</span>
            <h3>CSV/XLSX ingestion</h3>
            <p>Upload campaign spend, conversions, audience files, NPI lists, supply reports, and GA4 exports.</p>
          </div>
          <div>
            <span>02</span>
            <h3>Measurement calculator</h3>
            <p>Estimate statistical confidence, minimum conversions, exposed/control sizing, and expected lift range.</p>
          </div>
          <div>
            <span>03</span>
            <h3>Bid simulator</h3>
            <p>Model how bid multipliers change with supply quality, frequency, data cost, and outcome value.</p>
          </div>
          <div>
            <span>04</span>
            <h3>Partner adapters</h3>
            <p>Add GA4, Swoop/Crossix-style measurement imports, SSP deal QA, and verification reporting connectors.</p>
          </div>
        </div>
      </section>
    </main>
  );
}

export default App;
