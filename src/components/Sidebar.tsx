import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  LayoutGrid,
  FileText,
  History,
  Settings,
  Brain,
} from "lucide-react";
import { AXES } from "@/lib/axes";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/axes", label: "All Axes", icon: LayoutGrid },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/cases", label: "Case History", icon: History },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

export function Sidebar() {
  const path = useRouterState({ select: (s) => s.location.pathname });
  return (
    <aside className="hidden lg:flex w-64 shrink-0 flex-col border-r bg-sidebar text-sidebar-foreground">
      <Link to="/" className="flex items-center gap-2 px-6 h-16 border-b">
        <div className="h-9 w-9 rounded-xl bg-gradient-hero shadow-glow grid place-items-center">
          <Brain className="h-5 w-5 text-white" />
        </div>
        <div className="leading-tight">
          <div className="font-semibold tracking-tight">brAIn</div>
          <div className="text-[11px] text-muted-foreground">Decision support</div>
        </div>
      </Link>

      <nav className="p-3 space-y-1">
        {NAV.map((n) => {
          const active = path === n.to;
          return (
            <Link
              key={n.to}
              to={n.to}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                  : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
              )}
            >
              <n.icon className="h-4 w-4" />
              {n.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-3 mt-2">
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground px-3 mb-2">
          Axes
        </div>
        <div className="space-y-0.5 max-h-[50vh] overflow-y-auto pr-1">
          {AXES.map((a) => {
            const to = `/axes/${a.slug}`;
            const active = path === to;
            return (
              <Link
                key={a.id}
                to={to}
                className={cn(
                  "flex items-center gap-3 px-3 py-1.5 rounded-md text-xs transition-colors",
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                    : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
                )}
              >
                <a.icon className="h-3.5 w-3.5" />
                <span className="truncate">
                  <span className="text-bluegray mr-1">A{a.number}</span>
                  {a.shortTitle}
                </span>
              </Link>
            );
          })}
        </div>
      </div>

      <div className="mt-auto p-4 border-t text-[11px] text-muted-foreground">
        <div className="rounded-lg bg-accent/40 p-3 leading-relaxed">
          <span className="font-medium text-foreground">Decision-support only.</span>{" "}
          Outputs are interpretation aids, not standalone diagnoses.
        </div>
      </div>
    </aside>
  );
}
