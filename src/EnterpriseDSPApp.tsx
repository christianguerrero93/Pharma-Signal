import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Activity, BadgeCheck, Boxes, ClipboardList, Layers3, Lock, PencilRuler, RefreshCw, SlidersHorizontal, UploadCloud, Zap } from 'lucide-react';

type User = { id: string; email: string; name: string; role: string };
type SupplyPath = { id: string; partner: string; channel: string; deal_id: string; status: string; bid_floor_cpm: number; outcome_score: number; working_media_ratio: number };
type BidFactors = {
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
type LineItem = { id: string; campaign_id: string; name: string; channel: string; budget: number; max_bid_cpm: number; pacing_mode: string; status: string; frequency_cap: number; bid_factors?: BidFactors & { line_item_id: string } };
type Campaign = { id: string; name: string; brand: string; indication: string; audience_type: string; objective: string; budget: number; status: string; flight_start: string; flight_end: string; line_items: LineItem[] };
type Workbench = { user: User; campaigns: Campaign[]; supply_paths: SupplyPath[]; audit: Array<Record<string, string>>; summary: { campaigns: number; line_items: number; total_budget: number; active_campaigns: number } };

const API_BASE = import.meta.env.VITE_FULL_DSP_API_URL || 'http://localhost:8090';
const defaultPassword = import.meta.env.VITE_FULL_DSP_DEV_PASSWORD || 'pharma-signal-local';

const starterBidFactors: BidFactors = {
  audience_quality_weight: 0.28,
  supply_quality_weight: 0.22,
  outcome_signal_weight: 0.24,
  contextual_relevance_weight: 0.12,
  working_media_weight: 0.1,
  frequency_penalty_weight: 0.04,
  bid_shading_pct: 0.12,
  max_bid_multiplier: 2.5,
  data_cost_guardrail: 0.35,
};

function money(value: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value || 0);
}

function pct(value: number) {
  return `${Math.round(value * 100)}%`;
}

