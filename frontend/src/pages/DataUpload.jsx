import { useState } from "react";
import { API } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Upload, FileText } from "lucide-react";

const DATASETS = [
  { value: "pmps", label: "PMP / Supply Exports" },
  { value: "audiences", label: "Audience Reports" },
  { value: "ga4", label: "GA4 Engagement" },
  { value: "data_cost", label: "Data Cost / Working Media" },
  { value: "script_lift", label: "Script Lift Reports" },
  { value: "campaigns", label: "Campaign Exports" },
];

export default function DataUpload() {
  const [dataset, setDataset] = useState("pmps");
  const [file, setFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!file) { toast.error("Pick a CSV file first"); return; }
    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const resp = await fetch(`${API}/upload/${dataset}`, { method: "POST", body: fd });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "upload failed");
      toast.success(`Inserted ${data.rows_inserted} rows into ${data.dataset}`);
      setFile(null);
    } catch (e) {
      toast.error(e.message);
    } finally { setSubmitting(false); }
  };

  return (
    <div data-testid="upload-page">
      <PageHeader
        kicker="Ingestion"
        title="Data Upload"
        description="Ingest CSV exports from DeepIntent, PulsePoint, TTD, GA4, Crossix/Swoop, and PMP partners — fueling the intelligence layer."
      />

      <div className="max-w-2xl bg-white border border-slate-200 rounded-md p-6 space-y-5">
        <div>
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-600 mb-1.5 block">Dataset</label>
          <Select value={dataset} onValueChange={setDataset}>
            <SelectTrigger data-testid="upload-dataset"><SelectValue /></SelectTrigger>
            <SelectContent>
              {DATASETS.map(d => <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-600 mb-1.5 block">CSV File</label>
          <label
            data-testid="upload-dropzone"
            className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-slate-300 hover:border-blue-700 rounded-md p-10 text-slate-500 cursor-pointer transition-colors bg-slate-50"
          >
            <Upload className="h-7 w-7 text-slate-400" strokeWidth={1.5} />
            <div className="text-sm">{file ? <span className="text-slate-900 font-medium">{file.name}</span> : "Click or drop a CSV here"}</div>
            <input type="file" accept=".csv" className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </label>
        </div>

        <Button onClick={submit} disabled={submitting || !file} data-testid="upload-submit" className="bg-blue-900 hover:bg-blue-950 gap-2">
          <FileText className="h-4 w-4" /> {submitting ? "Uploading…" : "Ingest CSV"}
        </Button>

        <div className="text-xs text-slate-500 leading-relaxed border-t border-slate-200 pt-4">
          <span className="font-semibold text-slate-700">Tip:</span> Files are parsed row-by-row with header-based column mapping. Numeric columns are auto-coerced. No PHI should ever be uploaded.
        </div>
      </div>
    </div>
  );
}
