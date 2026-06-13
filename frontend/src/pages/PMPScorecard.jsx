import { useEffect, useState } from "react";
import { api, fmtMoney, fmtNum } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import {
  ResponsiveContainer, ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Cell,
} from "recharts";

const recoColor = (r) =>
  r === "Scale" ? "bg-emerald-100 text-emerald-800" :
  r === "Hold" ? "bg-amber-100 text-amber-800" :
  "bg-red-100 text-red-800";

export default function PMPScorecard() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/pmps").then(r => setRows(r.data)); }, []);

  return (
    <div data-testid="pmp-scorecard-page">
      <PageHeader
        kicker="Killer Feature"
        title="Outcome-Adjusted Supply Score"
        description="Every PMP gets one composite score: verified reach + engagement quality + script lift + working media + match rate, minus data cost drag and fraud risk."
      />

      <div className="bg-white border border-slate-200 rounded-md p-5 mb-6" data-testid="pmp-chart">
        <h3 className="font-heading font-semibold text-slate-900 mb-1">Score Composition by Vendor</h3>
        <p className="text-xs text-slate-500 mb-4 font-mono">score = reach·22 + engagement·18 + max(lift,0)·4 + working_media·18 + match·18 − data_drag·25 − fraud·60</p>
        <ResponsiveContainer width="100%" height={360}>
          <ComposedChart data={rows}>
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="vendor" tick={{ fontSize: 11, fill: "#64748b" }} angle={-12} textAnchor="end" height={60} />
            <YAxis yAxisId="left" domain={[0, 100]} tick={{ fontSize: 11, fill: "#64748b" }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: "#64748b" }} />
            <Tooltip contentStyle={{ fontSize: 12, borderRadius: 6 }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar yAxisId="left" dataKey="outcome_adjusted_score" name="Outcome-Adjusted Score" radius={[3, 3, 0, 0]}>
              {rows.map((r, i) => (
                <Cell key={i} fill={r.outcome_adjusted_score >= 72 ? "#059669" : r.outcome_adjusted_score >= 55 ? "#d97706" : "#dc2626"} />
              ))}
            </Bar>
            <Line yAxisId="right" type="monotone" dataKey="script_lift_pct" name="Script Lift %" stroke="#1e3a8a" strokeWidth={2} dot={{ r: 3 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="pmp-table">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-[10px] uppercase tracking-[0.1em] text-slate-500">
                <th className="text-left font-semibold py-2.5 px-4">Vendor / Deal</th>
                <th className="text-right font-semibold py-2.5 px-3">Spend</th>
                <th className="text-right font-semibold py-2.5 px-3">Verified Reach</th>
                <th className="text-right font-semibold py-2.5 px-3">Engagement</th>
                <th className="text-right font-semibold py-2.5 px-3">Match</th>
                <th className="text-right font-semibold py-2.5 px-3">Working Media</th>
                <th className="text-right font-semibold py-2.5 px-3">Data Drag</th>
                <th className="text-right font-semibold py-2.5 px-3">Script Lift</th>
                <th className="text-right font-semibold py-2.5 px-3">Score</th>
                <th className="text-center font-semibold py-2.5 px-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(p => (
                <tr key={p.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                  <td className="py-3 px-4">
                    <div className="font-medium text-slate-900">{p.vendor}</div>
                    <div className="text-xs text-slate-500 font-mono">{p.deal_id} · {p.supply_path}</div>
                  </td>
                  <td className="py-3 px-3 text-right mono-num">{fmtMoney(p.spend)}</td>
                  <td className="py-3 px-3 text-right mono-num">{(p.verified_reach * 100).toFixed(1)}%</td>
                  <td className="py-3 px-3 text-right mono-num">{(p.engagement_quality * 100).toFixed(1)}%</td>
                  <td className="py-3 px-3 text-right mono-num">{(p.match_rate * 100).toFixed(1)}%</td>
                  <td className="py-3 px-3 text-right mono-num">{(p.working_media_efficiency * 100).toFixed(1)}%</td>
                  <td className="py-3 px-3 text-right mono-num text-amber-700">{(p.data_cost_drag * 100).toFixed(1)}%</td>
                  <td className={`py-3 px-3 text-right mono-num ${p.script_lift_pct >= 2 ? "text-emerald-700 font-medium" : p.script_lift_pct < 0 ? "text-red-600" : ""}`}>
                    {p.script_lift_pct > 0 ? "+" : ""}{p.script_lift_pct.toFixed(2)}%
                  </td>
                  <td className="py-3 px-3 text-right">
                    <span className="font-heading font-bold text-base text-slate-900">{p.outcome_adjusted_score}</span>
                    <span className="text-xs text-slate-400 ml-0.5">/100</span>
                  </td>
                  <td className="py-3 px-3 text-center">
                    <Badge className={`${recoColor(p.recommendation)} hover:${recoColor(p.recommendation)}`}>{p.recommendation}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
