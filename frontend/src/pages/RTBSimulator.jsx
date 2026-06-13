import { useState } from "react";
import { api } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { Zap, Play } from "lucide-react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine,
} from "recharts";

const Param = ({ label, value, onChange, min = 0, max = 1, step = 0.01, suffix = "", testid }) => (
  <div className="bg-white border border-slate-200 rounded-md p-4" data-testid={testid}>
    <div className="flex items-baseline justify-between mb-3">
      <span className="text-[10px] uppercase tracking-[0.1em] font-semibold text-slate-600">{label}</span>
      <span className="mono-num text-sm font-medium text-slate-900">{value.toFixed(2)}{suffix}</span>
    </div>
    <Slider value={[value]} min={min} max={max} step={step} onValueChange={(v) => onChange(v[0])} />
  </div>
);

export default function RTBSimulator() {
  const [params, setParams] = useState({
    outcome_probability: 0.65,
    audience_quality_score: 0.78,
    supply_quality_score: 0.72,
    rx_lift_weight: 1.2,
    engagement_quality: 0.68,
    data_cost_multiplier: 1.25,
    base_value: 12,
  });
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);

  const upd = (k, v) => setParams(p => ({ ...p, [k]: v }));

  const run = async () => {
    setRunning(true);
    try {
      const { data } = await api.post("/rtb/simulate", params);
      setResult(data);
    } finally { setRunning(false); }
  };

  return (
    <div data-testid="rtb-simulator-page">
      <PageHeader
        kicker="Bidder Logic"
        title="RTB Bid Simulator"
        description="Tune the parameters of the outcome-aware bidder and visualize bid decisions, win rate, and final CPM."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="lg:col-span-1 space-y-3">
          <Param testid="param-outcome" label="Outcome Probability" value={params.outcome_probability}
            onChange={(v) => upd("outcome_probability", v)} />
          <Param testid="param-audience" label="Audience Quality" value={params.audience_quality_score}
            onChange={(v) => upd("audience_quality_score", v)} />
          <Param testid="param-supply" label="Supply Quality" value={params.supply_quality_score}
            onChange={(v) => upd("supply_quality_score", v)} />
          <Param testid="param-engagement" label="Engagement Quality" value={params.engagement_quality}
            onChange={(v) => upd("engagement_quality", v)} />
          <Param testid="param-rxlift" label="Rx Lift Weight" value={params.rx_lift_weight}
            onChange={(v) => upd("rx_lift_weight", v)} min={0.5} max={2.0} />
          <Param testid="param-datacost" label="Data Cost Multiplier" value={params.data_cost_multiplier}
            onChange={(v) => upd("data_cost_multiplier", v)} min={1.0} max={2.5} />
          <Button onClick={run} disabled={running} data-testid="rtb-run" className="w-full bg-blue-900 hover:bg-blue-950 gap-2">
            <Play className="h-4 w-4" /> {running ? "Simulating…" : "Run Simulation"}
          </Button>
        </div>

        <div className="lg:col-span-2 space-y-4">
          <div className="bg-slate-900 text-slate-100 border border-slate-800 rounded-md p-5 font-mono text-xs leading-relaxed" data-testid="formula-box">
            <div className="text-[10px] uppercase tracking-[0.15em] text-slate-400 font-semibold mb-2">Bid Formula</div>
            <div className="text-emerald-300">bid = outcome_prob × audience_quality × supply_quality × rx_lift_weight × engagement_quality / data_cost × base_value</div>
            <div className="mt-3 text-slate-400">
              = {params.outcome_probability.toFixed(2)} × {params.audience_quality_score.toFixed(2)} × {params.supply_quality_score.toFixed(2)} × {params.rx_lift_weight.toFixed(2)} × {params.engagement_quality.toFixed(2)} / {params.data_cost_multiplier.toFixed(2)} × {params.base_value}
            </div>
          </div>

          {result && (
            <>
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-white border border-slate-200 rounded-md p-4" data-testid="result-bid">
                  <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Final Bid CPM</div>
                  <div className="metric-num text-3xl text-slate-900 mt-2">${result.final_bid_cpm}</div>
                </div>
                <div className="bg-white border border-slate-200 rounded-md p-4" data-testid="result-decision">
                  <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Decision</div>
                  <div className={`metric-num text-2xl mt-2 ${result.decision === "BID" ? "text-emerald-700" : result.decision === "LOW_BID" ? "text-amber-700" : "text-red-600"}`}>
                    {result.decision}
                  </div>
                </div>
                <div className="bg-white border border-slate-200 rounded-md p-4" data-testid="result-winrate">
                  <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Win Rate</div>
                  <div className="metric-num text-3xl text-slate-900 mt-2">{result.win_rate_pct}%</div>
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-md p-5" data-testid="result-chart">
                <h3 className="font-heading font-semibold text-slate-900 mb-3">Simulated Bid Stream (24 requests)</h3>
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={result.stream}>
                    <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="t" tick={{ fontSize: 11, fill: "#64748b" }} />
                    <YAxis tick={{ fontSize: 11, fill: "#64748b" }} />
                    <Tooltip contentStyle={{ fontSize: 12 }} />
                    <ReferenceLine y={1.5} stroke="#059669" strokeDasharray="4 4" label={{ value: "BID floor", fontSize: 10, fill: "#059669" }} />
                    <ReferenceLine y={0.5} stroke="#d97706" strokeDasharray="4 4" label={{ value: "LOW_BID floor", fontSize: 10, fill: "#d97706" }} />
                    <Line type="monotone" dataKey="bid" stroke="#1e3a8a" strokeWidth={2} dot={{ r: 2 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {!result && (
            <div className="bg-white border border-dashed border-slate-300 rounded-md p-12 text-center text-slate-500">
              <Zap className="h-8 w-8 mx-auto mb-3 text-slate-300" strokeWidth={1.5} />
              <div className="text-sm">Tune parameters on the left and run the simulator to see live bid decisioning.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
