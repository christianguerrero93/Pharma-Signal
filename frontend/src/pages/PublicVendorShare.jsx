import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import axios from "axios";
import { API, fmtMoney } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { CircleDot, Lock } from "lucide-react";

const recoColor = (r) =>
  r === "Scale" ? "bg-emerald-100 text-emerald-800" :
  r === "Hold" ? "bg-amber-100 text-amber-800" :
  "bg-red-100 text-red-800";

export default function PublicVendorShare() {
  const { token } = useParams();
  const [state, setState] = useState({ loading: true, error: null, data: null });

  useEffect(() => {
    axios.get(`${API}/public/shares/vendor/${token}`)
      .then(r => setState({ loading: false, error: null, data: r.data }))
      .catch(e => setState({ loading: false, error: e.response?.data?.detail || "Link unavailable", data: null }));
  }, [token]);

  if (state.loading) return <div className="min-h-screen flex items-center justify-center text-slate-500">Loading scorecard…</div>;
  if (state.error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-8" data-testid="share-error">
        <div className="max-w-md text-center">
          <Lock className="h-8 w-8 text-slate-300 mx-auto mb-3" strokeWidth={1.5} />
          <h1 className="font-heading text-2xl font-bold text-slate-900">{state.error}</h1>
          <p className="text-sm text-slate-500 mt-2">This share link may have been revoked or expired. Please request a new one from your PharmaSignal contact.</p>
        </div>
      </div>
    );
  }
  const { vendor, deals, expires_at } = state.data;
  if (!vendor) return <div className="min-h-screen flex items-center justify-center text-slate-500">Vendor data unavailable.</div>;

  return (
    <div className="min-h-screen bg-slate-50" data-testid="public-share-page">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-sm bg-blue-900 flex items-center justify-center">
              <CircleDot className="h-4 w-4 text-white" strokeWidth={2.5} />
            </div>
            <div>
              <div className="font-heading font-bold text-[15px] text-slate-900">PharmaSignal</div>
              <div className="text-[10px] uppercase tracking-[0.15em] text-slate-500 -mt-0.5">Public Vendor Scorecard</div>
            </div>
          </div>
          <div className="text-xs text-slate-500 font-mono">Expires {new Date(expires_at).toLocaleDateString()}</div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-8 py-10">
        <div className="border-b-2 border-slate-900 pb-4 mb-6 flex items-center justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] font-semibold text-slate-500">Outcome-Adjusted Supply Scorecard</div>
            <h1 className="font-heading text-4xl font-bold text-slate-900 mt-1">{vendor.vendor}</h1>
          </div>
          <div className={`px-3 py-1.5 rounded-md text-sm font-semibold ${recoColor(vendor.recommendation)}`}>
            Recommendation: {vendor.recommendation}
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white border border-slate-200 rounded p-3">
            <div className="text-[10px] uppercase tracking-wide font-semibold text-slate-500">Avg Score</div>
            <div className="metric-num text-2xl mt-1">{vendor.avg_score}/100</div>
          </div>
          <div className="bg-white border border-slate-200 rounded p-3">
            <div className="text-[10px] uppercase tracking-wide font-semibold text-slate-500">Total Spend</div>
            <div className="metric-num text-2xl mt-1">{fmtMoney(vendor.spend)}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded p-3">
            <div className="text-[10px] uppercase tracking-wide font-semibold text-slate-500">Script Lift</div>
            <div className="metric-num text-2xl mt-1 text-emerald-700">+{vendor.script_lift_contribution}%</div>
          </div>
          <div className="bg-white border border-slate-200 rounded p-3">
            <div className="text-[10px] uppercase tracking-wide font-semibold text-slate-500">Working Media</div>
            <div className="metric-num text-2xl mt-1">{(vendor.working_media * 100).toFixed(0)}%</div>
          </div>
        </div>

        <h2 className="font-heading text-lg font-semibold text-slate-900 mb-2">Deal-Level Performance</h2>
        <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left p-2.5">Deal</th>
                <th className="text-right p-2.5">Spend</th>
                <th className="text-right p-2.5">Score</th>
                <th className="text-right p-2.5">Reach</th>
                <th className="text-right p-2.5">Engagement</th>
                <th className="text-right p-2.5">Match</th>
                <th className="text-right p-2.5">WM</th>
                <th className="text-right p-2.5">Data Drag</th>
                <th className="text-right p-2.5">Rx Lift</th>
              </tr>
            </thead>
            <tbody>
              {deals.map(p => (
                <tr key={p.id} className="border-b border-slate-100 last:border-0">
                  <td className="p-2.5 font-mono">{p.deal_id}</td>
                  <td className="p-2.5 text-right mono-num">{fmtMoney(p.spend)}</td>
                  <td className="p-2.5 text-right mono-num font-bold">{p.outcome_adjusted_score}</td>
                  <td className="p-2.5 text-right mono-num">{(p.verified_reach * 100).toFixed(0)}%</td>
                  <td className="p-2.5 text-right mono-num">{(p.engagement_quality * 100).toFixed(0)}%</td>
                  <td className="p-2.5 text-right mono-num">{(p.match_rate * 100).toFixed(0)}%</td>
                  <td className="p-2.5 text-right mono-num">{(p.working_media_efficiency * 100).toFixed(0)}%</td>
                  <td className="p-2.5 text-right mono-num text-amber-700">{(p.data_cost_drag * 100).toFixed(0)}%</td>
                  <td className="p-2.5 text-right mono-num text-emerald-700">+{p.script_lift_pct.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-6 text-[10px] text-slate-400 text-center">
          Confidential · Generated by PharmaSignal DSP · Public share link
        </div>
      </main>
    </div>
  );
}
