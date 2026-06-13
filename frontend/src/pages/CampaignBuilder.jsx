import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Checkbox } from "@/components/ui/checkbox";

const CHANNELS = ["Display", "OLV", "CTV", "Audio", "Native", "EHR/POC", "Endemic"];

export default function CampaignBuilder() {
  const nav = useNavigate();
  const [form, setForm] = useState({
    name: "", brand: "", indication: "", campaign_type: "DTC",
    budget: 500000, flight_start: "2026-02-01", flight_end: "2026-04-30",
    npi_target_count: 0, specialty: "", diagnosis: "", data_partner: "Crossix",
    outcome_kpi: "Script Lift", frequency_cap: 5, channels: ["Display", "OLV"],
  });
  const [submitting, setSubmitting] = useState(false);

  const upd = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const toggleChannel = (ch) => setForm(f => ({
    ...f, channels: f.channels.includes(ch) ? f.channels.filter(c => c !== ch) : [...f.channels, ch]
  }));

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/campaigns", { ...form, budget: parseFloat(form.budget), npi_target_count: parseInt(form.npi_target_count || 0) });
      toast.success("Campaign created");
      nav("/campaigns");
    } catch (err) {
      toast.error("Failed to create campaign");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div data-testid="campaign-builder-page">
      <PageHeader kicker="Activation" title="New Campaign"
        description="Pharma-native fields for HCP/DTC activation with MLR, NPI targeting, and outcome KPIs." />

      <form onSubmit={submit} className="max-w-4xl bg-white border border-slate-200 rounded-md p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <Label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Campaign Name</Label>
            <Input data-testid="cb-name" value={form.name} required onChange={(e) => upd("name", e.target.value)} className="mt-1.5" placeholder="Veltrexa Q2 DTC" />
          </div>
          <div>
            <Label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Brand</Label>
            <Input data-testid="cb-brand" value={form.brand} required onChange={(e) => upd("brand", e.target.value)} className="mt-1.5" placeholder="Veltrexa" />
          </div>
          <div>
            <Label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Indication</Label>
            <Input data-testid="cb-indication" value={form.indication} required onChange={(e) => upd("indication", e.target.value)} className="mt-1.5" placeholder="Type 2 Diabetes" />
          </div>
          <div>
            <Label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Campaign Type</Label>
            <Select value={form.campaign_type} onValueChange={(v) => upd("campaign_type", v)}>
              <SelectTrigger data-testid="cb-type" className="mt-1.5"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="DTC">DTC — Patient / Consumer</SelectItem>
                <SelectItem value="HCP">HCP — Provider</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Budget (USD)</Label>
            <Input data-testid="cb-budget" type="number" value={form.budget} onChange={(e) => upd("budget", e.target.value)} className="mt-1.5 font-mono" />
          </div>
          <div>
            <Label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Outcome KPI</Label>
            <Select value={form.outcome_kpi} onValueChange={(v) => upd("outcome_kpi", v)}>
              <SelectTrigger data-testid="cb-kpi" className="mt-1.5"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="Script Lift">Script Lift</SelectItem>
                <SelectItem value="Verified Reach">Verified Reach</SelectItem>
                <SelectItem value="Quality Visits">Quality Visits</SelectItem>
                <SelectItem value="NPS">NPS / New Starts</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Flight Start</Label>
            <Input data-testid="cb-start" type="date" value={form.flight_start} onChange={(e) => upd("flight_start", e.target.value)} className="mt-1.5" />
          </div>
          <div>
            <Label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Flight End</Label>
            <Input data-testid="cb-end" type="date" value={form.flight_end} onChange={(e) => upd("flight_end", e.target.value)} className="mt-1.5" />
          </div>
          {form.campaign_type === "HCP" ? (
            <>
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wide text-slate-600">NPI Target Count</Label>
                <Input data-testid="cb-npi" type="number" value={form.npi_target_count} onChange={(e) => upd("npi_target_count", e.target.value)} className="mt-1.5 font-mono" />
              </div>
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Specialty</Label>
                <Input data-testid="cb-specialty" value={form.specialty} onChange={(e) => upd("specialty", e.target.value)} className="mt-1.5" placeholder="Endocrinology" />
              </div>
            </>
          ) : (
            <div className="md:col-span-2">
              <Label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Diagnosis / Audience Segment</Label>
              <Input data-testid="cb-diag" value={form.diagnosis} onChange={(e) => upd("diagnosis", e.target.value)} className="mt-1.5" placeholder="Newly Diagnosed T2D 40-65" />
            </div>
          )}
          <div>
            <Label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Data Partner</Label>
            <Select value={form.data_partner} onValueChange={(v) => upd("data_partner", v)}>
              <SelectTrigger data-testid="cb-partner" className="mt-1.5"><SelectValue /></SelectTrigger>
              <SelectContent>
                {["Crossix", "Swoop", "IQVIA", "LiveRamp", "DeepIntent Audiences"].map(p =>
                  <SelectItem key={p} value={p}>{p}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Frequency Cap (per week)</Label>
            <Input data-testid="cb-freq" type="number" value={form.frequency_cap} onChange={(e) => upd("frequency_cap", parseInt(e.target.value || 0))} className="mt-1.5 font-mono" />
          </div>
        </div>

        <div>
          <Label className="text-xs font-semibold uppercase tracking-wide text-slate-600 mb-2 block">Channels</Label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {CHANNELS.map(ch => (
              <label key={ch} className="flex items-center gap-2 text-sm cursor-pointer p-2 border border-slate-200 rounded-md hover:bg-slate-50">
                <Checkbox checked={form.channels.includes(ch)} onCheckedChange={() => toggleChannel(ch)} data-testid={`cb-ch-${ch}`} />
                {ch}
              </label>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between pt-4 border-t border-slate-200">
          <div className="text-xs text-slate-500">
            <span className="font-semibold text-slate-700">MLR Status:</span> Auto-marked Approved (demo)
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={() => nav("/campaigns")}>Cancel</Button>
            <Button type="submit" disabled={submitting} data-testid="cb-submit" className="bg-blue-900 hover:bg-blue-950">
              {submitting ? "Creating…" : "Create Campaign"}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
