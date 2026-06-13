import { useEffect, useState } from "react";
import { api, fmtMoney, fmtPct } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";

export default function DataCost() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/data-cost").then(r => setRows(r.data)); }, []);

  const totals = rows.reduce((acc, r) => ({
    total: acc.total + r.total_spend,
    data: acc.data + r.data_fees,
    plat: acc.plat + r.platform_fees,
    work: acc.work + r.working_media,
  }), { total: 0, data: 0, plat: 0, work: 0 });

  const wmPct = totals.total ? (totals.work / totals.total) * 100 : 0;

  return (
    <div data-testid="data-cost-page">
      <PageHeader
        kicker="Cost Transparency"
        title="Data Cost & Working Media"
        description="How much budget actually becomes working media — versus data fees, platform fees, and other non-media drag."
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white border border-slate-200 rounded-md p-4">
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Total Spend</div>
          <div className="metric-num text-2xl text-slate-900 mt-2">{fmtMoney(totals.total)}</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-md p-4">
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Working Media</div>
          <div className="metric-num text-2xl text-emerald-700 mt-2">{fmtMoney(totals.work)}</div>
          <div className="text-xs text-slate-500 font-mono mt-1">{fmtPct(wmPct)} of spend</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-md p-4">
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Data Fees</div>
          <div className="metric-num text-2xl text-amber-700 mt-2">{fmtMoney(totals.data)}</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-md p-4">
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Platform Fees</div>
          <div className="metric-num text-2xl text-slate-700 mt-2">{fmtMoney(totals.plat)}</div>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-md p-5 mb-6">
        <h3 className="font-heading font-semibold text-slate-900 mb-4">Spend Composition by Channel</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={rows} stackOffset="expand">
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="channel" tick={{ fontSize: 11, fill: "#64748b" }} />
            <YAxis tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} tick={{ fontSize: 11, fill: "#64748b" }} />
            <Tooltip formatter={(v) => fmtMoney(v)} contentStyle={{ fontSize: 12 }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="working_media" stackId="a" fill="#059669" name="Working Media" />
            <Bar dataKey="data_fees" stackId="a" fill="#d97706" name="Data Fees" />
            <Bar dataKey="platform_fees" stackId="a" fill="#94a3b8" name="Platform Fees" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
        <table className="w-full text-sm" data-testid="data-cost-table">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr className="text-[10px] uppercase tracking-[0.1em] text-slate-500">
              <th className="text-left font-semibold py-2.5 px-4">Line Item</th>
              <th className="text-right font-semibold py-2.5 px-3">Total Spend</th>
              <th className="text-right font-semibold py-2.5 px-3">Working Media</th>
              <th className="text-right font-semibold py-2.5 px-3">Data Fees</th>
              <th className="text-right font-semibold py-2.5 px-3">Platform Fees</th>
              <th className="text-right font-semibold py-2.5 px-3">WM %</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-3 px-4 font-medium text-slate-900">{r.line_item}</td>
                <td className="py-3 px-3 text-right mono-num">{fmtMoney(r.total_spend)}</td>
                <td className="py-3 px-3 text-right mono-num text-emerald-700">{fmtMoney(r.working_media)}</td>
                <td className="py-3 px-3 text-right mono-num text-amber-700">{fmtMoney(r.data_fees)}</td>
                <td className="py-3 px-3 text-right mono-num">{fmtMoney(r.platform_fees)}</td>
                <td className={`py-3 px-3 text-right mono-num font-medium ${r.working_media_pct < 60 ? "text-amber-700" : "text-emerald-700"}`}>{r.working_media_pct.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
