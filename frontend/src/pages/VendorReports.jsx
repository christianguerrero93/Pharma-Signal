import { useEffect, useState } from "react";
import { api, fmtMoney } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import PageHeader from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Printer, FileText, Share2, Copy, Check, Trash2 } from "lucide-react";
import { toast } from "sonner";

const recoColor = (r) =>
  r === "Scale" ? "bg-emerald-100 text-emerald-800" :
  r === "Hold" ? "bg-amber-100 text-amber-800" :
  "bg-red-100 text-red-800";

export default function VendorReports() {
  const [rows, setRows] = useState([]);
  const [printVendor, setPrintVendor] = useState(null);
  const [pmps, setPmps] = useState([]);
  const [shareOpen, setShareOpen] = useState(false);
  const [shareVendor, setShareVendor] = useState(null);
  const [shareDays, setShareDays] = useState(14);
  const [shares, setShares] = useState([]);
  const [creating, setCreating] = useState(false);
  const { has } = useAuth();
  const canShare = has && has("admin", "trader");

  const loadShares = () => {
    if (!canShare) return;
    api.get("/shares/vendor").then(r => setShares(r.data)).catch(() => {});
  };

  useEffect(() => {
    api.get("/vendors").then(r => setRows(r.data));
    api.get("/pmps").then(r => setPmps(r.data));
    loadShares();
  }, []);

  const openShare = (v) => {
    setShareVendor(v);
    setShareOpen(true);
  };

  const createShare = async () => {
    setCreating(true);
    try {
      const { data } = await api.post("/shares/vendor", { vendor: shareVendor.vendor, expires_in_days: shareDays });
      toast.success("Share link created");
      loadShares();
      const url = `${window.location.origin}/share/v/${data.token}`;
      try { await navigator.clipboard.writeText(url); toast.success("Link copied"); } catch {}
    } finally { setCreating(false); }
  };

  const revoke = async (id) => {
    await api.delete(`/shares/vendor/${id}`);
    toast.success("Revoked");
    loadShares();
  };

  const copyLink = async (token) => {
    const url = `${window.location.origin}/share/v/${token}`;
    try { await navigator.clipboard.writeText(url); toast.success("Link copied"); } catch {
      toast.error("Copy failed");
    }
  };

  const openPrint = (v) => {
    setPrintVendor(v);
    setTimeout(() => window.print(), 300);
  };

  const vendorPmps = (vendor) => pmps.filter(p => p.vendor === vendor);

  return (
    <div data-testid="vendors-page">
      <div className="print:hidden">
        <PageHeader
          kicker="Vendor Conversations"
          title="Vendor Value Reports"
          description="A senior, outcome-led lens for vendor conversations. Export any vendor's scorecard as a one-page PDF for sales-call leverage."
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
              <div className="flex gap-2 mt-4">
              <Button onClick={() => openPrint(v)} variant="outline" size="sm"
                className="flex-1 gap-1.5" data-testid={`export-${v.vendor}`}>
                <FileText className="h-3.5 w-3.5" /> PDF
              </Button>
              {canShare && (
                <Button onClick={() => openShare(v)} variant="outline" size="sm"
                  className="flex-1 gap-1.5" data-testid={`share-${v.vendor}`}>
                  <Share2 className="h-3.5 w-3.5" /> Share Link
                </Button>
              )}
            </div>
            </div>
          ))}
        </div>

        {/* Active shares table */}
        {canShare && shares.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-md p-5 mt-6" data-testid="shares-list">
            <h3 className="font-heading font-semibold text-slate-900 mb-3">Active Share Links ({shares.length})</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-slate-200">
                  <tr className="text-[10px] uppercase tracking-[0.1em] text-slate-500">
                    <th className="text-left font-semibold py-2">Vendor</th>
                    <th className="text-left font-semibold py-2">Token</th>
                    <th className="text-left font-semibold py-2">Created By</th>
                    <th className="text-left font-semibold py-2">Expires</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {shares.map(s => (
                    <tr key={s.id} className="border-b border-slate-100" data-testid={`share-row-${s.id}`}>
                      <td className="py-2 font-medium text-slate-900">{s.vendor}</td>
                      <td className="py-2 font-mono text-xs text-slate-600">{s.token.slice(0,12)}…</td>
                      <td className="py-2 text-slate-600">{s.created_by}</td>
                      <td className="py-2 text-slate-600 font-mono text-xs">{new Date(s.expires_at).toLocaleDateString()}</td>
                      <td className="py-2 text-right">
                        <button onClick={() => copyLink(s.token)} className="text-slate-500 hover:text-blue-700 inline-flex items-center gap-1 mr-3" data-testid={`copy-${s.id}`}>
                          <Copy className="h-3.5 w-3.5" /> Copy
                        </button>
                        <button onClick={() => revoke(s.id)} className="text-slate-400 hover:text-red-600" data-testid={`revoke-${s.id}`}>
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Share dialog */}
      <Dialog open={shareOpen} onOpenChange={setShareOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Share {shareVendor?.vendor} scorecard</DialogTitle>
            <DialogDescription>
              Create a read-only public link that any vendor contact can open without an account. You can revoke it any time.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Link expires in (days)</label>
              <Input type="number" min={1} max={90} value={shareDays}
                onChange={(e) => setShareDays(parseInt(e.target.value) || 14)}
                className="mt-1.5" data-testid="share-days" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShareOpen(false)}>Cancel</Button>
            <Button onClick={createShare} disabled={creating} className="bg-blue-900 hover:bg-blue-950 gap-1.5" data-testid="create-share">
              <Share2 className="h-4 w-4" /> {creating ? "Creating…" : "Create & Copy Link"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Print-only scorecard */}
      {printVendor && (
        <div className="hidden print:block" data-testid="print-scorecard">
          <div className="p-8 max-w-3xl mx-auto">
            <div className="border-b-2 border-slate-900 pb-4 mb-6 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-[0.2em] font-semibold text-slate-500">PharmaSignal DSP · Vendor Scorecard</div>
                <h1 className="font-heading text-3xl font-bold text-slate-900 mt-1">{printVendor.vendor}</h1>
              </div>
              <div className={`px-3 py-1.5 rounded-md text-sm font-semibold ${recoColor(printVendor.recommendation)}`}>
                Recommendation: {printVendor.recommendation}
              </div>
            </div>

            <div className="grid grid-cols-4 gap-4 mb-6">
              <div className="border border-slate-200 rounded p-3">
                <div className="text-[10px] uppercase tracking-wide font-semibold text-slate-500">Avg Score</div>
                <div className="metric-num text-2xl mt-1">{printVendor.avg_score}/100</div>
              </div>
              <div className="border border-slate-200 rounded p-3">
                <div className="text-[10px] uppercase tracking-wide font-semibold text-slate-500">Total Spend</div>
                <div className="metric-num text-2xl mt-1">{fmtMoney(printVendor.spend)}</div>
              </div>
              <div className="border border-slate-200 rounded p-3">
                <div className="text-[10px] uppercase tracking-wide font-semibold text-slate-500">Script Lift</div>
                <div className="metric-num text-2xl mt-1 text-emerald-700">+{printVendor.script_lift_contribution}%</div>
              </div>
              <div className="border border-slate-200 rounded p-3">
                <div className="text-[10px] uppercase tracking-wide font-semibold text-slate-500">Working Media</div>
                <div className="metric-num text-2xl mt-1">{(printVendor.working_media * 100).toFixed(0)}%</div>
              </div>
            </div>

            <h2 className="font-heading text-lg font-semibold text-slate-900 mb-2">Deal-Level Performance</h2>
            <table className="w-full text-xs border border-slate-200">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="text-left p-2">Deal</th>
                  <th className="text-right p-2">Spend</th>
                  <th className="text-right p-2">Score</th>
                  <th className="text-right p-2">Reach</th>
                  <th className="text-right p-2">Engagement</th>
                  <th className="text-right p-2">Match</th>
                  <th className="text-right p-2">WM</th>
                  <th className="text-right p-2">Data Drag</th>
                  <th className="text-right p-2">Rx Lift</th>
                </tr>
              </thead>
              <tbody>
                {vendorPmps(printVendor.vendor).map(p => (
                  <tr key={p.id} className="border-b border-slate-100">
                    <td className="p-2 font-mono">{p.deal_id}</td>
                    <td className="p-2 text-right mono-num">{fmtMoney(p.spend)}</td>
                    <td className="p-2 text-right mono-num font-bold">{p.outcome_adjusted_score}</td>
                    <td className="p-2 text-right mono-num">{(p.verified_reach * 100).toFixed(0)}%</td>
                    <td className="p-2 text-right mono-num">{(p.engagement_quality * 100).toFixed(0)}%</td>
                    <td className="p-2 text-right mono-num">{(p.match_rate * 100).toFixed(0)}%</td>
                    <td className="p-2 text-right mono-num">{(p.working_media_efficiency * 100).toFixed(0)}%</td>
                    <td className="p-2 text-right mono-num text-amber-700">{(p.data_cost_drag * 100).toFixed(0)}%</td>
                    <td className="p-2 text-right mono-num text-emerald-700">+{p.script_lift_pct.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="mt-6 p-4 border-l-4 border-blue-900 bg-slate-50">
              <div className="text-[10px] uppercase tracking-[0.15em] font-semibold text-slate-600 mb-1">Strategic Note</div>
              <p className="text-sm text-slate-800 leading-relaxed">
                {printVendor.recommendation === "Scale" && (
                  <>{printVendor.vendor} is currently outperforming the portfolio average with composite outcome score {printVendor.avg_score}/100. Lift contribution is materially above peers and working-media efficiency is healthy. Recommend reallocation of additional budget toward this supply, with a focus on the highest-scoring deals listed above.</>
                )}
                {printVendor.recommendation === "Hold" && (
                  <>{printVendor.vendor} is delivering at portfolio average with score {printVendor.avg_score}/100. Hold current spend levels; opportunity exists to tighten match-rate and reduce data-cost drag on lower-performing deals before scaling further.</>
                )}
                {printVendor.recommendation === "Reduce" && (
                  <>{printVendor.vendor} is below acceptable performance thresholds (score {printVendor.avg_score}/100). Lift contribution is insufficient relative to data-cost drag and supply-quality risk. Recommend immediate budget reduction and SPO review of deal IDs listed.</>
                )}
              </p>
            </div>

            <div className="mt-6 text-[10px] text-slate-400 text-center">
              Generated by PharmaSignal DSP · Confidential · {new Date().toLocaleDateString()}
            </div>
          </div>
        </div>
      )}

      <style>{`
        @media print {
          body { background: white !important; }
          aside, header, [data-testid='sidebar-nav'] { display: none !important; }
          main { padding: 0 !important; overflow: visible !important; }
        }
      `}</style>
    </div>
  );
}
