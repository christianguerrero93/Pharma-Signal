import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Check, X, FileCheck, Clock } from "lucide-react";

const statusColor = (s) =>
  s === "Approved" ? "bg-emerald-100 text-emerald-800" :
  s === "Pending" ? "bg-amber-100 text-amber-800" :
  "bg-red-100 text-red-800";

export default function MLRReview() {
  const [rows, setRows] = useState([]);
  const [tab, setTab] = useState("Pending");
  const [notes, setNotes] = useState({});

  const load = async () => {
    const { data } = await api.get("/creatives");
    setRows(data);
  };
  useEffect(() => { load(); }, []);

  const review = async (id, status) => {
    await api.patch(`/creatives/${id}`, { mlr_status: status, reviewer_notes: notes[id] || "" });
    toast.success(`Marked ${status}`);
    load();
  };

  const filtered = rows.filter(r => r.mlr_status === tab);

  const counts = {
    Pending: rows.filter(r => r.mlr_status === "Pending").length,
    Approved: rows.filter(r => r.mlr_status === "Approved").length,
    Rejected: rows.filter(r => r.mlr_status === "Rejected").length,
  };

  return (
    <div data-testid="mlr-page">
      <PageHeader
        kicker="Compliance Workflow"
        title="MLR Creative Review"
        description="Medical, Legal & Regulatory review queue. Approve, reject, or request changes — every action is timestamped for audit."
      />

      <div className="flex gap-2 border-b border-slate-200 mb-6" data-testid="mlr-tabs">
        {["Pending", "Approved", "Rejected"].map(s => (
          <button key={s} onClick={() => setTab(s)} data-testid={`mlr-tab-${s}`}
            className={`px-4 py-2 text-sm border-b-2 -mb-px transition-colors ${tab === s ? "border-blue-900 text-blue-900 font-medium" : "border-transparent text-slate-500 hover:text-slate-800"}`}>
            {s} <span className="ml-1.5 text-xs text-slate-400 font-mono">{counts[s]}</span>
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="bg-white border border-dashed border-slate-300 rounded-md p-12 text-center text-slate-500">
          <FileCheck className="h-8 w-8 mx-auto mb-3 text-slate-300" strokeWidth={1.5} />
          <div className="text-sm">No creatives in {tab}.</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map(cr => (
            <div key={cr.id} className="bg-white border border-slate-200 rounded-md p-5" data-testid={`creative-${cr.id}`}>
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <div className="font-heading font-semibold text-slate-900">{cr.asset_name}</div>
                  <div className="text-xs text-slate-500 font-mono mt-0.5">{cr.format} · {cr.brand}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{cr.indication}</div>
                </div>
                <Badge className={`${statusColor(cr.mlr_status)} hover:${statusColor(cr.mlr_status)}`}>{cr.mlr_status}</Badge>
              </div>
              <div className="text-sm text-slate-700 border-l-2 border-slate-200 pl-3 py-1 my-3">
                <div className="text-[10px] uppercase tracking-[0.1em] font-semibold text-slate-500 mb-1">Claims</div>
                {cr.claims || "—"}
              </div>
              <div className="text-xs text-slate-500 flex items-center gap-1.5 mb-3">
                <Clock className="h-3 w-3" /> Created {new Date(cr.created_at).toLocaleString()}
              </div>
              {tab === "Pending" && (
                <>
                  <Textarea data-testid={`notes-${cr.id}`} placeholder="Reviewer notes (optional)…"
                    className="text-xs mb-3" rows={2}
                    value={notes[cr.id] || ""}
                    onChange={(e) => setNotes(n => ({ ...n, [cr.id]: e.target.value }))} />
                  <div className="flex gap-2">
                    <Button onClick={() => review(cr.id, "Approved")} className="flex-1 bg-emerald-700 hover:bg-emerald-800 gap-1.5" data-testid={`approve-${cr.id}`}>
                      <Check className="h-4 w-4" /> Approve
                    </Button>
                    <Button onClick={() => review(cr.id, "Rejected")} variant="outline" className="flex-1 text-red-700 border-red-200 hover:bg-red-50 gap-1.5" data-testid={`reject-${cr.id}`}>
                      <X className="h-4 w-4" /> Reject
                    </Button>
                  </div>
                </>
              )}
              {cr.reviewer_notes && (
                <div className="text-xs text-slate-600 mt-3 p-2 bg-slate-50 rounded border border-slate-200">
                  <span className="font-semibold text-slate-700">Notes:</span> {cr.reviewer_notes}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
