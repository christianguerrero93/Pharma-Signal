import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, BarChart, Bar,
} from "recharts";

export default function ScriptLift() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/script-lift").then(r => setRows(r.data)); }, []);

  const latest = rows.length ? rows[rows.length - 1] : null;

  return (
    <div data-testid="script-lift-page">
      <PageHeader
        kicker="Rx Outcomes"
        title="Script Lift — Exposed vs. Control"
        description="Indexed prescription volume of exposed cohort vs. a matched control group over the campaign flight."
      />

      {latest && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white border border-slate-200 rounded-md p-4">
            <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Latest Lift</div>
            <div className="metric-num text-3xl text-emerald-700 mt-2">+{latest.lift_pct}%</div>
            <div className="text-xs text-slate-500 font-mono mt-1">Week {latest.week.replace("W","")}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-md p-4">
            <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Exposed Rx Index</div>
            <div className="metric-num text-3xl text-slate-900 mt-2">{latest.exposed_rx_index}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-md p-4">
            <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Control Rx Index</div>
            <div className="metric-num text-3xl text-slate-500 mt-2">{latest.control_rx_index}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-md p-4">
            <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Weeks Tracked</div>
            <div className="metric-num text-3xl text-slate-900 mt-2">{rows.length}</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white border border-slate-200 rounded-md p-5">
          <h3 className="font-heading font-semibold text-slate-900 mb-4">Exposed vs Control — Rx Index</h3>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={rows}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="week" tick={{ fontSize: 11, fill: "#64748b" }} />
              <YAxis tick={{ fontSize: 11, fill: "#64748b" }} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="exposed_rx_index" name="Exposed" stroke="#059669" strokeWidth={2.4} dot={false} />
              <Line type="monotone" dataKey="control_rx_index" name="Control" stroke="#cbd5e1" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-white border border-slate-200 rounded-md p-5">
          <h3 className="font-heading font-semibold text-slate-900 mb-4">Weekly Lift %</h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={rows}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="week" tick={{ fontSize: 11, fill: "#64748b" }} />
              <YAxis tick={{ fontSize: 11, fill: "#64748b" }} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Bar dataKey="lift_pct" fill="#1e3a8a" radius={[3, 3, 0, 0]} name="Lift %" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
