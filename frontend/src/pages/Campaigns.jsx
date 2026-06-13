import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, fmtMoney, fmtPct } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Plus, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function Campaigns() {
  const [rows, setRows] = useState([]);
  const nav = useNavigate();
  useEffect(() => { api.get("/campaigns").then(r => setRows(r.data)); }, []);

  return (
    <div data-testid="campaigns-page">
      <PageHeader
        kicker="Activation"
        title="Campaigns"
        description="Active and recent pharma campaigns across HCP and DTC strategies. Click any row for full performance drill-down."
        actions={
          <Link to="/campaigns/new" data-testid="new-campaign-btn"
            className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md bg-blue-900 text-white hover:bg-blue-950">
            <Plus className="h-4 w-4" /> New Campaign
          </Link>
        }
      />

      <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="campaigns-table">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-[10px] uppercase tracking-[0.1em] text-slate-500">
                <th className="text-left font-semibold py-2.5 px-4">Campaign</th>
                <th className="text-left font-semibold py-2.5 px-3">Brand · Indication</th>
                <th className="text-left font-semibold py-2.5 px-3">Type</th>
                <th className="text-right font-semibold py-2.5 px-3">Budget</th>
                <th className="text-right font-semibold py-2.5 px-3">Spent</th>
                <th className="text-right font-semibold py-2.5 px-3">Pacing</th>
                <th className="text-left font-semibold py-2.5 px-3">KPI</th>
                <th className="text-left font-semibold py-2.5 px-3">Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => {
                const pacing = c.budget ? (c.spent / c.budget) * 100 : 0;
                return (
                  <tr key={c.id} onClick={() => nav(`/campaigns/${c.id}`)}
                    data-testid={`campaign-row-${c.id}`}
                    className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-medium text-slate-900">{c.name}</div>
                      <div className="text-xs text-slate-500 font-mono">{c.flight_start} → {c.flight_end}</div>
                    </td>
                    <td className="py-3 px-3">
                      <div className="text-slate-900">{c.brand}</div>
                      <div className="text-xs text-slate-500">{c.indication}</div>
                    </td>
                    <td className="py-3 px-3">
                      <Badge variant="outline" className={c.campaign_type === "HCP" ? "border-blue-300 text-blue-800" : "border-emerald-300 text-emerald-800"}>
                        {c.campaign_type}
                      </Badge>
                    </td>
                    <td className="py-3 px-3 text-right mono-num">{fmtMoney(c.budget)}</td>
                    <td className="py-3 px-3 text-right mono-num">{fmtMoney(c.spent)}</td>
                    <td className="py-3 px-3 text-right mono-num">{fmtPct(pacing)}</td>
                    <td className="py-3 px-3 text-slate-700">{c.outcome_kpi}</td>
                    <td className="py-3 px-3">
                      <Badge className={c.status === "Active"
                        ? "bg-emerald-100 text-emerald-800 hover:bg-emerald-100"
                        : "bg-slate-100 text-slate-700 hover:bg-slate-100"}>
                        {c.status}
                      </Badge>
                    </td>
                    <td className="py-3 px-3 text-slate-400"><ChevronRight className="h-4 w-4" /></td>
                  </tr>
                );
              })}
              {rows.length === 0 && (
                <tr><td colSpan={9} className="text-center text-slate-500 py-8">No campaigns yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
