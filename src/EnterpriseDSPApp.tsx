import { FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity, BadgeCheck, Boxes, ClipboardList, Gauge, LayoutDashboard, Lock, PencilRuler,
  RefreshCw, Radio, ShieldCheck, SlidersHorizontal, Target, TrendingUp, Users, Zap,
} from 'lucide-react';
import {
  API_BASE, DEFAULT_PASSWORD, createClient, friendlyError, loginRequest,
  Audience, BidFactors, Bidstream, Campaign, Compliance, Creative, Deal, Forecast,
  FrequencyGovernance, MeasurementPlan, Optimizer, Overview, RankedSupply, Reporting,
  SupplyOptimize, SupplyPath, User, Workbench,
} from './api/fullDspClient';

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------
const money = (v: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(v || 0);
const money2 = (v: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(v || 0);
const num = (v: number) => new Intl.NumberFormat('en-US').format(Math.round(v || 0));
const pct = (v: number) => `${Math.round((v || 0) * 100)}%`;
const pct1 = (v: number) => `${((v || 0) * 100).toFixed(1)}%`;

const starterBidFactors: BidFactors = {
  audience_quality_weight: 0.28, supply_quality_weight: 0.22, outcome_signal_weight: 0.24,
  contextual_relevance_weight: 0.12, working_media_weight: 0.1, frequency_penalty_weight: 0.04,
  bid_shading_pct: 0.12, max_bid_multiplier: 2.5, data_cost_guardrail: 0.35,
};

type TabKey =
  | 'overview' | 'campaigns' | 'audiences' | 'creative' | 'supply'
  | 'bidder' | 'measurement' | 'optimization' | 'reporting' | 'compliance' | 'audit';

const TABS: { key: TabKey; label: string; icon: ReactNode }[] = [
  { key: 'overview', label: 'Overview', icon: <LayoutDashboard size={16} /> },
  { key: 'campaigns', label: 'Campaigns', icon: <ClipboardList size={16} /> },
  { key: 'audiences', label: 'Audiences', icon: <Users size={16} /> },
  { key: 'creative', label: 'Creative & MLR', icon: <BadgeCheck size={16} /> },
  { key: 'supply', label: 'Supply & Deals', icon: <Boxes size={16} /> },
  { key: 'bidder', label: 'Bidder', icon: <Radio size={16} /> },
  { key: 'measurement', label: 'Measurement', icon: <Target size={16} /> },
  { key: 'optimization', label: 'Optimization', icon: <TrendingUp size={16} /> },
  { key: 'reporting', label: 'Reporting', icon: <Gauge size={16} /> },
  { key: 'compliance', label: 'Compliance', icon: <ShieldCheck size={16} /> },
  { key: 'audit', label: 'Audit', icon: <Activity size={16} /> },
];

function Badge({ tone, children }: { tone: string; children: ReactNode }) {
  return <span className={`pill pill-${tone}`}>{children}</span>;
}

function Panel({ eyebrow, title, icon, children, actions }: { eyebrow: string; title: string; icon?: ReactNode; children: ReactNode; actions?: ReactNode }) {
  return (
    <section className="dsp-panel">
      <div className="panel-title">
        <div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div>
        {actions || icon}
      </div>
      {children}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Root
// ---------------------------------------------------------------------------
export default function EnterpriseDSPApp() {
  const [token, setToken] = useState(localStorage.getItem('pharma_signal_full_token') || '');
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState('admin@pharmasignal.local');
  const [password, setPassword] = useState(DEFAULT_PASSWORD);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<TabKey>('overview');

  const [workbench, setWorkbench] = useState<Workbench | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);

  const client = useMemo(() => createClient(() => token), [token]);

  const loadCore = useCallback(async () => {
    if (!token) return;
    setBusy(true);
    try {
      const [wb, ov] = await Promise.all([
        client.get<Workbench>('/api/full/workbench'),
        client.get<Overview>('/api/full/overview'),
      ]);
      setWorkbench(wb);
      setOverview(ov);
      setUser(wb.user);
      setError('');
    } catch (err) {
      setError(friendlyError(err, 'Unable to load DSP workbench'));
    } finally {
      setBusy(false);
    }
  }, [client, token]);

  useEffect(() => { loadCore(); }, [loadCore]);

  async function login(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const data = await loginRequest(email, password);
      localStorage.setItem('pharma_signal_full_token', data.access_token);
      setToken(data.access_token);
      setUser(data.user);
    } catch (err) {
      setError(friendlyError(err, 'Login failed'));
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    localStorage.removeItem('pharma_signal_full_token');
    setToken('');
    setUser(null);
    setWorkbench(null);
    setOverview(null);
  }

  if (!token || !user) {
    return (
      <main className="dsp-app login-screen">
        <section className="login-card">
          <div className="brand-mark large-mark">PS</div>
          <p className="eyebrow">Pharma-native DSP</p>
          <h1>Pharma Signal</h1>
          <p>Sign in to the command OS: campaigns, audiences, MLR creative review, supply paths, bidder, measurement power, optimization, reporting, and compliance.</p>
          <form onSubmit={login} className="form-grid">
            <label>Email<input value={email} onChange={(e) => setEmail(e.target.value)} /></label>
            <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
            <button className="primary-button" disabled={busy}><Lock size={16} /> Sign in</button>
          </form>
          <small>API: {API_BASE}. Local dev users use `@pharmasignal.local`; set `FULL_DSP_DEV_PASSWORD` to change the seed password. Roles: admin, trader, analyst.</small>
          {error && <div className="error-box">{error}</div>}
        </section>
      </main>
    );
  }

  return (
    <main className="dsp-app">
      <nav className="dsp-nav">
        <div className="brand-lockup"><div className="brand-mark">PS</div><div><p className="eyebrow">Enterprise DSP</p><strong>Pharma Signal Command OS</strong></div></div>
        <div className="nav-actions">
          <span>{user.email} · {user.role}</span>
          <button onClick={loadCore} disabled={busy}><RefreshCw size={16} /> Refresh</button>
          <button onClick={logout}>Logout</button>
        </div>
      </nav>

      <div className="tab-bar">
        {TABS.map((t) => (
          <button key={t.key} className={`tab-button ${tab === t.key ? 'active' : ''}`} onClick={() => setTab(t.key)}>
            {t.icon}<span>{t.label}</span>
          </button>
        ))}
      </div>

      {error && <div className="error-box wide">{error}</div>}

      {tab === 'overview' && <OverviewTab overview={overview} workbench={workbench} client={client} />}
      {tab === 'campaigns' && <CampaignsTab client={client} workbench={workbench} reload={loadCore} setError={setError} />}
      {tab === 'audiences' && <AudiencesTab client={client} setError={setError} />}
      {tab === 'creative' && <CreativeTab client={client} workbench={workbench} role={user.role} setError={setError} />}
      {tab === 'supply' && <SupplyTab client={client} setError={setError} />}
      {tab === 'bidder' && <BidderTab client={client} workbench={workbench} reload={loadCore} setError={setError} />}
      {tab === 'measurement' && <MeasurementTab client={client} workbench={workbench} setError={setError} />}
      {tab === 'optimization' && <OptimizationTab client={client} setError={setError} />}
      {tab === 'reporting' && <ReportingTab client={client} setError={setError} />}
      {tab === 'compliance' && <ComplianceTab client={client} setError={setError} />}
      {tab === 'audit' && <AuditTab workbench={workbench} />}
    </main>
  );
}

type Client = ReturnType<typeof createClient>;
type TabProps = { client: Client; setError: (m: string) => void };

// ---------------------------------------------------------------------------
// Overview
// ---------------------------------------------------------------------------
function OverviewTab({ overview, workbench, client }: { overview: Overview | null; workbench: Workbench | null; client: Client }) {
  const [compliance, setCompliance] = useState<Compliance | null>(null);
  const [freq, setFreq] = useState<FrequencyGovernance | null>(null);
  useEffect(() => {
    client.get<Compliance>('/api/full/compliance/scan').then(setCompliance).catch(() => {});
    client.get<FrequencyGovernance>('/api/full/frequency/governance').then(setFreq).catch(() => {});
  }, [client]);

  const k = overview?.kpis || {};
  const cards: { label: string; value: string }[] = [
    { label: 'Active campaigns', value: `${k.active_campaigns ?? 0}/${k.campaigns ?? 0}` },
    { label: 'Line items', value: num(k.line_items ?? 0) },
    { label: 'Total budget', value: money(k.total_budget ?? 0) },
    { label: 'Audiences', value: num(k.audiences ?? 0) },
    { label: 'Addressable HCPs', value: num(k.addressable_hcps ?? 0) },
    { label: 'Creatives approved', value: `${k.creatives_approved ?? 0}/${k.creatives ?? 0}` },
    { label: 'PMP / deals', value: num(k.deals ?? 0) },
    { label: 'Supply paths', value: num(k.supply_paths ?? 0) },
    { label: 'Measurement ready', value: `${k.measurement_ready ?? 0}/${k.measurement_plans ?? 0}` },
    { label: 'Avg working media', value: pct(k.avg_working_media_ratio ?? 0) },
  ];

  return (
    <>
      <section className="dsp-hero">
        <div>
          <p className="eyebrow">One operating view</p>
          <h1>The pharma-native DSP command OS.</h1>
          <p>{overview?.narrative}</p>
        </div>
        <div className="hero-side">
          <div className="big-score">
            <span>Compliance score</span>
            <strong className={compliance && compliance.compliance_score < 80 ? 'warn' : 'ok'}>{compliance?.compliance_score ?? '—'}</strong>
            <small>{compliance?.creatives_blocked_from_serving ?? 0} creatives gated by MLR</small>
          </div>
        </div>
      </section>

      <section className="metric-grid">
        {cards.map((c) => <div className="metric-card" key={c.label}><span>{c.label}</span><strong>{c.value}</strong></div>)}
      </section>

      <div className="dsp-grid two">
        <Panel eyebrow="Frequency governance" title="Cross-channel HCP + DTC coordination" icon={<Gauge />}>
          <p>{freq?.note}</p>
          <div className="kv-row"><span>Recommended global weekly cap</span><strong>{freq?.recommended_global_weekly_cap ?? '—'}</strong></div>
          <div className="kv-row"><span>Uncoordinated cap pressure</span><strong>{freq?.uncoordinated_cap_pressure ?? '—'}</strong></div>
          <div className="table-list">
            {freq?.by_channel.map((c) => (
              <div key={c.channel}>
                <strong>{c.channel}</strong>
                <span>{c.lines} lines · caps {c.min_cap}–{c.max_cap} (avg {c.avg_cap})</span>
                <span>Audiences: {c.audiences.join(', ') || '—'}</span>
              </div>
            ))}
          </div>
        </Panel>
        <Panel eyebrow="Live campaigns" title="Portfolio snapshot" icon={<ClipboardList />}>
          <div className="table-list">
            {workbench?.campaigns.slice(0, 6).map((c) => (
              <div key={c.id}>
                <strong>{c.name}</strong>
                <span>{c.brand} · {c.indication} · {c.audience_type}</span>
                <span>{money(c.budget)} · {c.line_items.length} lines · <Badge tone={c.status === 'active' ? 'ok' : 'muted'}>{c.status}</Badge></span>
              </div>
            ))}
            {!workbench?.campaigns.length && <p>No campaigns yet — build one in the Campaigns tab.</p>}
          </div>
        </Panel>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Campaigns
// ---------------------------------------------------------------------------
function CampaignsTab({ client, workbench, reload, setError }: { client: Client; workbench: Workbench | null; reload: () => void; setError: (m: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [campaignForm, setCampaignForm] = useState({
    name: 'New Pharma Signal Launch', brand: 'TZIELD', indication: 'Type 1 diabetes delay',
    audience_type: 'DTC', objective: 'Quality reach, conversion readiness, and measurable lift',
    budget: 500000, flight_start: '2026-07-01', flight_end: '2026-12-31', status: 'draft',
  });
  const [lineItems, setLineItems] = useState([
    { name: 'Display + Native Outcomes', channel: 'Display', budget: 250000, max_bid_cpm: 24, pacing_mode: 'even', status: 'draft', frequency_cap: 3 },
    { name: 'CTV Reach Extension', channel: 'CTV', budget: 250000, max_bid_cpm: 42, pacing_mode: 'front_loaded', status: 'draft', frequency_cap: 2 },
  ]);
  const [bulkForm, setBulkForm] = useState({ entity_type: 'line_item', ids: '', updates: '{"status":"active"}', reason: 'Launch approved line items', dry_run: true });
  const [bulkResult, setBulkResult] = useState<unknown>(null);

  async function buildCampaign(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await client.post('/api/full/campaign-build', { campaign: campaignForm, line_items: lineItems, default_bid_factors: starterBidFactors });
      reload();
    } catch (err) { setError(friendlyError(err, 'Campaign build failed')); } finally { setBusy(false); }
  }

  async function bulkEdit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const result = await client.post('/api/full/bulk-edit', {
        entity_type: bulkForm.entity_type,
        ids: bulkForm.ids.split(',').map((id) => id.trim()).filter(Boolean),
        updates: JSON.parse(bulkForm.updates), reason: bulkForm.reason, dry_run: bulkForm.dry_run,
      });
      setBulkResult(result);
      if (!bulkForm.dry_run) reload();
    } catch (err) { setError(friendlyError(err, 'Bulk edit failed')); } finally { setBusy(false); }
  }

  return (
    <>
      <div className="dsp-grid two">
        <form className="dsp-panel" onSubmit={buildCampaign}>
          <div className="panel-title"><div><p className="eyebrow">Campaign builder</p><h2>Build campaign + line items</h2></div><PencilRuler /></div>
          <div className="form-grid two-col">
            {Object.entries(campaignForm).map(([key, value]) => (
              <label key={key}>{key.replaceAll('_', ' ')}<input value={value} type={typeof value === 'number' ? 'number' : 'text'} onChange={(e) => setCampaignForm({ ...campaignForm, [key]: typeof value === 'number' ? Number(e.target.value) : e.target.value })} /></label>
            ))}
          </div>
          <h3>Line items</h3>
          {lineItems.map((line, index) => (
            <div className="line-editor" key={index}>
              <input value={line.name} onChange={(e) => setLineItems(lineItems.map((it, i) => i === index ? { ...it, name: e.target.value } : it))} />
              <input value={line.channel} onChange={(e) => setLineItems(lineItems.map((it, i) => i === index ? { ...it, channel: e.target.value } : it))} />
              <input type="number" value={line.budget} onChange={(e) => setLineItems(lineItems.map((it, i) => i === index ? { ...it, budget: Number(e.target.value) } : it))} />
              <input type="number" value={line.max_bid_cpm} onChange={(e) => setLineItems(lineItems.map((it, i) => i === index ? { ...it, max_bid_cpm: Number(e.target.value) } : it))} />
            </div>
          ))}
          <button type="button" className="secondary-button" onClick={() => setLineItems([...lineItems, { name: 'New Line Item', channel: 'Display', budget: 100000, max_bid_cpm: 20, pacing_mode: 'even', status: 'draft', frequency_cap: 3 }])}>Add line item</button>
          <button className="primary-button" disabled={busy}>Create campaign</button>
        </form>

        <form className="dsp-panel" onSubmit={bulkEdit}>
          <div className="panel-title"><div><p className="eyebrow">Bulk editor</p><h2>Edit campaigns, lines, or bid factors</h2></div><SlidersHorizontal /></div>
          <label>Entity<select value={bulkForm.entity_type} onChange={(e) => setBulkForm({ ...bulkForm, entity_type: e.target.value })}><option value="campaign">Campaign</option><option value="line_item">Line item</option><option value="bid_factor">Bid factor</option></select></label>
          <label>IDs comma separated<textarea value={bulkForm.ids} onChange={(e) => setBulkForm({ ...bulkForm, ids: e.target.value })} placeholder="Paste IDs from the table below" /></label>
          <label>Updates JSON<textarea value={bulkForm.updates} onChange={(e) => setBulkForm({ ...bulkForm, updates: e.target.value })} /></label>
          <label>Reason<input value={bulkForm.reason} onChange={(e) => setBulkForm({ ...bulkForm, reason: e.target.value })} /></label>
          <label className="check-row"><input type="checkbox" checked={bulkForm.dry_run} onChange={(e) => setBulkForm({ ...bulkForm, dry_run: e.target.checked })} /> Dry run first</label>
          <button className="primary-button" disabled={busy}>Run bulk edit</button>
          {bulkResult ? <pre className="result-box">{JSON.stringify(bulkResult, null, 2)}</pre> : null}
        </form>
      </div>

      <Panel eyebrow="Campaigns" title="Live campaign table" icon={<ClipboardList />}>
        <div className="campaign-table">
          {workbench?.campaigns.map((c) => (
            <article key={c.id}>
              <header><strong>{c.name}</strong><Badge tone={c.status === 'active' ? 'ok' : 'muted'}>{c.status}</Badge></header>
              <p>{c.brand} · {c.indication} · {c.audience_type} · {money(c.budget)}</p>
              <code>{c.id}</code>
              <div className="nested-lines">
                {c.line_items.map((line) => (
                  <div key={line.id}><strong>{line.name}</strong><span>{line.channel} · {money(line.budget)} · max {money2(line.max_bid_cpm)} CPM · cap {line.frequency_cap}</span><code>{line.id}</code></div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </Panel>
    </>
  );
}

// ---------------------------------------------------------------------------
// Audiences
// ---------------------------------------------------------------------------
function AudiencesTab({ client, setError }: TabProps) {
  const [audiences, setAudiences] = useState<Audience[]>([]);
  const [busy, setBusy] = useState(false);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [form, setForm] = useState({ audience_id: '', budget: 250000, cpm: 18, frequency_cap: 3, flight_days: 30 });
  const [newAud, setNewAud] = useState({ name: 'Cardiology HCP - High Decile', audience_type: 'HCP', description: 'NPI-verified cardiologists, decile 7-10', npi_count: 52000, reach: 52000, match_rate: 0.89, data_cpm: 11, refresh_cadence: 'weekly', contains_phi: false, status: 'active' });

  const load = useCallback(() => { client.get<Audience[]>('/api/full/audiences').then((a) => { setAudiences(a); if (a[0] && !form.audience_id) setForm((f) => ({ ...f, audience_id: a[0].id })); }).catch((e) => setError(friendlyError(e, 'Load audiences failed'))); }, [client, setError, form.audience_id]);
  useEffect(() => { load(); }, [load]);

  async function runForecast(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try { setForecast(await client.post<Forecast>('/api/full/audiences/forecast', form)); } catch (e) { setError(friendlyError(e, 'Forecast failed')); } finally { setBusy(false); }
  }
  async function createAudience(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try { await client.post('/api/full/audiences', newAud); load(); } catch (e) { setError(friendlyError(e, 'Create audience failed')); } finally { setBusy(false); }
  }

  return (
    <>
      <Panel eyebrow="Audience library" title="HCP, DTC, lookalike & contextual" icon={<Users />}>
        <div className="data-table">
          <div className="data-head audience-cols"><span>Audience</span><span>Type</span><span>NPIs</span><span>Reach</span><span>Match</span><span>Data CPM</span><span>PHI</span></div>
          {audiences.map((a) => (
            <div className="data-row audience-cols" key={a.id}>
              <div><strong>{a.name}</strong><small>{a.description}</small></div>
              <span><Badge tone="accent">{a.audience_type}</Badge></span>
              <span>{a.npi_count ? num(a.npi_count) : '—'}</span>
              <span>{num(a.reach)}</span>
              <span>{a.match_rate ? pct(a.match_rate) : '—'}</span>
              <span>{a.data_cpm ? money2(a.data_cpm) : 'Free'}</span>
              <span>{a.contains_phi ? <Badge tone="danger">PHI</Badge> : <Badge tone="ok">No PHI</Badge>}</span>
            </div>
          ))}
        </div>
      </Panel>

      <div className="dsp-grid two">
        <form className="dsp-panel" onSubmit={runForecast}>
          <div className="panel-title"><div><p className="eyebrow">Reach & frequency</p><h2>Forecast planner</h2></div><Target /></div>
          <label>Audience<select value={form.audience_id} onChange={(e) => setForm({ ...form, audience_id: e.target.value })}>{audiences.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label>
          <div className="form-grid two-col">
            <label>Budget<input type="number" value={form.budget} onChange={(e) => setForm({ ...form, budget: Number(e.target.value) })} /></label>
            <label>CPM<input type="number" value={form.cpm} onChange={(e) => setForm({ ...form, cpm: Number(e.target.value) })} /></label>
            <label>Frequency cap<input type="number" value={form.frequency_cap} onChange={(e) => setForm({ ...form, frequency_cap: Number(e.target.value) })} /></label>
            <label>Flight days<input type="number" value={form.flight_days} onChange={(e) => setForm({ ...form, flight_days: Number(e.target.value) })} /></label>
          </div>
          <button className="primary-button" disabled={busy || !form.audience_id}><Zap size={16} /> Run forecast</button>
          {forecast && (
            <div className="result-grid">
              <div className="metric-card"><span>Impressions</span><strong>{num(forecast.impressions)}</strong></div>
              <div className="metric-card"><span>Unique reach</span><strong>{num(forecast.unique_reach)}</strong></div>
              <div className="metric-card"><span>% of audience</span><strong>{pct1(forecast.pct_of_audience_reached)}</strong></div>
              <div className="metric-card"><span>Achieved freq</span><strong>{forecast.achieved_frequency}x</strong></div>
              <div className="metric-card"><span>Working media</span><strong>{pct(forecast.working_media_ratio)}</strong></div>
              <div className="metric-card"><span>Data spend</span><strong>{money(forecast.data_spend)}</strong></div>
              <div className="metric-card"><span>Effective CPM</span><strong>{money2(forecast.effective_cpm)}</strong></div>
              <div className="metric-card"><span>Daily impressions</span><strong>{num(forecast.daily_impressions)}</strong></div>
            </div>
          )}
        </form>

        <form className="dsp-panel" onSubmit={createAudience}>
          <div className="panel-title"><div><p className="eyebrow">Onboard audience</p><h2>Add to library (no PHI)</h2></div><Users /></div>
          <div className="form-grid two-col">
            <label>Name<input value={newAud.name} onChange={(e) => setNewAud({ ...newAud, name: e.target.value })} /></label>
            <label>Type<select value={newAud.audience_type} onChange={(e) => setNewAud({ ...newAud, audience_type: e.target.value })}>{['HCP', 'DTC', 'Lookalike', 'Contextual', 'Retargeting'].map((t) => <option key={t}>{t}</option>)}</select></label>
            <label>NPI count<input type="number" value={newAud.npi_count} onChange={(e) => setNewAud({ ...newAud, npi_count: Number(e.target.value) })} /></label>
            <label>Reach<input type="number" value={newAud.reach} onChange={(e) => setNewAud({ ...newAud, reach: Number(e.target.value) })} /></label>
            <label>Match rate<input type="number" step="0.01" value={newAud.match_rate} onChange={(e) => setNewAud({ ...newAud, match_rate: Number(e.target.value) })} /></label>
            <label>Data CPM<input type="number" step="0.5" value={newAud.data_cpm} onChange={(e) => setNewAud({ ...newAud, data_cpm: Number(e.target.value) })} /></label>
          </div>
          <label>Description<textarea value={newAud.description} onChange={(e) => setNewAud({ ...newAud, description: e.target.value })} /></label>
          <button className="primary-button" disabled={busy}>Onboard audience</button>
          <small>Audiences flagged as containing PHI are rejected at onboarding — a hard pharma guardrail.</small>
        </form>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Creative & MLR
// ---------------------------------------------------------------------------
function CreativeTab({ client, workbench, role, setError }: { client: Client; workbench: Workbench | null; role: string; setError: (m: string) => void }) {
  const [creatives, setCreatives] = useState<Creative[]>([]);
  const [busy, setBusy] = useState(false);
  const campaigns = workbench?.campaigns || [];
  const [form, setForm] = useState({ campaign_id: '', name: 'Hero Banner 300x250', fmt: 'Display 300x250', channel: 'Display', claims: 'Helps delay onset in at-risk patients', isi_included: true, landing_url: 'https://brand.example/hcp' });
  const [notes, setNotes] = useState<Record<string, string>>({});

  const load = useCallback(() => client.get<Creative[]>('/api/full/creatives').then(setCreatives).catch((e) => setError(friendlyError(e, 'Load creatives failed'))), [client, setError]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (campaigns[0] && !form.campaign_id) setForm((f) => ({ ...f, campaign_id: campaigns[0].id })); }, [campaigns, form.campaign_id]);

  async function submitCreative(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try { await client.post('/api/full/creatives', form); load(); } catch (e) { setError(friendlyError(e, 'Submit creative failed')); } finally { setBusy(false); }
  }
  async function review(id: string, decision: string) {
    setBusy(true);
    try { await client.post(`/api/full/creatives/${id}/review`, { decision, notes: notes[id] || '' }); load(); } catch (e) { setError(friendlyError(e, 'Review failed')); } finally { setBusy(false); }
  }

  const canReview = role === 'admin' || role === 'analyst';

  return (
    <>
      <form className="dsp-panel" onSubmit={submitCreative}>
        <div className="panel-title"><div><p className="eyebrow">Creative intake</p><h2>Submit creative for MLR review</h2></div><BadgeCheck /></div>
        <div className="form-grid two-col">
          <label>Campaign<select value={form.campaign_id} onChange={(e) => setForm({ ...form, campaign_id: e.target.value })}>{campaigns.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
          <label>Name<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
          <label>Format<input value={form.fmt} onChange={(e) => setForm({ ...form, fmt: e.target.value })} /></label>
          <label>Channel<input value={form.channel} onChange={(e) => setForm({ ...form, channel: e.target.value })} /></label>
          <label>Landing URL<input value={form.landing_url} onChange={(e) => setForm({ ...form, landing_url: e.target.value })} /></label>
          <label className="check-row"><input type="checkbox" checked={form.isi_included} onChange={(e) => setForm({ ...form, isi_included: e.target.checked })} /> ISI included</label>
        </div>
        <label>Claims<textarea value={form.claims} onChange={(e) => setForm({ ...form, claims: e.target.value })} /></label>
        <button className="primary-button" disabled={busy || !form.campaign_id}>Submit for review</button>
      </form>

      <Panel eyebrow="MLR queue" title="Medical-Legal-Regulatory review" icon={<ShieldCheck />}>
        <div className="data-table">
          {creatives.map((c) => (
            <div className="creative-row" key={c.id}>
              <div className="creative-main">
                <strong>{c.name}</strong>
                <small>{c.fmt} · {c.channel} · v{c.version} {c.isi_included ? '' : '· ⚠ no ISI'}</small>
                <small>{c.claims}</small>
                {c.review_notes ? <small>Reviewer note: {c.review_notes}</small> : null}
              </div>
              <div className="creative-status">
                <Badge tone={c.mlr_status === 'approved' ? 'ok' : c.mlr_status === 'rejected' ? 'danger' : 'warn'}>{c.mlr_status.replaceAll('_', ' ')}</Badge>
                {c.reviewer ? <small>{c.reviewer}</small> : null}
              </div>
              {canReview && c.mlr_status !== 'approved' && (
                <div className="creative-actions">
                  <input placeholder="Review note" value={notes[c.id] || ''} onChange={(e) => setNotes({ ...notes, [c.id]: e.target.value })} />
                  <button type="button" className="mini ok" disabled={busy} onClick={() => review(c.id, 'approved')}>Approve</button>
                  <button type="button" className="mini warn" disabled={busy} onClick={() => review(c.id, 'changes_requested')}>Changes</button>
                  <button type="button" className="mini danger" disabled={busy} onClick={() => review(c.id, 'rejected')}>Reject</button>
                </div>
              )}
            </div>
          ))}
          {!creatives.length && <p>No creatives submitted yet.</p>}
        </div>
        {!canReview && <small>Sign in as admin or analyst to action MLR decisions.</small>}
      </Panel>
    </>
  );
}

// ---------------------------------------------------------------------------
// Supply & Deals
// ---------------------------------------------------------------------------
function SupplyTab({ client, setError }: TabProps) {
  const [ranked, setRanked] = useState<RankedSupply[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [busy, setBusy] = useState(false);
  const [newDeal, setNewDeal] = useState({ partner: 'PubMatic', deal_id: 'PM-PMP-NEW-01', deal_type: 'PMP', channel: 'Display', floor_cpm: 8, audience_match: 0.8, status: 'active' });

  const load = useCallback(() => {
    client.get<SupplyOptimize>('/api/full/supply-paths/optimize').then((s) => setRanked(s.supply_paths)).catch((e) => setError(friendlyError(e, 'Load supply failed')));
    client.get<Deal[]>('/api/full/deals').then(setDeals).catch(() => {});
  }, [client, setError]);
  useEffect(() => { load(); }, [load]);

  async function createDeal(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try { await client.post('/api/full/deals', newDeal); load(); } catch (e) { setError(friendlyError(e, 'Create deal failed')); } finally { setBusy(false); }
  }

  const recTone = (r: string) => (r === 'prioritize' ? 'ok' : r === 'reduce' ? 'danger' : r === 'hold_review' ? 'warn' : 'accent');

  return (
    <>
      <Panel eyebrow="Supply path optimization" title="Ranked SSP / endemic supply" icon={<Boxes />}>
        <div className="data-table">
          <div className="data-head supply-cols"><span>Partner</span><span>Channel</span><span>SPO score</span><span>Floor</span><span>View</span><span>Fraud</span><span>Working</span><span>Action</span></div>
          {ranked.map((s) => (
            <div className="data-row supply-cols" key={s.id}>
              <div><strong>{s.partner}</strong><small>{s.deal_id} · {s.seller_type}</small></div>
              <span>{s.channel}</span>
              <span><strong className="score">{s.spo_score}</strong></span>
              <span>{money2(s.bid_floor_cpm)}</span>
              <span>{Math.round(s.viewability)}%</span>
              <span>{s.fraud_risk}%</span>
              <span>{pct(s.working_media_ratio)}</span>
              <span><Badge tone={recTone(s.recommendation)}>{s.recommendation.replaceAll('_', ' ')}</Badge></span>
            </div>
          ))}
        </div>
      </Panel>

      <div className="dsp-grid two">
        <Panel eyebrow="Deal marketplace" title="PMP / PG / curated deals" icon={<Boxes />}>
          <div className="table-list">
            {deals.map((d) => (
              <div key={d.id}>
                <strong>{d.partner} · {d.deal_type}</strong>
                <span>{d.channel} · {money2(d.floor_cpm)} floor · {pct(d.audience_match)} audience match</span>
                <code>{d.deal_id}</code>
              </div>
            ))}
          </div>
        </Panel>
        <form className="dsp-panel" onSubmit={createDeal}>
          <div className="panel-title"><div><p className="eyebrow">Activate deal</p><h2>Add private marketplace deal</h2></div><Boxes /></div>
          <div className="form-grid two-col">
            <label>Partner<input value={newDeal.partner} onChange={(e) => setNewDeal({ ...newDeal, partner: e.target.value })} /></label>
            <label>Deal ID<input value={newDeal.deal_id} onChange={(e) => setNewDeal({ ...newDeal, deal_id: e.target.value })} /></label>
            <label>Type<select value={newDeal.deal_type} onChange={(e) => setNewDeal({ ...newDeal, deal_type: e.target.value })}>{['PMP', 'PG', 'Auction Package', 'Curated'].map((t) => <option key={t}>{t}</option>)}</select></label>
            <label>Channel<input value={newDeal.channel} onChange={(e) => setNewDeal({ ...newDeal, channel: e.target.value })} /></label>
            <label>Floor CPM<input type="number" step="0.5" value={newDeal.floor_cpm} onChange={(e) => setNewDeal({ ...newDeal, floor_cpm: Number(e.target.value) })} /></label>
            <label>Audience match<input type="number" step="0.01" value={newDeal.audience_match} onChange={(e) => setNewDeal({ ...newDeal, audience_match: Number(e.target.value) })} /></label>
          </div>
          <button className="primary-button" disabled={busy}>Activate deal</button>
        </form>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Bidder
// ---------------------------------------------------------------------------
function BidderTab({ client, workbench, reload, setError }: { client: Client; workbench: Workbench | null; reload: () => void; setError: (m: string) => void }) {
  const allLines = useMemo(() => (workbench?.campaigns || []).flatMap((c) => c.line_items.map((l) => ({ ...l, campaignName: c.name }))), [workbench]);
  const [selectedLineId, setSelectedLineId] = useState('');
  const [bidFactors, setBidFactors] = useState<BidFactors>(starterBidFactors);
  const [busy, setBusy] = useState(false);
  const [auctionResult, setAuctionResult] = useState<Record<string, unknown> | null>(null);
  const [sim, setSim] = useState<Bidstream | null>(null);
  const [simForm, setSimForm] = useState({ requests: 2000, phi_leak_rate: 0.03 });

  useEffect(() => {
    if (!selectedLineId && allLines[0]) {
      setSelectedLineId(allLines[0].id);
      if (allLines[0].bid_factors) setBidFactors(allLines[0].bid_factors);
    }
  }, [allLines, selectedLineId]);

  async function saveBidFactors(event: FormEvent) {
    event.preventDefault();
    if (!selectedLineId) return;
    setBusy(true);
    try { await client.put(`/api/full/line-items/${selectedLineId}/bid-factors`, bidFactors); reload(); } catch (e) { setError(friendlyError(e, 'Save bid factors failed')); } finally { setBusy(false); }
  }
  async function testAuction() {
    const line = allLines.find((l) => l.id === selectedLineId);
    const supply = workbench?.supply_paths.find((p) => p.status === 'approved');
    if (!line || !supply) return;
    setBusy(true);
    try {
      const result = await client.post<Record<string, unknown>>('/api/full/auction/evaluate', {
        line_item_id: line.id, supply_path_id: supply.id, audience_quality: 86, supply_quality: supply.outcome_score,
        outcome_signal: 78, contextual_relevance: 82, working_media_ratio: supply.working_media_ratio, data_cost_ratio: 0.22,
        frequency_seen_today: 1, floor_cpm: supply.bid_floor_cpm, contains_phi: false, creative_approved: true, geo_allowed: true, consent_ok: true,
      });
      setAuctionResult(result);
    } catch (e) { setError(friendlyError(e, 'Auction failed')); } finally { setBusy(false); }
  }
  async function runSim() {
    if (!selectedLineId) return;
    setBusy(true);
    try { setSim(await client.post<Bidstream>('/api/full/bidstream/simulate', { line_item_id: selectedLineId, requests: simForm.requests, phi_leak_rate: simForm.phi_leak_rate, seed: 42 })); } catch (e) { setError(friendlyError(e, 'Bidstream simulation failed')); } finally { setBusy(false); }
  }

  return (
    <>
      <form className="dsp-panel" onSubmit={saveBidFactors}>
        <div className="panel-title"><div><p className="eyebrow">Bid engine</p><h2>Weighted, outcome-aware bid factors</h2></div><SlidersHorizontal /></div>
        <label>Line item<select value={selectedLineId} onChange={(e) => { setSelectedLineId(e.target.value); const f = allLines.find((l) => l.id === e.target.value); if (f?.bid_factors) setBidFactors(f.bid_factors); }}><option value="">Select line item</option>{allLines.map((l) => <option key={l.id} value={l.id}>{l.campaignName} · {l.name}</option>)}</select></label>
        <div className="form-grid two-col">
          {Object.entries(bidFactors).map(([key, value]) => (
            <label key={key}>{key.replaceAll('_', ' ')}<input type="number" step="0.01" value={value} onChange={(e) => setBidFactors({ ...bidFactors, [key]: Number(e.target.value) } as BidFactors)} /></label>
          ))}
        </div>
        <div className="button-row">
          <button className="primary-button" disabled={busy || !selectedLineId}>Save bid factors</button>
          <button type="button" className="secondary-button" disabled={!selectedLineId || busy} onClick={testAuction}><Zap size={16} /> Test single auction</button>
        </div>
        {auctionResult ? <pre className="result-box">{JSON.stringify(auctionResult, null, 2)}</pre> : null}
      </form>

      <Panel eyebrow="OpenRTB bidstream" title="Simulate live auction traffic" icon={<Radio />}
        actions={<div className="inline-form"><label>Requests<input type="number" value={simForm.requests} onChange={(e) => setSimForm({ ...simForm, requests: Number(e.target.value) })} /></label><label>PHI leak rate<input type="number" step="0.01" value={simForm.phi_leak_rate} onChange={(e) => setSimForm({ ...simForm, phi_leak_rate: Number(e.target.value) })} /></label><button type="button" className="primary-button" disabled={busy || !selectedLineId} onClick={runSim}>Run</button></div>}>
        {sim ? (
          <>
            <div className="metric-grid">
              <div className="metric-card"><span>Bid rate</span><strong>{pct1(sim.bid_rate)}</strong></div>
              <div className="metric-card"><span>Win rate</span><strong>{pct1(sim.win_rate)}</strong></div>
              <div className="metric-card"><span>Impressions won</span><strong>{num(sim.impressions_won)}</strong></div>
              <div className="metric-card"><span>Avg clearing (2nd price)</span><strong>{money2(sim.avg_clearing_cpm)}</strong></div>
              <div className="metric-card"><span>2nd-price CPM</span><strong>{money2(sim.avg_second_price_cpm)}</strong></div>
              <div className="metric-card"><span>Est. spend</span><strong>{money(sim.est_spend)}</strong></div>
              <div className="metric-card"><span>Budget utilization</span><strong>{pct1(sim.budget_utilization)}</strong></div>
              <div className="metric-card"><span>Unique reach</span><strong>{num(sim.unique_reach)}</strong></div>
              <div className="metric-card"><span>Avg frequency</span><strong>{sim.avg_frequency}x</strong></div>
              <div className="metric-card"><span>Frequency capped</span><strong>{num(sim.frequency_capped)}</strong></div>
              <div className="metric-card"><span>Pace throttled</span><strong>{num(sim.pace_throttled)}</strong></div>
              <div className="metric-card"><span>PHI blocked</span><strong className="warn">{num(sim.phi_blocked)}</strong></div>
            </div>
            <div className="decision-bar">
              <span className="seg seg-ok" style={{ flex: sim.decisions.bid || 0.001 }} title={`bid ${sim.decisions.bid}`} />
              <span className="seg seg-warn" style={{ flex: sim.decisions.throttle || 0.001 }} title={`throttle ${sim.decisions.throttle}`} />
              <span className="seg seg-muted" style={{ flex: sim.decisions.no_bid || 0.001 }} title={`no_bid ${sim.decisions.no_bid}`} />
              <span className="seg seg-danger" style={{ flex: sim.decisions.blocked || 0.001 }} title={`blocked ${sim.decisions.blocked}`} />
            </div>
            <p className="legend"><Badge tone="ok">bid {sim.decisions.bid}</Badge> <Badge tone="warn">throttle {sim.decisions.throttle}</Badge> <Badge tone="muted">no-bid {sim.decisions.no_bid}</Badge> <Badge tone="danger">blocked {sim.decisions.blocked}</Badge></p>
            <div className="data-table">
              <div className="data-head partner-cols"><span>Partner</span><span>Requests</span><span>Wins</span><span>Win rate</span><span>Spend</span></div>
              {sim.by_partner.map((p) => (
                <div className="data-row partner-cols" key={p.partner}><strong>{p.partner}</strong><span>{num(p.requests)}</span><span>{num(p.wins)}</span><span>{pct1(p.win_rate)}</span><span>{money(p.est_spend)}</span></div>
              ))}
            </div>
          </>
        ) : <p>Select a line item and run the simulator to see win rate, clearing prices, spend, and PHI guardrail blocks across supply partners.</p>}
      </Panel>
    </>
  );
}

// ---------------------------------------------------------------------------
// Measurement
// ---------------------------------------------------------------------------
function MeasurementTab({ client, workbench, setError }: { client: Client; workbench: Workbench | null; setError: (m: string) => void }) {
  const campaigns = workbench?.campaigns || [];
  const [busy, setBusy] = useState(false);
  const [plans, setPlans] = useState<MeasurementPlan[]>([]);
  const [result, setResult] = useState<MeasurementPlan | null>(null);
  const [form, setForm] = useState({ campaign_id: '', study_type: 'script_lift', baseline_rate: 0.02, expected_lift_pct: 15, exposed_size: 80000, control_size: 80000 });

  const load = useCallback(() => client.get<MeasurementPlan[]>('/api/full/measurement/plans').then(setPlans).catch(() => {}), [client]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (campaigns[0] && !form.campaign_id) setForm((f) => ({ ...f, campaign_id: campaigns[0].id })); }, [campaigns, form.campaign_id]);

  async function plan(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try { const r = await client.post<MeasurementPlan>('/api/full/measurement/plan', form); setResult(r); load(); } catch (e) { setError(friendlyError(e, 'Measurement plan failed')); } finally { setBusy(false); }
  }

  const tone = (r?: string) => (r === 'ready' ? 'ok' : r === 'borderline' ? 'warn' : 'danger');

  return (
    <>
      <form className="dsp-panel" onSubmit={plan}>
        <div className="panel-title"><div><p className="eyebrow">Script-lift planner</p><h2>Measurement power & MDL</h2></div><Target /></div>
        <div className="form-grid two-col">
          <label>Campaign<select value={form.campaign_id} onChange={(e) => setForm({ ...form, campaign_id: e.target.value })}>{campaigns.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
          <label>Study type<select value={form.study_type} onChange={(e) => setForm({ ...form, study_type: e.target.value })}>{['script_lift', 'diagnosis_lift', 'audience_quality', 'brand_lift'].map((t) => <option key={t}>{t}</option>)}</select></label>
          <label>Baseline rate<input type="number" step="0.001" value={form.baseline_rate} onChange={(e) => setForm({ ...form, baseline_rate: Number(e.target.value) })} /></label>
          <label>Expected lift %<input type="number" value={form.expected_lift_pct} onChange={(e) => setForm({ ...form, expected_lift_pct: Number(e.target.value) })} /></label>
          <label>Exposed size<input type="number" value={form.exposed_size} onChange={(e) => setForm({ ...form, exposed_size: Number(e.target.value) })} /></label>
          <label>Control size<input type="number" value={form.control_size} onChange={(e) => setForm({ ...form, control_size: Number(e.target.value) })} /></label>
        </div>
        <button className="primary-button" disabled={busy || !form.campaign_id}><Zap size={16} /> Compute power</button>
        {result && (
          <div className="result-grid">
            <div className="metric-card"><span>Statistical power</span><strong className={result.power >= 0.8 ? 'ok' : 'warn'}>{pct(result.power)}</strong></div>
            <div className="metric-card"><span>Min detectable lift</span><strong>{result.minimum_detectable_lift_pct}%</strong></div>
            <div className="metric-card"><span>Readiness</span><strong><Badge tone={tone(result.readiness)}>{result.readiness}</Badge></strong></div>
            <div className="metric-card"><span>Exp. exposed conv.</span><strong>{num(result.expected_exposed_conversions || 0)}</strong></div>
            <div className="metric-card"><span>Exp. control conv.</span><strong>{num(result.expected_control_conversions || 0)}</strong></div>
          </div>
        )}
        {result?.interpretation && <p className="interpretation">{result.interpretation}</p>}
      </form>

      <Panel eyebrow="Measurement plans" title="Saved study designs" icon={<Target />}>
        <div className="data-table">
          <div className="data-head plan-cols"><span>Study</span><span>Baseline</span><span>Lift</span><span>Exposed</span><span>Control</span><span>Power</span><span>MDL</span><span>Status</span></div>
          {plans.map((p) => (
            <div className="data-row plan-cols" key={p.id}>
              <span>{p.study_type.replaceAll('_', ' ')}</span>
              <span>{pct1(p.baseline_rate)}</span>
              <span>{p.expected_lift_pct}%</span>
              <span>{num(p.exposed_size)}</span>
              <span>{num(p.control_size)}</span>
              <span>{pct(p.power)}</span>
              <span>{p.mdl ?? p.minimum_detectable_lift_pct}%</span>
              <span><Badge tone={tone(p.status || p.readiness)}>{p.status || p.readiness}</Badge></span>
            </div>
          ))}
          {!plans.length && <p>No measurement plans yet.</p>}
        </div>
      </Panel>
    </>
  );
}

// ---------------------------------------------------------------------------
// Optimization
// ---------------------------------------------------------------------------
function OptimizationTab({ client, setError }: TabProps) {
  const [opt, setOpt] = useState<Optimizer | null>(null);
  const load = useCallback(() => client.get<Optimizer>('/api/full/optimizer/portfolio').then(setOpt).catch((e) => setError(friendlyError(e, 'Optimizer failed'))), [client, setError]);
  useEffect(() => { load(); }, [load]);

  return (
    <Panel eyebrow="Portfolio optimizer" title="Budget reallocation recommendations" icon={<TrendingUp />}
      actions={<button className="secondary-button" onClick={load}><RefreshCw size={16} /> Re-run</button>}>
      <div className="metric-grid">
        <div className="metric-card"><span>Total budget</span><strong>{money(opt?.total_budget || 0)}</strong></div>
        <div className="metric-card"><span>Recommended reallocation</span><strong>{money(opt?.reallocated || 0)}</strong></div>
        <div className="metric-card"><span>Avg efficiency</span><strong>{opt?.avg_efficiency ?? '—'}</strong></div>
        <div className="metric-card"><span>Line items</span><strong>{opt?.recommendations.length ?? 0}</strong></div>
      </div>
      <div className="data-table">
        <div className="data-head opt-cols"><span>Line item</span><span>Campaign</span><span>Channel</span><span>Current</span><span>Recommended</span><span>Δ</span><span>Action</span></div>
        {opt?.recommendations.map((r) => (
          <div className={`data-row opt-cols opt-${r.action}`} key={r.line_item_id}>
            <strong>{r.name}</strong>
            <span>{r.campaign}</span>
            <span>{r.channel}</span>
            <span>{money(r.current_budget)}</span>
            <span>{money(r.recommended_budget)}</span>
            <span className={r.delta_pct >= 0 ? 'pos' : 'neg'}>{r.delta_pct > 0 ? '+' : ''}{r.delta_pct}%</span>
            <span><Badge tone={r.action === 'increase' ? 'ok' : r.action === 'decrease' ? 'danger' : 'muted'}>{r.action}</Badge></span>
          </div>
        ))}
        {!opt?.recommendations.length && <p>No line items to optimize yet — build a campaign first.</p>}
      </div>
    </Panel>
  );
}

// ---------------------------------------------------------------------------
// Reporting
// ---------------------------------------------------------------------------
function ReportingTab({ client, setError }: TabProps) {
  const [report, setReport] = useState<Reporting | null>(null);
  const [days, setDays] = useState(14);
  const load = useCallback((d: number) => client.get<Reporting>(`/api/full/reporting/performance?days=${d}`).then(setReport).catch((e) => setError(friendlyError(e, 'Reporting failed'))), [client, setError]);
  useEffect(() => { load(days); }, [load, days]);

  const p = report?.portfolio;
  return (
    <>
      <Panel eyebrow="Delivery & outcomes" title="Portfolio performance" icon={<Gauge />}
        actions={<label className="inline-label">Window<select value={days} onChange={(e) => setDays(Number(e.target.value))}>{[7, 14, 30, 60, 90].map((d) => <option key={d} value={d}>{d}d</option>)}</select></label>}>
        <div className="metric-grid">
          <div className="metric-card"><span>Spend</span><strong>{money(p?.spend || 0)}</strong></div>
          <div className="metric-card"><span>Impressions</span><strong>{num(p?.impressions || 0)}</strong></div>
          <div className="metric-card"><span>Clicks</span><strong>{num(p?.clicks || 0)}</strong></div>
          <div className="metric-card"><span>Conversions</span><strong>{num(p?.conversions || 0)}</strong></div>
          <div className="metric-card"><span>CTR</span><strong>{pct1(p?.ctr || 0)}</strong></div>
          <div className="metric-card"><span>CPA</span><strong>{money2(p?.cpa || 0)}</strong></div>
        </div>
      </Panel>

      {report?.campaigns.map((c) => {
        const maxSpend = Math.max(...c.series.map((s) => s.spend), 1);
        return (
          <Panel key={c.campaign_id} eyebrow={c.brand} title={c.name} icon={<Badge tone={c.pacing_status === 'on_pace' ? 'ok' : 'warn'}>{c.pacing_status.replaceAll('_', ' ')}</Badge>}>
            <div className="metric-grid">
              <div className="metric-card"><span>Spend / budget</span><strong>{money(c.spend)} / {money(c.budget)}</strong></div>
              <div className="metric-card"><span>Pacing</span><strong>{pct(c.pacing)}</strong></div>
              <div className="metric-card"><span>Impressions</span><strong>{num(c.impressions)}</strong></div>
              <div className="metric-card"><span>Conversions</span><strong>{num(c.conversions)}</strong></div>
              <div className="metric-card"><span>CTR</span><strong>{pct1(c.ctr)}</strong></div>
              <div className="metric-card"><span>eCPM / CPA</span><strong>{money2(c.ecpm)} / {money2(c.cpa)}</strong></div>
            </div>
            <div className="spark">
              {c.series.map((s) => <span key={s.date} className="spark-bar" style={{ height: `${Math.max(4, (s.spend / maxSpend) * 100)}%` }} title={`${s.date}: ${money(s.spend)} · ${num(s.conversions)} conv`} />)}
            </div>
          </Panel>
        );
      })}
    </>
  );
}

// ---------------------------------------------------------------------------
// Compliance
// ---------------------------------------------------------------------------
function ComplianceTab({ client, setError }: TabProps) {
  const [scan, setScan] = useState<Compliance | null>(null);
  const [freq, setFreq] = useState<FrequencyGovernance | null>(null);
  const load = useCallback(() => {
    client.get<Compliance>('/api/full/compliance/scan').then(setScan).catch((e) => setError(friendlyError(e, 'Compliance scan failed')));
    client.get<FrequencyGovernance>('/api/full/frequency/governance').then(setFreq).catch(() => {});
  }, [client, setError]);
  useEffect(() => { load(); }, [load]);

  const sevTone = (s: string) => (s === 'critical' ? 'danger' : s === 'high' ? 'danger' : s === 'medium' ? 'warn' : 'muted');

  return (
    <>
      <section className="dsp-hero compact-heading">
        <div>
          <p className="eyebrow">Pharma guardrails</p>
          <h1>Compliance & governance</h1>
          <p>No-PHI enforcement, consent at auction, MLR gating, ISI checks, brand safety, and cross-channel frequency coordination — the pharma-native controls generic DSPs leave to spreadsheets.</p>
        </div>
        <div className="hero-side">
          <div className="big-score"><span>Compliance score</span><strong className={scan && scan.compliance_score < 80 ? 'warn' : 'ok'}>{scan?.compliance_score ?? '—'}</strong><small>scanned {scan ? new Date(scan.scanned_at).toLocaleString() : '—'}</small></div>
        </div>
      </section>

      <div className="dsp-grid two">
        <Panel eyebrow="Control checks" title="Hard guardrails" icon={<ShieldCheck />} actions={<button className="secondary-button" onClick={load}><RefreshCw size={16} /> Re-scan</button>}>
          <div className="table-list">
            {Object.entries(scan?.checks || {}).map(([k, v]) => (
              <div key={k} className="kv-row"><span>{k.replaceAll('_', ' ')}</span><strong>{v ? <Badge tone="ok">pass</Badge> : <Badge tone="danger">fail</Badge>}</strong></div>
            ))}
            <div className="kv-row"><span>creatives blocked from serving</span><strong>{scan?.creatives_blocked_from_serving ?? 0}</strong></div>
          </div>
        </Panel>
        <Panel eyebrow="Frequency governance" title="Coordinated cap" icon={<Gauge />}>
          <div className="kv-row"><span>Recommended global weekly cap</span><strong>{freq?.recommended_global_weekly_cap ?? '—'}</strong></div>
          <div className="kv-row"><span>Channels over recommended</span><strong>{freq?.channels_over_recommended.join(', ') || 'none'}</strong></div>
          <div className="table-list">
            {freq?.by_channel.map((c) => <div key={c.channel}><strong>{c.channel}</strong><span>caps {c.min_cap}–{c.max_cap} (avg {c.avg_cap}) · {c.lines} lines</span></div>)}
          </div>
        </Panel>
      </div>

      <Panel eyebrow="Findings" title="Open compliance findings" icon={<ShieldCheck />}>
        <div className="table-list">
          {scan?.findings.map((f, i) => (
            <div key={i} className="kv-row"><span><Badge tone={sevTone(f.severity)}>{f.severity}</Badge> {f.area} · <strong>{f.entity}</strong></span><span>{f.issue}</span></div>
          ))}
          {!scan?.findings.length && <p>No open findings — all controls passing.</p>}
        </div>
      </Panel>
    </>
  );
}

// ---------------------------------------------------------------------------
// Audit
// ---------------------------------------------------------------------------
function AuditTab({ workbench }: { workbench: Workbench | null }) {
  return (
    <Panel eyebrow="Audit" title="Every login, build, edit, review, and auction is logged" icon={<ClipboardList />}>
      <div className="audit-list">
        {workbench?.audit.map((row) => (
          <div key={row.id}><strong>{row.action}</strong><span>{row.actor}</span><span>{row.entity_type}:{row.entity_id}</span><small>{row.ts}</small></div>
        ))}
        {!workbench?.audit.length && <p>No audit events yet.</p>}
      </div>
    </Panel>
  );
}
