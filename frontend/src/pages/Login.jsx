import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { CircleDot, AlertCircle } from "lucide-react";
import { toast } from "sonner";

const DEMO = [
  { label: "Admin", email: "admin@pharmasignal.io", password: "Admin@2026" },
  { label: "Trader", email: "trader@pharmasignal.io", password: "Trader@2026" },
  { label: "Analyst", email: "analyst@pharmasignal.io", password: "Analyst@2026" },
  { label: "Vendor", email: "vendor@pulsepoint.com", password: "Vendor@2026" },
];

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const from = loc.state?.from || "/dashboard";

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await login(email, password);
      toast.success("Welcome back");
      nav(from, { replace: true });
    } catch (e) {
      const d = e.response?.data?.detail;
      setErr(typeof d === "string" ? d : "Invalid credentials");
    } finally { setBusy(false); }
  };

  const quickLogin = (d) => {
    setEmail(d.email);
    setPassword(d.password);
  };

  return (
    <div className="min-h-screen flex bg-slate-50" data-testid="login-page">
      <div className="hidden lg:flex flex-1 bg-blue-900 text-white p-12 flex-col justify-between bg-grid-slate">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-sm bg-white/10 flex items-center justify-center border border-white/20">
            <CircleDot className="h-5 w-5 text-white" strokeWidth={2.5} />
          </div>
          <div>
            <div className="font-heading font-bold text-lg tracking-tight">PharmaSignal</div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-blue-200">DSP · Intelligence</div>
          </div>
        </div>
        <div className="max-w-md">
          <div className="text-[10px] uppercase tracking-[0.2em] text-blue-200 font-semibold mb-3">Built for senior pharma</div>
          <h1 className="font-heading text-4xl font-bold leading-tight tracking-tight">
            Buy the best verified healthcare outcome per dollar.
          </h1>
          <p className="mt-4 text-blue-100 leading-relaxed text-sm">
            Connect HCP and DTC audience strategy, PMP supply quality, data-cost transparency, GA4 engagement, verified reach, and Rx lift into one decisioning layer.
          </p>
        </div>
        <div className="text-[10px] uppercase tracking-[0.15em] text-blue-200">© 2026 PharmaSignal DSP</div>
      </div>

      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <div className="h-7 w-7 rounded-sm bg-blue-900 flex items-center justify-center">
              <CircleDot className="h-4 w-4 text-white" strokeWidth={2.5} />
            </div>
            <div className="font-heading font-bold text-slate-900">PharmaSignal</div>
          </div>

          <div className="text-[10px] uppercase tracking-[0.15em] font-semibold text-slate-500 mb-2">Sign in</div>
          <h2 className="font-heading text-3xl font-bold tracking-tight text-slate-900 mb-1">Welcome back</h2>
          <p className="text-sm text-slate-500 mb-8">Use your team credentials, or try a demo role below.</p>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Email</Label>
              <Input data-testid="login-email" type="email" required autoComplete="username"
                value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1.5" placeholder="you@pharma.co" />
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Password</Label>
              <Input data-testid="login-password" type="password" required autoComplete="current-password"
                value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1.5" />
            </div>
            {err && (
              <div className="flex items-start gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md p-3" data-testid="login-error">
                <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <span>{err}</span>
              </div>
            )}
            <Button type="submit" disabled={busy} data-testid="login-submit"
              className="w-full bg-blue-900 hover:bg-blue-950 h-11">
              {busy ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <div className="mt-8 border-t border-slate-200 pt-6">
            <div className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500 mb-3">Demo accounts</div>
            <div className="grid grid-cols-2 gap-2">
              {DEMO.map(d => (
                <button key={d.label} type="button" onClick={() => quickLogin(d)} data-testid={`demo-${d.label}`}
                  className="text-left text-xs border border-slate-200 hover:border-blue-700 hover:bg-blue-50 rounded-md p-2.5 transition-colors">
                  <div className="font-semibold text-slate-900">{d.label}</div>
                  <div className="text-slate-500 font-mono truncate">{d.email}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
