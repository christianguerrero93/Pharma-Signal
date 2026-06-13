import { useEffect, useState } from "react";
import { api, fmtMoney } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";

const recoColor = (r) =>
  r === "Scale" ? "bg-emerald-100 text-emerald-800" :
  r === "Hold" ? "bg-amber-100 text-amber-800" :
  "bg-red-100 text-red-800";

export default function VendorReports() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/vendors").then(r => setRows(r.data)); }, []);

  return (
    <div data-testid="vendors-page">
      <PageHeader
        kicker="Vendor Conversations"
        title="Vendor Value Reports"
        description="A senior, outcome-led lens for vendor conversations: avg supply score, lift contribution, working media efficiency, and recommended action."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {rows.map((v) => (
          <div key={v.vendor} className="bg-white border border-slate-200 rounded-md p-5 hover:shadow-sm transition-all" data-testid={`vendor-${v.vendor}`}>
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="font-heading font-bold text-lg text-slate-900">{v.vendor}</div>
                <div className="text-xs text-slate-500 font-mono">{v.deals} deal{v.deals !== 1 ? "s" : ""}</div>
              </div>
              <Badge className={`${recoColor(v.recommendation)} hover:${recoColor(v.recommendation)}`}>{v.recommendation}</Badge>
            </div>
            <div className="grid grid-cols-2 gap-3 mt-4">
              <div>
                <div className="text-[10px] uppercase tracking-[0.1em] font-semibold text-slate-500">Avg Score</div>
                <div className="metric-num text-2xl text-slate-900 mt-1">{v.avg_score}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.1em] font-semibold text-slate-500">Spend</div>
                <div className="metric-num text-xl text-slate-900 mt-1">{fmtMoney(v.spend)}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.1em] font-semibold text-slate-500">Lift Contrib.</div>
                <div className="metric-num text-xl text-emerald-700 mt-1">+{v.script_lift_contribution.toFixed(1)}%</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.1em] font-semibold text-slate-500">Working Media</div>
                <div className="metric-num text-xl text-slate-900 mt-1">{(v.working_media * 100).toFixed(0)}%</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
