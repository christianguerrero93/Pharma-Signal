import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { api, fmtMoney, fmtPct, fmtNum } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import MetricCard from "@/components/MetricCard";
import {
  DollarSign, Target, Gauge, TrendingUp, Activity, Building2, Layers, Megaphone, X, Filter,
} from "lucide-react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar, Legend,
} from "recharts";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [filters, setFilters] = useState({ brand: "", indication: "", campaign_type: "" });
  const nav = useNavigate();

  const queryString = useMemo(() => {
    const p = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => { if (v) p.append(k, v); });
    return p.toString();
  }, [filters]);

  useEffect(() => {
    api.get(`/dashboard/overview?${queryString}`).then(r => setData(r.data));
  }, [queryString]);

  if (!data) return <div className="text-slate-500" data-testid="loading">Loading control room…</div>;
  const k = data.kpis;
  const fo = data.filter_options;

  const setFilter = (key, value) => setFilters(f => ({ ...f, [key]: f[key] === value ? "" : value }));
  const clearAll = () => setFilters({ brand: "", indication: "", campaign_type: "" });
  const hasFilter = Object.values(filters).some(Boolean);

  return (
    <div data-testid="dashboard-page">
      <PageHeader
        kicker="Executive Control Room"
        title="Outcome over Impressions"
        description="Real-time view of working media, verified reach, supply quality, and Rx outcomes across your pharma portfolio."
      />

      {/* Filter bar */}
      <div className="bg-white border border-slate-200 rounded-md p-4 mb-6 flex flex-wrap items-center gap-3" data-testid="dashboard-filters">
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">
          <Filter className="h-3.5 w-3.5" /> Filters
        </div>
        <div className="flex flex-wrap gap-1.5">
          {fo.campaign_types.map(t => (
            <button key={t} data-testid={`filter-type-${t}`}
              onClick={() => setFilter("campaign_type", t)}
              className={`text-xs px-2.5 py-1 rounded-md border transition-colors ${filters.campaign_type === t ? "bg-blue-900 text-white border-blue-900" : "bg-white text-slate-700 border-slate-200 hover:border-slate-300"}`}>
              {t}
            </button>
          ))}
        </div>
        <span className="text-slate-200">|</span>
        <select data-testid="filter-brand" value={filters.brand} onChange={(e) => setFilters(f => ({ ...f, brand: e.target.value }))}
          className="text-xs border border-slate-200 rounded-md px-2 py-1 bg-white">
          <option value="">All brands</option>
          {fo.brands.map(b => <option key={b} value={b}>{b}</option>)}
        </select>
        <select data-testid="filter-indication" value={filters.indication} onChange={(e) => setFilters(f => ({ ...f, indication: e.target.value }))}
          className="text-xs border border-slate-200 rounded-md px-2 py-1 bg-white">
          <option value="">All indications</option>
          {fo.indications.map(i => <option key={i} value={i}>{i}</option>)}
        </select>
        {hasFilter && (
          <button onClick={clearAll} data-testid="filter-clear"
            className="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1 ml-auto">
            <X className="h-3.5 w-3.5" /> Clear
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <MetricCard testid="kpi-budget" label="Total Budget" value={fmtMoney(k.total_budget)}
          sub={`Spent: ${fmtMoney(k.total_spent)}`} icon={DollarSign} />
        <MetricCard testid="kpi-working-media" label="Working Media" value={fmtPct(k.working_media_pct)}
          sub="vs. data & platform fees" delta="+2.4 pts WoW" deltaType="good" icon={Gauge} />
        <MetricCard testid="kpi-verified-reach" label="Verified Reach" value={fmtPct(k.verified_reach_pct)}
          sub="HCP + patient verified" delta="+1.1 pts" deltaType="good" icon={Target} />
        <MetricCard testid="kpi-script-lift" label="Script Lift" value={fmtPct(k.script_lift_pct, 1)}
          sub="exposed vs control" delta="+0.6 pts" deltaType="good" icon={TrendingUp} />
        <MetricCard testid="kpi-supply-score" label="Avg Supply Score" value={`${k.avg_supply_score}/100`}
          sub="outcome-adjusted" icon={Layers} />
        <MetricCard testid="kpi-campaigns" label="Campaigns" value={`${k.active_campaigns}/${k.total_campaigns}`}
          sub="active / total in view" icon={Megaphone} />
        <MetricCard testid="kpi-cpqo" label="Cost / Quality Outcome" value={fmtMoney(k.cost_per_quality_outcome)}
          sub="quality visit basis" icon={Activity} />
        <MetricCard testid="kpi-active-vendors" label="Top Vendors" value={data.top_pmps.length}
          sub="scaling recommended" icon={Building2} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-md p-5" data-testid="chart-script-lift">
          <div className="flex items-baseline justify-between mb-1">
            <h3 className="font-heading font-semibold text-slate-900">Script Lift — Exposed vs Control</h3>
            <span className="text-xs text-slate-500 font-mono">12-week index</span>
          </div>
          <p className="text-xs text-slate-500 mb-4">Indexed Rx volume relative to a matched control cohort.</p>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={data.script_lift_series}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="week" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={{ stroke: "#cbd5e1" }} />
              <YAxis tick={{ fontSize: 11, fill: "#64748b" }} axisLine={{ stroke: "#cbd5e1" }} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid #e2e8f0" }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="exposed_rx_index" name="Exposed" stroke="#059669" strokeWidth={2.2} dot={false} />
              <Line type="monotone" dataKey="control_rx_index" name="Control" stroke="#cbd5e1" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white border border-slate-200 rounded-md p-5" data-testid="chart-top-pmps">
          <h3 className="font-heading font-semibold text-slate-900 mb-1">Top Supply by Outcome Score</h3>
          <p className="text-xs text-slate-500 mb-4">Composite of verified reach, lift, working media, fraud risk.</p>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data.top_pmps} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: "#64748b" }} />
              <YAxis type="category" dataKey="vendor" tick={{ fontSize: 11, fill: "#64748b" }} width={110} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Bar dataKey="outcome_adjusted_score" fill="#1e3a8a" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-indigo-50/60 border border-indigo-200 rounded-md p-5" data-testid="ai-tease">
        <div className="flex items-start gap-3">
          <div className="h-8 w-8 rounded-md bg-indigo-900 flex items-center justify-center flex-shrink-0">
            <TrendingUp className="h-4 w-4 text-white" strokeWidth={2} />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.15em] font-semibold text-indigo-700">AI Strategist · Claude Sonnet 4.5</div>
            <p className="text-sm text-slate-800 mt-1 leading-relaxed">
              <span className="font-medium">{data.top_pmps[0]?.vendor}</span> is currently your strongest awareness driver — scaling with above-benchmark engagement quality and the lowest data-cost drag in your portfolio.
              Visit <button onClick={() => nav("/ai")} className="text-indigo-700 underline">AI Recommendations</button> for the full next-best-action briefing.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
