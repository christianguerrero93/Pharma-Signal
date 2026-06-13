import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  LayoutDashboard, Megaphone, Users, Network, Wallet,
  Activity, TrendingUp, Zap, Sparkles, Building2, Upload, Plus, CircleDot, Radio, FileCheck,
  Repeat, LogOut, ChevronDown,
} from "lucide-react";

const NAV_ALL = [
  { to: "/dashboard", label: "Overview", icon: LayoutDashboard, group: "MONITOR", roles: ["admin","trader","analyst","vendor"] },
  { to: "/campaigns", label: "Campaigns", icon: Megaphone, group: "MONITOR", roles: ["admin","trader","analyst"] },
  { to: "/mlr", label: "MLR Review", icon: FileCheck, group: "MONITOR", roles: ["admin","analyst"] },
  { to: "/audiences", label: "Audience Scorer", icon: Users, group: "INTELLIGENCE", roles: ["admin","trader","analyst"] },
  { to: "/pmp", label: "PMP / Supply", icon: Network, group: "INTELLIGENCE", roles: ["admin","trader","analyst","vendor"] },
  { to: "/data-cost", label: "Data Cost", icon: Wallet, group: "INTELLIGENCE", roles: ["admin","trader","analyst"] },
  { to: "/ga4", label: "GA4 Engagement", icon: Activity, group: "INTELLIGENCE", roles: ["admin","trader","analyst"] },
  { to: "/frequency", label: "Frequency Intel", icon: Repeat, group: "INTELLIGENCE", roles: ["admin","trader","analyst"] },
  { to: "/script-lift", label: "Script Lift", icon: TrendingUp, group: "OUTCOMES", roles: ["admin","trader","analyst"] },
  { to: "/vendors", label: "Vendor Value", icon: Building2, group: "OUTCOMES", roles: ["admin","trader","analyst","vendor"] },
  { to: "/rtb", label: "RTB Simulator", icon: Zap, group: "OPTIMIZE", roles: ["admin","trader","analyst"] },
  { to: "/live", label: "Live Bid Stream", icon: Radio, group: "OPTIMIZE", roles: ["admin","trader","analyst"] },
  { to: "/ai", label: "AI Recommendations", icon: Sparkles, group: "OPTIMIZE", roles: ["admin","trader","analyst"] },
  { to: "/upload", label: "Data Upload", icon: Upload, group: "ADMIN", roles: ["admin","trader"] },
];

const roleLabel = {
  admin: "Admin", trader: "Trader", analyst: "Analyst", vendor: "Vendor",
};
const roleBadge = {
  admin: "bg-blue-100 text-blue-900",
  trader: "bg-indigo-100 text-indigo-900",
  analyst: "bg-slate-100 text-slate-800",
  vendor: "bg-emerald-100 text-emerald-900",
};

function groupBy(items, key) {
  return items.reduce((acc, it) => { (acc[it[key]] = acc[it[key]] || []).push(it); return acc; }, {});
}

export default function Layout() {
  const { user, logout, has } = useAuth();
  const nav = useNavigate();
  const NAV = NAV_ALL.filter(n => n.roles.includes(user?.role));
  const grouped = groupBy(NAV, "group");
  const location = useLocation();
  const current = NAV.find((n) => location.pathname.startsWith(n.to));

  const initials = (user?.name || "?").split(" ").map(w => w[0]).slice(0,2).join("").toUpperCase();

  return (
    <div className="min-h-screen flex bg-slate-50" data-testid="app-layout">
      <aside className="hidden lg:flex w-64 flex-col bg-white border-r border-slate-200">
        <div className="h-14 flex items-center px-5 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-sm bg-blue-900 flex items-center justify-center">
              <CircleDot className="h-4 w-4 text-white" strokeWidth={2.5} />
            </div>
            <div>
              <div className="font-heading font-bold text-[15px] tracking-tight text-slate-900">PharmaSignal</div>
              <div className="text-[10px] uppercase tracking-[0.15em] text-slate-500 -mt-0.5">DSP · Intelligence</div>
            </div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-5" data-testid="sidebar-nav">
          {Object.entries(grouped).map(([group, items]) => (
            <div key={group}>
              <div className="px-3 mb-1.5 text-[10px] uppercase tracking-[0.15em] font-semibold text-slate-400">{group}</div>
              <div className="space-y-0.5">
                {items.map(({ to, label, icon: Icon }) => (
                  <NavLink key={to} to={to} data-testid={`nav-${to.replace("/", "")}`}
                    className={({ isActive }) =>
                      `flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
                        isActive ? "bg-blue-50 text-blue-900 font-medium" : "text-slate-700 hover:bg-slate-100"
                      }`
                    }>
                    <Icon className="h-4 w-4" strokeWidth={1.8} /> {label}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>
        {has("admin", "trader") && (
          <div className="p-3 border-t border-slate-200">
            <NavLink to="/campaigns/new" data-testid="sidebar-new-campaign"
              className="flex items-center justify-center gap-2 w-full px-3 py-2 text-sm font-medium rounded-md bg-blue-900 text-white hover:bg-blue-950 transition-colors">
              <Plus className="h-4 w-4" /> New Campaign
            </NavLink>
          </div>
        )}
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <span className="text-[10px] uppercase tracking-[0.15em] text-slate-400">PharmaSignal</span>
            <span className="text-slate-300">/</span>
            <h1 className="font-heading text-base font-semibold tracking-tight text-slate-900" data-testid="page-title">
              {current?.label || "Dashboard"}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 text-xs text-slate-500 font-mono">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
              <span>LIVE · Q1 2026</span>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-2 px-2 py-1 rounded-md hover:bg-slate-100 transition-colors" data-testid="user-menu">
                  <div className="h-8 w-8 rounded-full bg-blue-900 text-white flex items-center justify-center text-xs font-semibold">{initials}</div>
                  <div className="hidden md:block text-left">
                    <div className="text-xs font-medium text-slate-900 leading-tight">{user?.name}</div>
                    <div className={`text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded inline-block ${roleBadge[user?.role]}`}>{roleLabel[user?.role]}</div>
                  </div>
                  <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="text-slate-900">{user?.name}</div>
                  <div className="text-xs font-normal text-slate-500 font-mono">{user?.email}</div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => { logout(); nav("/login"); }} data-testid="logout-btn" className="gap-2 text-red-700">
                  <LogOut className="h-4 w-4" /> Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
