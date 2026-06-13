import { useEffect, useState } from "react";
import { api, fmtNum, fmtPct, fmtMoney } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";

const riskBadge = (lvl) => {
  const map = {
    Low: "bg-emerald-100 text-emerald-800",
    Medium: "bg-amber-100 text-amber-800",
    High: "bg-red-100 text-red-800",
  };
  return <Badge className={`${map[lvl]} hover:${map[lvl]}`}>{lvl}</Badge>;
};

export default function AudienceScorer() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/audiences").then(r => setRows(r.data)); }, []);

  return (
    <div data-testid="audience-scorer-page">
      <PageHeader
        kicker="Pre-Flight Intelligence"
        title="Audience Quality Scorer"
        description="Score every audience before launch on match rate, data CPM, working media, Rx relevance, and scale/waste risk."
      />

      <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="audiences-table">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-[10px] uppercase tracking-[0.1em] text-slate-500">
                <th className="text-left font-semibold py-2.5 px-4">Audience</th>
                <th className="text-left font-semibold py-2.5 px-3">Type</th>
                <th className="text-right font-semibold py-2.5 px-3">Est. Size</th>
                <th className="text-right font-semibold py-2.5 px-3">Match Rate</th>
                <th className="text-right font-semibold py-2.5 px-3">Data CPM</th>
                <th className="text-right font-semibold py-2.5 px-3">Working Media</th>
                <th className="text-right font-semibold py-2.5 px-3">Quality</th>
                <th className="text-right font-semibold py-2.5 px-3">Rx Relevance</th>
                <th className="text-center font-semibold py-2.5 px-3">Scale Risk</th>
                <th className="text-center font-semibold py-2.5 px-3">Waste Risk</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(a => (
                <tr key={a.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                  <td className="py-3 px-4">
                    <div className="font-medium text-slate-900">{a.name}</div>
                    <div className="text-xs text-slate-500">{a.data_partner}</div>
                  </td>
                  <td className="py-3 px-3">
                    <Badge variant="outline" className={a.type === "HCP" ? "border-blue-300 text-blue-800" : "border-emerald-300 text-emerald-800"}>{a.type}</Badge>
                  </td>
                  <td className="py-3 px-3 text-right mono-num">{fmtNum(a.estimated_size)}</td>
                  <td className="py-3 px-3 text-right mono-num">{(a.match_rate_forecast * 100).toFixed(1)}%</td>
                  <td className="py-3 px-3 text-right mono-num">${a.data_cpm.toFixed(2)}</td>
                  <td className="py-3 px-3 text-right mono-num">
                    <span className={a.working_media_ratio < 0.65 ? "text-amber-600 font-medium" : ""}>{(a.working_media_ratio * 100).toFixed(1)}%</span>
                  </td>
                  <td className="py-3 px-3 text-right mono-num">{a.audience_quality_score.toFixed(1)}</td>
                  <td className="py-3 px-3 text-right mono-num">{a.rx_relevance_score.toFixed(1)}</td>
                  <td className="py-3 px-3 text-center">{riskBadge(a.scale_risk)}</td>
                  <td className="py-3 px-3 text-center">{riskBadge(a.waste_risk)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