export default function EnterpriseDSPApp() {
  const [token, setToken] = useState(localStorage.getItem('pharma_signal_full_token') || '');
  const [user, setUser] = useState<User | null>(null);
  const [workbench, setWorkbench] = useState<Workbench | null>(null);
  const [email, setEmail] = useState('admin@pharmasignal.local');
  const [password, setPassword] = useState(defaultPassword);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [campaignForm, setCampaignForm] = useState({
    name: 'New Pharma Signal Launch',
    brand: 'TZIELD',
    indication: 'Type 1 diabetes delay',
    audience_type: 'DTC',
    objective: 'Quality reach, conversion readiness, and measurable lift',
    budget: 500000,
    flight_start: '2026-07-01',
    flight_end: '2026-12-31',
    status: 'draft',
  });
  const [lineItems, setLineItems] = useState([
    { name: 'Display + Native Outcomes', channel: 'Display', budget: 250000, max_bid_cpm: 24, pacing_mode: 'even', status: 'draft', frequency_cap: 3 },
    { name: 'CTV Reach Extension', channel: 'CTV', budget: 250000, max_bid_cpm: 42, pacing_mode: 'front_loaded', status: 'draft', frequency_cap: 2 },
  ]);
  const [selectedLineId, setSelectedLineId] = useState('');
  const [bidFactors, setBidFactors] = useState<BidFactors>(starterBidFactors);
  const [bulkForm, setBulkForm] = useState({ entity_type: 'line_item', ids: '', updates: '{"status":"active"}', reason: 'Launch approved line items', dry_run: true });
  const [auctionResult, setAuctionResult] = useState<Record<string, unknown> | null>(null);

  async function api<T>(path: string, init: RequestInit = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...(init.headers || {}),
      },
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json() as Promise<T>;
  }

  async function loadWorkbench() {
    if (!token) return;
    setBusy(true);
    try {
      const data = await api<Workbench>('/api/full/workbench');
      setWorkbench(data);
      setUser(data.user);
      const firstLine = data.campaigns.flatMap((campaign) => campaign.line_items)[0];
      if (firstLine && !selectedLineId) {
        setSelectedLineId(firstLine.id);
        if (firstLine.bid_factors) setBidFactors(firstLine.bid_factors);
      }
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load DSP workbench');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadWorkbench();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function login(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE}/api/full/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) throw new Error(await response.text());
      const data = await response.json();
      localStorage.setItem('pharma_signal_full_token', data.access_token);
      setToken(data.access_token);
      setUser(data.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setBusy(false);
    }
  }

  async function buildCampaign(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api('/api/full/campaign-build', {
        method: 'POST',
        body: JSON.stringify({ campaign: campaignForm, line_items: lineItems, default_bid_factors: bidFactors }),
      });
      await loadWorkbench();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Campaign build failed');
    } finally {
      setBusy(false);
    }
  }

  async function saveBidFactors(event: FormEvent) {
    event.preventDefault();
    if (!selectedLineId) return;
    setBusy(true);
    try {
      await api(`/api/full/line-items/${selectedLineId}/bid-factors`, { method: 'PUT', body: JSON.stringify(bidFactors) });
      await loadWorkbench();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bid factor update failed');
    } finally {
      setBusy(false);
    }
  }

  async function bulkEdit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api('/api/full/bulk-edit', {
        method: 'POST',
        body: JSON.stringify({
          entity_type: bulkForm.entity_type,
          ids: bulkForm.ids.split(',').map((id) => id.trim()).filter(Boolean),
          updates: JSON.parse(bulkForm.updates),
          reason: bulkForm.reason,
          dry_run: bulkForm.dry_run,
        }),
      });
      await loadWorkbench();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk edit failed');
    } finally {
      setBusy(false);
    }
  }

  async function evaluateAuction() {
    const line = workbench?.campaigns.flatMap((campaign) => campaign.line_items).find((item) => item.id === selectedLineId);
    const supply = workbench?.supply_paths.find((path) => path.status === 'approved');
    if (!line || !supply) return;
    setBusy(true);
    try {
      const result = await api<Record<string, unknown>>('/api/full/auction/evaluate', {
        method: 'POST',
        body: JSON.stringify({
          line_item_id: line.id,
          supply_path_id: supply.id,
          audience_quality: 86,
          supply_quality: supply.outcome_score,
          outcome_signal: 78,
          contextual_relevance: 82,
          working_media_ratio: supply.working_media_ratio,
          data_cost_ratio: 0.22,
          frequency_seen_today: 1,
          floor_cpm: supply.bid_floor_cpm,
          contains_phi: false,
          creative_approved: true,
          geo_allowed: true,
          consent_ok: true,
        }),
      });
      setAuctionResult(result);
      await loadWorkbench();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Auction evaluation failed');
    } finally {
      setBusy(false);
    }
  }

  const allLineItems = useMemo(() => workbench?.campaigns.flatMap((campaign) => campaign.line_items.map((line) => ({ ...line, campaignName: campaign.name }))) || [], [workbench]);

  if (!token || !user) {
    return (
      <main className="dsp-app login-screen">
        <section className="login-card">
          <div className="brand-mark large-mark">PS</div>
          <p className="eyebrow">Full DSP login</p>
          <h1>Pharma Signal</h1>
          <p>Sign in to manage campaign builds, bid factors, bulk edits, auction decisions, and audit trails.</p>
          <form onSubmit={login} className="form-grid">
            <label>Email<input value={email} onChange={(e) => setEmail(e.target.value)} /></label>
            <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
            <button className="primary-button" disabled={busy}><Lock size={16} /> Sign in</button>
          </form>
          <small>Local dev users use `@pharmasignal.local`; set `FULL_DSP_DEV_PASSWORD` to change the seed password.</small>
          {error && <div className="error-box">{error}</div>}
        </section>
      </main>
    );
  }

  return (
    <main className="dsp-app">
      <nav className="dsp-nav">
        <div className="brand-lockup"><div className="brand-mark">PS</div><div><p className="eyebrow">Enterprise DSP</p><strong>Pharma Signal Command OS</strong></div></div>
        <div className="nav-actions"><span>{user.email} · {user.role}</span><button onClick={loadWorkbench} disabled={busy}><RefreshCw size={16} /> Refresh</button><button onClick={() => { localStorage.removeItem('pharma_signal_full_token'); setToken(''); setUser(null); }}>Logout</button></div>
      </nav>

      {error && <div className="error-box wide">{error}</div>}

      <section className="dsp-hero">
        <div><p className="eyebrow">Not a mockup</p><h1>Build, edit, activate, and audit pharma campaigns.</h1><p>This workbench is wired to the full DSP API: login, campaign builder, line items, bid-factor engine, bulk edit, auction evaluation, supply paths, and audit history.</p></div>
        <div className="kpi-strip"><div><Activity /><span>Campaigns</span><strong>{workbench?.summary.campaigns || 0}</strong></div><div><Layers3 /><span>Line items</span><strong>{workbench?.summary.line_items || 0}</strong></div><div><BadgeCheck /><span>Total budget</span><strong>{money(workbench?.summary.total_budget || 0)}</strong></div></div>
      </section>

      <section className="dsp-grid two">
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
              <input value={line.name} onChange={(e) => setLineItems(lineItems.map((item, i) => i === index ? { ...item, name: e.target.value } : item))} />
              <input value={line.channel} onChange={(e) => setLineItems(lineItems.map((item, i) => i === index ? { ...item, channel: e.target.value } : item))} />
              <input type="number" value={line.budget} onChange={(e) => setLineItems(lineItems.map((item, i) => i === index ? { ...item, budget: Number(e.target.value) } : item))} />
              <input type="number" value={line.max_bid_cpm} onChange={(e) => setLineItems(lineItems.map((item, i) => i === index ? { ...item, max_bid_cpm: Number(e.target.value) } : item))} />
            </div>
          ))}
          <button type="button" className="secondary-button" onClick={() => setLineItems([...lineItems, { name: 'New Line Item', channel: 'Display', budget: 100000, max_bid_cpm: 20, pacing_mode: 'even', status: 'draft', frequency_cap: 3 }])}>Add line item</button>
          <button className="primary-button" disabled={busy}>Create campaign</button>
        </form>

        <form className="dsp-panel" onSubmit={saveBidFactors}>
          <div className="panel-title"><div><p className="eyebrow">Bid factors</p><h2>Weighted bid engine</h2></div><SlidersHorizontal /></div>
          <label>Line item<select value={selectedLineId} onChange={(e) => { setSelectedLineId(e.target.value); const found = allLineItems.find((line) => line.id === e.target.value); if (found?.bid_factors) setBidFactors(found.bid_factors); }}><option value="">Select line item</option>{allLineItems.map((line) => <option value={line.id} key={line.id}>{line.campaignName} · {line.name}</option>)}</select></label>
          <div className="form-grid two-col">
            {Object.entries(bidFactors).map(([key, value]) => (
              <label key={key}>{key.replaceAll('_', ' ')}<input type="number" step="0.01" value={value} onChange={(e) => setBidFactors({ ...bidFactors, [key]: Number(e.target.value) })} /></label>
            ))}
          </div>
          <button className="primary-button" disabled={busy || !selectedLineId}>Save bid factors</button>
          <button type="button" className="secondary-button" disabled={!selectedLineId || busy} onClick={evaluateAuction}><Zap size={16} /> Test auction</button>
          {auctionResult && <pre className="result-box">{JSON.stringify(auctionResult, null, 2)}</pre>}
        </form>
      </section>

      <section className="dsp-grid two">
        <form className="dsp-panel" onSubmit={bulkEdit}>
          <div className="panel-title"><div><p className="eyebrow">Bulk editor</p><h2>Edit campaigns, lines, or bid factors</h2></div><UploadCloud /></div>
          <label>Entity<select value={bulkForm.entity_type} onChange={(e) => setBulkForm({ ...bulkForm, entity_type: e.target.value })}><option value="campaign">Campaign</option><option value="line_item">Line item</option><option value="bid_factor">Bid factor</option></select></label>
          <label>IDs comma separated<textarea value={bulkForm.ids} onChange={(e) => setBulkForm({ ...bulkForm, ids: e.target.value })} placeholder="Paste IDs from the table" /></label>
          <label>Updates JSON<textarea value={bulkForm.updates} onChange={(e) => setBulkForm({ ...bulkForm, updates: e.target.value })} /></label>
          <label>Reason<input value={bulkForm.reason} onChange={(e) => setBulkForm({ ...bulkForm, reason: e.target.value })} /></label>
          <label className="check-row"><input type="checkbox" checked={bulkForm.dry_run} onChange={(e) => setBulkForm({ ...bulkForm, dry_run: e.target.checked })} /> Dry run first</label>
          <button className="primary-button" disabled={busy}>Run bulk edit</button>
        </form>

        <div className="dsp-panel">
          <div className="panel-title"><div><p className="eyebrow">Supply paths</p><h2>Approved inventory</h2></div><Boxes /></div>
          <div className="table-list">{workbench?.supply_paths.map((path) => <div key={path.id}><strong>{path.partner}</strong><span>{path.channel} · {path.deal_id}</span><span>{money(path.bid_floor_cpm)} floor · {pct(path.working_media_ratio)} working media</span><code>{path.id}</code></div>)}</div>
        </div>
      </section>

      <section className="dsp-panel">
        <div className="panel-title"><div><p className="eyebrow">Campaigns</p><h2>Live campaign table</h2></div><ClipboardList /></div>
        <div className="campaign-table">{workbench?.campaigns.map((campaign) => <article key={campaign.id}><header><strong>{campaign.name}</strong><span>{campaign.status}</span></header><p>{campaign.brand} · {campaign.indication} · {campaign.audience_type}</p><code>{campaign.id}</code><div className="nested-lines">{campaign.line_items.map((line) => <div key={line.id}><strong>{line.name}</strong><span>{line.channel} · {money(line.budget)} · max {money(line.max_bid_cpm)} CPM</span><code>{line.id}</code></div>)}</div></article>)}</div>
      </section>

      <section className="dsp-panel">
        <div className="panel-title"><div><p className="eyebrow">Audit</p><h2>Every login, build, edit, and auction is logged</h2></div></div>
        <div className="audit-list">{workbench?.audit.map((row) => <div key={row.id}><strong>{row.action}</strong><span>{row.actor}</span><span>{row.entity_type}:{row.entity_id}</span><small>{row.ts}</small></div>)}</div>
      </section>
    </main>
  );
}
