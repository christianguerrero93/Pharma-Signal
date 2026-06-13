import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export default function ProtectedRoute({ children, roles }) {
  const { user, loading, has } = useAuth();
  const loc = useLocation();

  if (loading) return <div className="min-h-screen flex items-center justify-center text-slate-500">Loading…</div>;
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  if (roles && !has(...roles)) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8" data-testid="forbidden">
        <div className="max-w-md text-center">
          <div className="text-[10px] uppercase tracking-[0.15em] text-slate-500 font-semibold mb-2">403 · Forbidden</div>
          <h1 className="font-heading text-2xl font-bold text-slate-900">You don't have access to this page</h1>
          <p className="text-sm text-slate-500 mt-2">This area is restricted to: {roles.join(", ")}.</p>
        </div>
      </div>
    );
  }
  return children;
}
