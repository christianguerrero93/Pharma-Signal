import {
  Activity,
  BadgeCheck,
  BarChart3,
  BrainCircuit,
  ClipboardCheck,
  DatabaseZap,
  LineChart,
  Network,
  ShieldCheck,
  Target,
  Zap,
} from 'lucide-react';
import { architectureLayers, audienceSegments, bidRequests, campaigns, complianceControls, integrations, pacingSnapshots, supplyPartners } from './data/dsp';
import { mockGa4Sync, mockMeasurementSync, mockSspDeliverySync } from './connectors/partnerAdapters';
import { buildMeasurementPlan, calculateBidDecision, calculatePacing, formatCurrency, formatNumber, scoreSupplyPartner } from './lib/dspEngine';
import type { BidDecision, Campaign, MeasurementPlan } from './types';

type BidDecisionRow = {
  campaign: Campaign;
  partnerName: string;
  decision: BidDecision;
};

type MeasurementRow = {
  campaign: Campaign;
  plan: MeasurementPlan;
};

const moduleCards = [
  {
    title: 'Audience intelligence',
    icon: Target,
    body: 'HCP lists, modeled patient audiences, contextual intent, GA4 engagement, geography, and retargeting rules in one planning layer.',
  },
  {
    title: 'Outcome-aware bidder',
    icon: Zap,
    body: 'Bid CPM is weighted by audience match, supply quality, working-media ratio, outcome signal, frequency, and floor-price economics.',
  },
  {
    title: 'Supply path optimization',
    icon: Network,
    body: 'PubMatic, Magnite, OpenX, Index Exchange, endemic health, curated PMPs, CTV, and open web routes are scored before scale.',
  },
  {
    title: 'Measurement planner',
    icon: LineChart,
    body: 'Forecasts conversion depth, exposed/control size, minimum detectable lift, and whether a campaign is ready to claim impact.',
  },
  {
    title: 'Compliance guardrails',
    icon: ShieldCheck,
    body: 'No PHI by design, audience separation, MLR-safe activation logic, audit logs, and privacy-conscious outcome measurement.',
  },
  {
    title: 'Partner adapters',
    icon: DatabaseZap,
    body: 'Scaffolded connector pattern for GA4, SSP delivery, Crossix/Swoop-style outcome imports, verification, and data warehouse syncs.',
  },
];

const roadmap = [
  ['01', 'OpenRTB bidder service', 'Move the current TypeScript bid model into a Go/Rust/Java low-latency bidder with Redis/Aerospike state.'],
  ['02', 'Control-plane API', 'Add campaign CRUD, line items, budgets, approvals, roles, and audit logs through FastAPI or Node.'],
  ['03', 'Warehouse + event stream', 'Pipe impressions, clicks, spend, conversions, and outcome reads through Kafka/Flink into BigQuery or Snowflake.'],
  ['04', 'Optimization models', 'Train supply, pacing, frequency, and outcome propensity models so the DSP improves every flight.'],
];

