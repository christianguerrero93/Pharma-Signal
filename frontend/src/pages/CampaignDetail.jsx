import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api, fmtMoney, fmtPct, fmtNum } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import { ArrowLeft, Pencil } from "lucide-react";

const recoColor = (r) =>
  r === "Scale" ? "bg-emerald-100 text-emerald-800" :
  r === "Hold" ? "bg-amber-100 text-amber-800" :
  "bg-red-100 text-red-800";

export default function CampaignDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [data, setData] = useState(null);
  const [allAud, setAllAud] = useState([]);
  const [allPmps, setAllPmps] = useState([]);
  const [open, setOpen] = useState(false);
  const [linkAud, setLinkAud] = useState([]);
  const [linkPmp, setLinkPmp] = useState([]);

  const load = async () => {
    const { data } = await api.get(`/campaigns/${id}`);
    setData(data);
    setLinkAud(data.campaign.audience_ids || []);
    setLinkPmp(data.campaign.pmp_ids || []);
  };
  useEffect(() => {
    load();
    api.get("/audiences").then(r => setAllAud(r.data));
    api.get("/pmps").then(r => setAllPmps(r.data));
  }, [id]);

  if (!data) return <div className="text-slate-500">Loading…</div>;

  const c = data.campaign;
  const perf = data.performance;
  const pacing = c.budget ? (c.spent / c.budget) * 100 : 0;

  const save = async () => {
    await api.patch(`/campaigns/${id}`, { audience_ids: linkAud, pmp_ids: linkPmp });
    toast.success("Links updated");
    setOpen(false);
    load();
  };

  return (
    <div data-testid="campaign-detail-page">
      <button onClick={() => nav("/campaigns")} className="text-xs text-slate-500 hover:text-slate-800 inline-flex items-center gap-1 mb-3" data-testid="back-btn">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to campaigns
      </button>
      <PageHeader
        kicker={c.campaign_type === "HCP" ? "HCP · Provider Campaign" : "DTC · Patient Campaign"}
        title={c.name}
        description={`${c.brand} · ${c.indication} · ${c.flight_start} → ${c.flight_end}`}
        actions={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" data-testid="edit-links-btn" className="gap-2">
                <Pencil className="h-4 w-4" /> Link Audiences & PMPs
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-3xl">
              <DialogHeader>
                <DialogTitle>Link Audiences & PMPs</DialogTitle>
                <DialogDescription>Attach audiences and supply deals to drive this campaign's performance reporting and bidder logic.</DialogDescription>
              </DialogHeader>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <div className="text-[10px] uppercase tracking-[0.1em] font-semibold text-slate-500 mb-2">Audiences</div>
                  <div className="max-h-72 overflow-y-auto space-y-1.5 border border-slate-200 rounded-md p-2">
                    {allAud.map(a => (
                      <label key={a.id} className="flex items-start gap-2 text-sm p-1.5 hover:bg-slate-50 rounded cursor-pointer">
                        <Checkbox checked={linkAud.includes(a.id)} onCheckedChange={(v) => setLinkAud(s => v ? [...s, a.id] : s.filter(x => x !== a.id))} />
                        <div className="flex-1">
                          <div className="text-slate-900">{a.name}</div>
                          <div className="text-xs text-slate-500">{a.type} · match {(a.match_rate_forecast * 100).toFixed(0)}%</div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-[0.1em] font-semibold text-slate-500 mb-2">PMPs</div>
                  <div className="max-h-72 overflow-y-auto space-y-1.5 border border-slate-200 rounded-md p-2">
                    {allPmps.map(p => (
                      <label key={p.id} className="flex items-start gap-2 text-sm p-1.5 hover:bg-slate-50 rounded cursor-pointer">
                        <Checkbox checked={linkPmp.includes(p.id)} onCheckedChange={(v) => setLinkPmp(s => v ? [...s, p.id] : s.filter(x => x !== p.id))} />
                        <div className="flex-1">
                          <div className="text-slate-900">{p.vendor}</div>
                          <div className="text-xs text-slate-500">Score {p.outcome_adjusted_score} · {p.recommendation}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                <Button onClick={save} className="bg-blue-900 hover:bg-blue-950" data-testid="save-links-btn">Save</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      {/* Performance KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white border border-slate-200 rounded-md p-4">
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Budget · Pacing</div>
          <div className="metric-num text-2xl text-slate-900 mt-2">{fmtMoney(c.budget)}</div>
          <div className="text-xs text-slate-500 font-mono mt-1">{fmtPct(pacing)} spent · {fmtMoney(c.spent)}</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-md p-4">
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Avg Supply Score</div>
          <div className="metric-num text-2xl text-slate-900 mt-2">{perf.avg_supply_score}/100</div>
          <div className="text-xs text-slate-500 mt-1">from {data.pmps.length} linked PMPs</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-md p-4">
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Script Lift</div>
          <div className="metric-num text-2xl text-emerald-700 mt-2">+{perf.avg_script_lift_pct}%</div>
          <div className="text-xs text-slate-500 mt-1">avg across PMPs</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-md p-4">
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Working Media</div>
          <div className="metric-num text-2xl text-slate-900 mt-2">{perf.avg_working_media_pct}%</div>
          <div className="text-xs text-slate-500 mt-1">avg efficiency</div>
        </div>
      </div>

      {/* Campaign details */}
      <div className="bg-white border border-slate-200 rounded-md p-5 mb-6">
        <h3 className="font-heading font-semibold text-slate-900 mb-3">Campaign Setup</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div><div className="text-xs text-slate-500">Type</div><Badge variant="outline" className={c.campaign_type === "HCP" ? "border-blue-300 text-blue-800 mt-1" : "border-emerald-300 text-emerald-800 mt-1"}>{c.campaign_type}</Badge></div>
          <div><div className="text-xs text-slate-500">Outcome KPI</div><div className="text-slate-900 mt-1">{c.outcome_kpi}</div></div>
          <div><div className="text-xs text-slate-500">Data Partner</div><div className="text-slate-900 mt-1">{c.data_partner || "—"}</div></div>
          <div><div className="text-xs text-slate-500">Frequency Cap</div><div className="text-slate-900 mt-1 font-mono">{c.frequency_cap}/wk</div></div>
          {c.campaign_type === "HCP" && <>
            <div><div className="text-xs text-slate-500">Specialty</div><div className="text-slate-900 mt-1">{c.specialty || "—"}</div></div>
            <div><div className="text-xs text-slate-500">NPI Targets</div><div className="text-slate-900 mt-1 font-mono">{fmtNum(c.npi_target_count)}</div></div>
          </>}
          {c.campaign_type === "DTC" && <div className="col-span-2"><div className="text-xs text-slate-500">Diagnosis / Segment</div><div className="text-slate-900 mt-1">{c.diagnosis || "—"}</div></div>}
          <div><div className="text-xs text-slate-500">MLR</div><Badge className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100 mt-1">{c.mlr_status}</Badge></div>
          <div><div className="text-xs text-slate-500">Channels</div><div className="text-slate-900 mt-1 text-xs">{(c.channels || []).join(", ") || "—"}</div></div>
        </div>
      </div>

      {/* Linked audiences & PMPs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <div className="bg-white border border-slate-200 rounded-md p-5" data-testid="linked-audiences">
          <h3 className="font-heading font-semibold text-slate-900 mb-3">Linked Audiences ({data.audiences.length})</h3>
          {data.audiences.length === 0 ? (
            <div className="text-sm text-slate-500">No audiences linked yet.</div>
          ) : (
            <div className="space-y-2">
              {data.audiences.map(a => (
                <div key={a.id} className="flex items-center justify-between text-sm border-b border-slate-100 pb-2 last:border-0">
                  <div><div className="text-slate-900 font-medium">{a.name}</div><div className="text-xs text-slate-500">{a.type} · {a.data_partner}</div></div>
                  <div className="text-right text-xs text-slate-500 font-mono">match {(a.match_rate_forecast * 100).toFixed(0)}% · WM {(a.working_media_ratio * 100).toFixed(0)}%</div>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="bg-white border border-slate-200 rounded-md p-5" data-testid="linked-pmps">
          <h3 className="font-heading font-semibold text-slate-900 mb-3">Linked PMPs ({data.pmps.length})</h3>
          {data.pmps.length === 0 ? (
            <div className="text-sm text-slate-500">No PMPs linked yet.</div>
          ) : (
            <div className="space-y-2">
              {data.pmps.map(p => (
                <div key={p.id} className="flex items-center justify-between text-sm border-b border-slate-100 pb-2 last:border-0">
                  <div><div className="text-slate-900 font-medium">{p.vendor}</div><div className="text-xs text-slate-500 font-mono">{p.deal_id}</div></div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-heading font-bold text-slate-900">{p.outcome_adjusted_score}</span>
                    <Badge className={`${recoColor(p.recommendation)} hover:${recoColor(p.recommendation)} text-[10px]`}>{p.recommendation}</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Creatives / MLR */}
      <div className="bg-white border border-slate-200 rounded-md p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-heading font-semibold text-slate-900">Creatives & MLR Status ({data.creatives.length})</h3>
          <Link to="/mlr" className="text-xs text-blue-700 hover:underline">Open MLR Review →</Link>
        </div>
        {data.creatives.length === 0 ? (
          <div className="text-sm text-slate-500">No creatives yet.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {data.creatives.map(cr => (
              <div key={cr.id} className="border border-slate-200 rounded-md p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-sm font-medium text-slate-900">{cr.asset_name}</div>
                    <div className="text-xs text-slate-500 font-mono mt-0.5">{cr.format}</div>
                  </div>
                  <Badge className={
                    cr.mlr_status === "Approved" ? "bg-emerald-100 text-emerald-800 hover:bg-emerald-100" :
                    cr.mlr_status === "Pending" ? "bg-amber-100 text-amber-800 hover:bg-amber-100" :
                    "bg-red-100 text-red-800 hover:bg-red-100"
                  }>{cr.mlr_status}</Badge>
                </div>
                <div className="text-xs text-slate-600 mt-2">{cr.claims}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
