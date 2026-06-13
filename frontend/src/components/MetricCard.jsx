import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";

export default function MetricCard({ label, value, sub, delta, deltaType = "neutral", testid, icon: Icon }) {
  const dColor =
    deltaType === "good" ? "text-emerald-600" :
    deltaType === "bad" ? "text-red-600" : "text-slate-500";
  const DIcon = deltaType === "good" ? ArrowUpRight : deltaType === "bad" ? ArrowDownRight : Minus;
  return (
    <div
      className="bg-white border border-slate-200 rounded-md p-5 hover:shadow-sm transition-all"
      data-testid={testid}
    >
      <div className="flex items-start justify-between mb-3">
        <span className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">{label}</span>
        {Icon && <Icon className="h-4 w-4 text-slate-400" strokeWidth={1.8} />}
      </div>
      <div className="metric-num text-3xl text-slate-900">{value}</div>
      <div className="mt-2 flex items-center justify-between">
        {sub && <span className="text-xs text-slate-500 font-mono">{sub}</span>}
        {delta != null && (
          <span className={`inline-flex items-center gap-0.5 text-xs font-medium ${dColor}`}>
            <DIcon className="h-3 w-3" strokeWidth={2.2} />
            {delta}
          </span>
        )}
      </div>
    </div>
  );
}
