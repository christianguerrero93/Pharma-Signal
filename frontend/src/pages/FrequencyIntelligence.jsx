import { useEffect, useState } from "react";
import { api, fmtNum } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
} from "recharts";

const riskColor = {
  Critical: "#dc2626",
  High: "#d97706",
  Moderate: "#f59e0b",
  Healthy: "#059669",
};
const riskBadge = (r) => (
  <Badge className={
    r === "Critical" ? "bg-red-100 text-red-800 hover:bg-red-100" :
    r === "High" ? "bg-orange-100 text-orange-800 hover:bg-orange-100" :
    r === "Moderate" ? "bg-amber-100 text-amber-800 hover:bg-amber-100" :
    "bg-emerald-100 text-emerald-800 hover:bg-emerald-100"
  }>{r}</Badge>
);

export default function FrequencyIntelligence() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/frequency-intelligence").then(r => setData(r.data)); }, []);

  if (!data) return <div className="text-slate-500">Loading…</div>;
  const { rows, summary } = data;

  return (
    <div data-testid="frequency-page">
      <PageHeader
        kicker="HCP Saturation"
        title="Frequency Intelligence"
        description="Detect overexposure risk per HCP target list. Small NPI lists are easy to over-serve, which kills engagement and inflates frequency-cap violations."
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white border border-slate-200 rounded-md p-4">
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">HCP Lists Tracked</div>
          <div className="metric-num text-3xl text-slate-900 mt-2">{summary.total_hcp_lists}</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-md p-4" data-testid="freq-critical">
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-red-700">Critical</div>
          <div className="metric-num text-3xl text-red-700 mt-2">{summary.critical}</div>
          <div className="text-xs text-slate-500 mt-1">{">"}115% of cap</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-md p-4">
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-orange-700">High Risk</div>
          <div className="metric-num text-3xl text-orange-700 mt-2">{summary.high}</div>
          <div className="text-xs text-slate-500 mt-1">85–115% of cap</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-md p-4">
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-emerald-700">Healthy</div>
          <div className="metric-num text-3xl text-emerald-700 mt-2">{summary.healthy}</div>
          <div className="text-xs text-slate-500 mt-1">{"<"}55% of cap</div>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-md p-5 mb-6" data-testid="freq-chart">
        <h3 className="font-heading font-semibold text-slate-900 mb-1">Saturation % vs. Frequency Cap</h3>
        <p className="text-xs text-slate-500 mb-4">100% = at-cap. Bars over 100% indicate over-saturation.</p>
        <ResponsiveContainer width="100%" height={360}>
          <BarChart data={rows} margin={{ left: 10 }}>
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="audience_name" tick={{ fontSize: 10, fill: "#64748b" }} angle={-18} textAnchor="end" height={80} interval={0} />
            <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickFormatter={(v) => `${v}%`} />
            <Tooltip contentStyle={{ fontSize: 12 }} formatter={(v) => `${v}%`} />
            <Bar dataKey="saturation_pct" radius={[3, 3, 0, 0]}>
              {rows.map((r, i) => <Cell key={i} fill={riskColor[r.risk]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
        <table className="w-full text-sm" data-testid="freq-table">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr className="text-[10px] uppercase tracking-[0.1em] text-slate-500">
              <th className="text-left font-semibold py-2.5 px-4">Audience</th>
              <th className="text-left font-semibold py-2.5 px-3">Campaign</th>
              <th className="text-right font-semibold py-2.5 px-3">Audience Size</th>
              <th className="text-right font-semibold py-2.5 px-3">Cap (wk)</th>
              <th className="text-right font-semibold py-2.5 px-3">Wkly / HCP</th>
              <th className="text-right font-semibold py-2.5 px-3">Saturation</th>
              <th className="text-center font-semibold py-2.5 px-3">Risk</th>
              <th className="text-left font-semibold py-2.5 px-3">Recommendation</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                <td className="py-3 px-4 text-slate-900 font-medium">{r.audience_name}</td>
                <td className="py-3 px-3 text-slate-700">{r.campaign_name}<div className="text-xs text-slate-500">{r.brand}</div></td>
                <td className="py-3 px-3 text-right mono-num">{fmtNum(r.audience_size)}</td>
                <td className="py-3 px-3 text-right mono-num">{r.frequency_cap}</td>
                <td className="py-3 px-3 text-right mono-num">{r.weekly_impressions_per_hcp.toFixed(2)}</td>
                <td className={`py-3 px-3 text-right mono-num font-medium ${r.saturation_pct >= 115 ? "text-red-700" : r.saturation_pct >= 85 ? "text-orange-700" : ""}`}>
                  {r.saturation_pct.toFixed(0)}%
                </td>
                <td className="py-3 px-3 text-center">{riskBadge(r.risk)}</td>
                <td className="py-3 px-3 text-xs text-slate-600">{r.recommendation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
