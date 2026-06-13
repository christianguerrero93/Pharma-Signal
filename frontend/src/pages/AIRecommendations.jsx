import { useState } from "react";
import { API } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Sparkles, Play, RotateCw } from "lucide-react";

export default function AIRecommendations() {
  const [text, setText] = useState("");
  const [streaming, setStreaming] = useState(false);

  const run = async () => {
    setStreaming(true);
    setText("");
    try {
      const resp = await fetch(`${API}/ai/recommendations`, { method: "POST" });
      if (!resp.ok || !resp.body) throw new Error("stream failed");
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        setText((t) => t + decoder.decode(value, { stream: true }));
      }
    } catch (e) {
      setText((t) => t + `\n[error: ${e.message}]`);
    } finally {
      setStreaming(false);
    }
  };

  return (
    <div data-testid="ai-recommendations-page">
      <PageHeader
        kicker="AI Strategist"
        title="Next-Best-Action"
        description="Claude Sonnet 4.5 reads your supply, audience, and outcome data and produces senior, commercial recommendations."
        actions={
          <Button onClick={run} disabled={streaming} data-testid="ai-run" className="bg-blue-900 hover:bg-blue-950 gap-2">
            {streaming ? <RotateCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {streaming ? "Generating…" : text ? "Re-generate" : "Generate Recommendations"}
          </Button>
        }
      />

      <div className="bg-indigo-50/60 border border-indigo-200 rounded-md p-6" data-testid="ai-output">
        <div className="flex items-center gap-2 mb-4">
          <div className="h-7 w-7 rounded-md bg-indigo-900 flex items-center justify-center">
            <Sparkles className="h-3.5 w-3.5 text-white" strokeWidth={2.2} />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.15em] font-semibold text-indigo-700">Claude Sonnet 4.5</div>
            <div className="text-xs text-slate-500">Streaming narrative · grounded in your live portfolio data</div>
          </div>
        </div>

        {text ? (
          <div className="prose prose-sm max-w-none">
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-800">{text}</pre>
          </div>
        ) : (
          <div className="text-center py-16 text-slate-500">
            <Sparkles className="h-8 w-8 mx-auto mb-3 text-indigo-300" strokeWidth={1.5} />
            <div className="text-sm">Click <span className="font-semibold text-slate-700">Generate Recommendations</span> to stream your next-best-action briefing.</div>
          </div>
        )}
      </div>
    </div>
  );
}
