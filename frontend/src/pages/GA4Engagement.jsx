import { useEffect, useState } from "react";
import { api, fmtNum, fmtPct } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";

export default function GA4Engagement() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/ga4").then(r => setRows(r.data)); }, []);

  return (
    <div data-testid="ga4-page">
      <PageHeader
        kicker="Engagement"
        title="GA4 Engagement Quality"
        description="Engaged sessions, quality visits, and conversion behavior tied back to media exposure."
      />

      <div className="bg-white border border-slate-200 rounded-md p-5 mb-6">
        <h3 className="font-heading font-semibold text-slate-900 mb-4">Sessions vs. Engaged vs. Quality Visits</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={rows}>
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="channel" tick={{ fontSize: 11, fill: "#64748b" }} />
            <YAxis tick={{ fontSize: 11, fill: "#64748b" }} />
            <Tooltip contentStyle={{ fontSize: 12 }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="sessions" name="Sessions" fill="#cbd5e1" radius={[3, 3, 0, 0]} />
            <Bar dataKey="engaged_sessions" name="Engaged" fill="#3b82f6" radius={[3, 3, 0, 0]} />
            <Bar dataKey="quality_visits" name="Quality Visits" fill="#059669" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr className="text-[10px] uppercase tracking-[0.1em] text-slate-500">
              <th className="text-left font-semibold py-2.5 px-4">Channel</th>
              <th className="text-right font-semibold py-2.5 px-3">Sessions</th>
              <th className="text-right font-semibold py-2.5 px-3">Engaged</th>
              <th className="text-right font-semibold py-2.5 px-3">Engagement Rate</th>
              <th className="text-right font-semibold py-2.5 px-3">Quality Visits</th>
              <th className="text-right font-semibold py-2.5 px-3">Avg. Duration (s)</th>
              <th className="text-right font-semibold py-2.5 px-3">Conversions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-3 px-4 font-medium text-slate-900">{r.channel}</td>
                <td className="py-3 px-3 text-right mono-num">{fmtNum(r.sessions)}</td>
                <td className="py-3 px-3 text-right mono-num">{fmtNum(r.engaged_sessions)}</td>
                <td className="py-3 px-3 text-right mono-num">{(r.engagement_rate * 100).toFixed(1)}%</td>
                <td className="py-3 px-3 text-right mono-num text-emerald-700">{fmtNum(r.quality_visits)}</td>
                <td className="py-3 px-3 text-right mono-num">{r.avg_session_duration}</td>
                <td className="py-3 px-3 text-right mono-num font-medium">{fmtNum(r.conversions)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
