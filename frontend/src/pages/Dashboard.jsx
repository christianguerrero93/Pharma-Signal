import { useEffect, useState } from "react";
import { api, fmtMoney, fmtPct, fmtNum } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import MetricCard from "@/components/MetricCard";
import {
  DollarSign, Target, Gauge, TrendingUp, Activity, Building2, Layers, Megaphone,
} from "lucide-react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar, Legend,
} from "recharts";

export default function Dashboard() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/dashboard/overview").then(r => setData(r.data)); }, []);

  if (!data) return <div className="text-slate-500" data-testid="loading">Loading control room…</div>;
  const k = data.kpis;

  return (
    <div data-testid="dashboard-page">
      <PageHeader
        kicker="Executive Control Room"
        title="Outcome over Impressions"
        description="Real-time view of working media, verified reach, supply quality, and Rx outcomes across your pharma portfolio."
      />

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
        <MetricCard testid="kpi-campaigns" label="Active Campaigns" value={`${k.active_campaigns}`}
          sub={`of ${k.total_campaigns} total`} icon={Megaphone} />
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
              Visit <a href="/ai" className="text-indigo-700 underline">AI Recommendations</a> for the full next-best-action briefing.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