function App() {
  const averageSupplyScore = Math.round(
    supplyPartners.reduce((total, partner) => total + scoreSupplyPartner(partner), 0) / supplyPartners.length,
  );

  const totalBudget = campaigns.reduce((sum, campaign) => sum + campaign.budget, 0);
  const totalReach = audienceSegments.reduce((sum, segment) => sum + segment.estimatedReach, 0);

  const bidDecisionRows: BidDecisionRow[] = bidRequests
    .map((request) => {
      const campaign = campaigns.find((item) => item.id === request.campaignId);
      const partner = supplyPartners.find((item) => item.id === request.partnerId);
      if (!campaign || !partner) return null;

      return {
        campaign,
        partnerName: partner.name,
        decision: calculateBidDecision(request, campaign, partner),
      };
    })
    .filter((row): row is BidDecisionRow => Boolean(row));

  const measurementRows: MeasurementRow[] = campaigns
    .map((campaign) => {
      const pacing = pacingSnapshots.find((snapshot) => snapshot.campaignId === campaign.id);
      if (!pacing) return null;

      return {
        campaign,
        plan: buildMeasurementPlan(campaign, pacing),
      };
    })
    .filter((row): row is MeasurementRow => Boolean(row));

  const measurementReadyCount = measurementRows.filter((row) => row.plan.powerScore >= 70).length;
  const connectorFeeds = [mockGa4Sync(), mockSspDeliverySync(), mockMeasurementSync()];

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
          <div className="nav-links">
            <a href="#bidder">Bidder</a>
            <a href="#measurement">Measurement</a>
            <a href="#architecture">Architecture</a>
          </div>
        </nav>

        <div className="hero-grid">
          <div>
            <p className="eyebrow">Pharma-native demand-side platform</p>
            <h1>The DSP layer built around healthcare outcomes.</h1>
            <p className="hero-copy">
              Pharma Signal connects campaign strategy, audience quality, supply path economics, bid logic, frequency, measurement readiness, and compliance before media dollars are wasted. The goal is simple: make every bid defensible against business impact.
            </p>
            <div className="hero-actions">
              <a href="#command-center" className="primary-button">Open command center</a>
              <a href="#integrations" className="secondary-button">View integrations</a>
            </div>
          </div>

          <div className="signal-card hero-card">
            <div className="card-header">
              <div>
                <p className="eyebrow">DSP readiness score</p>
                <h2>{averageSupplyScore}/100</h2>
              </div>
              <Activity />
            </div>
            <p>
              The platform is ready for planning, simulation, partner QA, measurement forecasting, and Netlify deployment. Real-time bidding is represented as a typed scoring engine ready to move into a low-latency service.
            </p>
            <div className="meter"><span style={{ width: `${averageSupplyScore}%` }} /></div>
            <div className="metric-row">
              <span>Modeled budget</span>
              <strong>{formatCurrency(totalBudget)}</strong>
            </div>
            <div className="metric-row">
              <span>Modeled addressable reach</span>
              <strong>{formatNumber(totalReach)}</strong>
            </div>
            <div className="metric-row">
              <span>Measurement-ready plans</span>
              <strong>{measurementReadyCount}/{measurementRows.length}</strong>
            </div>
          </div>
        </div>
      </section>

      <section id="command-center" className="section dashboard-section">
        <div className="section-heading">
          <p className="eyebrow">Command center</p>
          <h2>One view for planning, activation, bidding, and proof.</h2>
          <p>
            The MVP now behaves like a real DSP control layer: every campaign has budget, frequency, outcome, compliance, pacing, supply, audience, and measurement logic attached.
          </p>
        </div>

        <div className="kpi-grid">
          <div className="kpi-card">
            <BadgeCheck />
            <span>Campaigns modeled</span>
            <strong>{campaigns.length} pharma programs</strong>
          </div>
          <div className="kpi-card">
            <BarChart3 />
            <span>Supply partners</span>
            <strong>{supplyPartners.length} routes scored</strong>
          </div>
          <div className="kpi-card">
            <BrainCircuit />
            <span>Bid engine</span>
            <strong>{bidDecisionRows.length} simulated requests</strong>
          </div>
          <div className="kpi-card">
            <ClipboardCheck />
            <span>Compliance posture</span>
            <strong>No PHI by design</strong>
          </div>
        </div>

        <div className="panel-grid campaign-grid">
          {campaigns.map((campaign) => {
            const pacing = pacingSnapshots.find((snapshot) => snapshot.campaignId === campaign.id);
            const pacingStatus = pacing ? calculatePacing(campaign, pacing) : null;

            return (
              <article className="panel campaign-panel" key={campaign.id}>
                <div className="panel-title">
                  <div>
                    <p className="eyebrow">{campaign.audienceType} · {campaign.indication}</p>
                    <h3>{campaign.brand}</h3>
                  </div>
                  <span>{formatCurrency(campaign.budget)}</span>
                </div>
                <p>{campaign.audience}</p>
                <div className="mini-metrics">
                  <span><strong>{campaign.targetFrequencyPerWeek}x</strong> weekly freq</span>
                  <span><strong>{formatCurrency(campaign.baseCpm)}</strong> base CPM</span>
                  <span><strong>{campaign.priorityScore}</strong> priority</span>
                </div>
                <strong className="green-callout">{campaign.optimizationFocus}</strong>
                {pacingStatus && (
                  <div className="status-strip">
                    <span>{pacingStatus.status}</span>
                    <strong>{pacingStatus.pacingIndex}% pacing index</strong>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      </section>

      <section id="bidder" className="section">
        <div className="section-heading">
          <p className="eyebrow">Bidder simulation</p>
          <h2>Bid only when audience, supply, cost, frequency, and outcome signal line up.</h2>
        </div>
        <div className="bid-grid">
          {bidDecisionRows.map((row) => (
            <article className={`bid-card decision-${row.decision.decision}`} key={row.decision.requestId}>
              <div className="panel-title">
                <div>
                  <p className="eyebrow">{row.partnerName}</p>
                  <h3>{row.campaign.brand}</h3>
                </div>
                <span>{row.decision.decision.toUpperCase()}</span>
              </div>
              <div className="bid-price">{formatCurrency(row.decision.maxBidCpm)} CPM</div>
              <div className="mini-metrics">
                <span><strong>{row.decision.bidMultiplier}x</strong> multiplier</span>
                <span><strong>{row.decision.confidence}</strong> confidence</span>
                <span><strong>{Math.round(row.decision.workingMediaRatio * 100)}%</strong> working media</span>
              </div>
              <ul>
                {row.decision.reasons.map((reason) => <li key={reason}>{reason}</li>)}
              </ul>
              {row.decision.riskFlags.length > 0 && (
                <div className="risk-box">
                  {row.decision.riskFlags.map((flag) => <span key={flag}>{flag}</span>)}
                </div>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <p className="eyebrow">Supply path scorecard</p>
          <h2>Know where working media is actually creating value.</h2>
        </div>
        <div className="supply-table">
          <div className="table-row table-head">
            <span>Partner</span>
            <span>Channel / type</span>
            <span>Score</span>
            <span>Economics</span>
            <span>Recommendation</span>
          </div>
          {supplyPartners.map((partner) => (
            <div className="table-row" key={partner.name}>
              <strong>{partner.name}</strong>
              <span>{partner.channel} · {partner.type}</span>
              <span className="score-pill">{scoreSupplyPartner(partner)}</span>
              <span>{partner.matchRate}% match · {partner.dataCost}% data · {partner.viewability}% viewability</span>
              <span>{partner.recommendation}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="section two-column-section">
        <div>
          <div className="section-heading">
            <p className="eyebrow">Audience activation</p>
            <h2>HCP, DTC, retargeting, and contextual logic are kept separate.</h2>
          </div>
          <div className="stacked-list">
            {audienceSegments.map((segment) => (
              <article className="list-card" key={segment.id}>
                <div className="panel-title">
                  <div>
                    <p className="eyebrow">{segment.type} · {segment.source}</p>
                    <h3>{segment.name}</h3>
                  </div>
                  <span>{formatNumber(segment.estimatedReach)}</span>
                </div>
                <p>{segment.activationRule}</p>
                <div className="mini-metrics">
                  <span><strong>{segment.matchRate}%</strong> match</span>
                  <span><strong>{formatCurrency(segment.dataCostCpm)}</strong> data CPM</span>
                  <span><strong>{segment.qualityScore}</strong> quality</span>
                </div>
                <small>{segment.privacyPosture}</small>
              </article>
            ))}
          </div>
        </div>

        <div id="measurement">
          <div className="section-heading">
            <p className="eyebrow">Measurement planner</p>
            <h2>Do we have enough signal to prove impact?</h2>
          </div>
          <div className="stacked-list">
            {measurementRows.map((row) => (
              <article className="list-card" key={row.campaign.id}>
                <div className="panel-title">
                  <div>
                    <p className="eyebrow">Power score</p>
                    <h3>{row.campaign.brand}</h3>
                  </div>
                  <span className="score-pill">{row.plan.powerScore}</span>
                </div>
                <div className="mini-metrics">
                  <span><strong>{formatNumber(row.plan.expectedConversions)}</strong> expected conv.</span>
                  <span><strong>{formatNumber(row.plan.exposedSample)}</strong> exposed</span>
                  <span><strong>{Math.round(row.plan.minimumDetectableLift * 100)}%</strong> MDE</span>
                </div>
                <p>{row.plan.recommendation}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="integrations" className="section">
        <div className="section-heading">
          <p className="eyebrow">Partner and data connections</p>
          <h2>Built so live connectors can replace mocked feeds cleanly.</h2>
        </div>
        <div className="integration-grid">
          {integrations.map((integration) => (
            <article className="module-card" key={integration.name}>
              <p className="eyebrow">{integration.category} · {integration.status}</p>
              <h3>{integration.name}</h3>
              <p>{integration.purpose}</p>
              <strong>{integration.connectionPattern}</strong>
            </article>
          ))}
        </div>
        <div className="connector-feed-grid">
          {connectorFeeds.map((feed) => (
            <article className="connector-card" key={feed.source}>
              <div className="panel-title">
                <h3>{feed.source}</h3>
                <span>{feed.health}</span>
              </div>
              <p>{feed.records.length} records synced · {feed.warnings[0]}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="architecture" className="section">
        <div className="section-heading">
          <p className="eyebrow">Architecture</p>
          <h2>A real DSP roadmap, delivered first as a hostable MVP.</h2>
        </div>
        <div className="module-grid">
          {moduleCards.map((module) => {
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
        <div className="architecture-table">
          {architectureLayers.map((layer) => (
            <div className="architecture-row" key={layer.layer}>
              <strong>{layer.layer}</strong>
              <span>{layer.stack}</span>
              <p>{layer.owns}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="section two-column-section">
        <div>
          <div className="section-heading">
            <p className="eyebrow">Compliance controls</p>
            <h2>Healthcare buying needs guardrails before scale.</h2>
          </div>
          <div className="stacked-list">
            {complianceControls.map((control) => (
              <article className="list-card" key={control.title}>
                <div className="panel-title">
                  <h3>{control.title}</h3>
                  <span>{control.severity}</span>
                </div>
                <p>{control.guardrail}</p>
                <small>Owner: {control.owner}</small>
              </article>
            ))}
          </div>
        </div>
        <div className="roadmap-panel">
          <div className="section-heading">
            <p className="eyebrow">Build roadmap</p>
            <h2>Next steps to move from prototype to production DSP.</h2>
          </div>
          <div className="roadmap-grid">
            {roadmap.map(([number, title, body]) => (
              <div key={title}>
                <span>{number}</span>
                <h3>{title}</h3>
                <p>{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

export default App;
