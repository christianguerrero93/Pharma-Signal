import { useEffect, useRef, useState } from "react";
import { API } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Play, Square, Radio } from "lucide-react";

const decisionColor = (d) =>
  d === "BID" ? "text-emerald-700" :
  d === "LOW_BID" ? "text-amber-700" : "text-red-600";

export default function LiveStream() {
  const [events, setEvents] = useState([]);
  const [running, setRunning] = useState(false);
  const ctrlRef = useRef(null);

  const start = async () => {
    setRunning(true);
    setEvents([]);
    const ac = new AbortController();
    ctrlRef.current = ac;
    try {
      const resp = await fetch(`${API}/live/bid-stream`, { signal: ac.signal });
      if (!resp.body) throw new Error("no body");
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n\n");
        buf = lines.pop() || "";
        for (const line of lines) {
          if (!line.startsWith("data:")) continue;
          const payload = line.slice(5).trim();
          if (payload === "[DONE]") { setRunning(false); return; }
          try {
            const ev = JSON.parse(payload);
            setEvents(e => [ev, ...e].slice(0, 100));
          } catch {}
        }
      }
    } catch (e) {
      // aborted or network
    } finally {
      setRunning(false);
    }
  };

  const stop = () => { ctrlRef.current?.abort(); setRunning(false); };

  useEffect(() => () => ctrlRef.current?.abort(), []);

  const win = events.filter(e => e.decision === "BID").length;
  const total = events.length;
  const winRate = total ? Math.round((win / total) * 100) : 0;
  const avgBid = total ? (events.reduce((s, e) => s + e.bid_cpm, 0) / total).toFixed(2) : "0.00";

  return (
    <div data-testid="live-stream-page">
      <PageHeader
        kicker="OpenRTB (Simulated)"
        title="Live Bid Stream"
        description="Watch the outcome-aware bidder respond to incoming bid requests in real time. In production this consumes OpenRTB feeds from PubMatic / Magnite / OpenX / Index."
        actions={
          running ? (
            <Button onClick={stop} variant="outline" className="gap-2 text-red-700 border-red-200" data-testid="live-stop">
              <Square className="h-4 w-4 fill-current" /> Stop
            </Button>
          ) : (
            <Button onClick={start} className="bg-blue-900 hover:bg-blue-950 gap-2" data-testid="live-start">
              <Play className="h-4 w-4" /> Start Stream
            </Button>
          )
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white border border-slate-200 rounded-md p-4">
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500 flex items-center gap-1.5">
            <Radio className={`h-3 w-3 ${running ? "text-emerald-600 animate-pulse" : "text-slate-300"}`} />
            Status
          </div>
          <div className={`metric-num text-2xl mt-2 ${running ? "text-emerald-700" : "text-slate-400"}`}>{running ? "LIVE" : "IDLE"}</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-md p-4">
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Bid Requests</div>
          <div className="metric-num text-2xl text-slate-900 mt-2 mono-num">{total}</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-md p-4">
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Win Rate</div>
          <div className="metric-num text-2xl text-slate-900 mt-2 mono-num">{winRate}%</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-md p-4">
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">Avg Bid CPM</div>
          <div className="metric-num text-2xl text-slate-900 mt-2 mono-num">${avgBid}</div>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
        <div className="px-4 py-2.5 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="text-[10px] uppercase tracking-[0.1em] font-semibold text-slate-500">Most Recent Bid Requests</div>
          {running && <span className="text-xs font-mono text-emerald-600 flex items-center gap-1">●&nbsp;streaming</span>}
        </div>
        <div className="max-h-[520px] overflow-y-auto">
          <table className="w-full text-xs" data-testid="live-table">
            <thead className="bg-white border-b border-slate-200 sticky top-0">
              <tr className="text-[10px] uppercase tracking-[0.1em] text-slate-500">
                <th className="text-left font-semibold py-2 px-3">t</th>
                <th className="text-left font-semibold py-2 px-3">Vendor</th>
                <th className="text-left font-semibold py-2 px-3">Channel</th>
                <th className="text-left font-semibold py-2 px-3">Audience</th>
                <th className="text-right font-semibold py-2 px-3">Outcome P</th>
                <th className="text-right font-semibold py-2 px-3">Match</th>
                <th className="text-right font-semibold py-2 px-3">Bid CPM</th>
                <th className="text-center font-semibold py-2 px-3">Decision</th>
              </tr>
            </thead>
            <tbody>
              {events.length === 0 && (
                <tr><td colSpan={8} className="text-center text-slate-400 py-12">Click <span className="font-semibold text-slate-700">Start Stream</span> to begin receiving bid requests…</td></tr>
              )}
              {events.map((e, i) => (
                <tr key={`${e.t}-${i}`} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                  <td className="py-1.5 px-3 mono-num text-slate-500">{e.t}</td>
                  <td className="py-1.5 px-3 text-slate-900">{e.vendor}</td>
                  <td className="py-1.5 px-3 text-slate-700">{e.channel}</td>
                  <td className="py-1.5 px-3 text-slate-700">{e.audience} <span className="text-slate-400">({e.audience_type})</span></td>
                  <td className="py-1.5 px-3 mono-num text-right">{e.outcome_prob}</td>
                  <td className="py-1.5 px-3 mono-num text-right">{(e.match_rate * 100).toFixed(0)}%</td>
                  <td className="py-1.5 px-3 mono-num text-right font-medium">${e.bid_cpm.toFixed(2)}</td>
                  <td className={`py-1.5 px-3 text-center font-mono font-semibold ${decisionColor(e.decision)}`}>{e.decision}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
