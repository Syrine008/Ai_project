import { Link } from "@tanstack/react-router";
import { ThemeToggle } from "./ThemeToggle";

export function Topbar({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="border-b bg-card/95 backdrop-blur sticky top-0 z-30">
      <div className="min-h-16 px-4 sm:px-6 py-3 flex items-center gap-4">
        <div className="min-w-0 flex-1">
          <h1 className="text-base font-semibold tracking-tight">{title}</h1>
          {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
        </div>
        <span className="hidden sm:inline text-xs text-muted-foreground">Research workspace</span>
        {import.meta.env.VITE_API_BASE_URL && (
          <a
            className="text-xs underline whitespace-nowrap"
            href={`${String(import.meta.env.VITE_API_BASE_URL).replace(/\/$/, "")}/admin/login/?next=/`}
            target="_blank"
            rel="noreferrer"
          >
            Sign in
          </a>
        )}
        <ThemeToggle />
      </div>
      <nav
        aria-label="Workspace navigation"
        className="lg:hidden flex gap-5 overflow-x-auto px-4 pb-3 text-sm"
      >
        <Link to="/dashboard">Overview</Link>
        <Link to="/axes">Analyses</Link>
        <Link to="/reports">Reports</Link>
        <Link to="/cases">History</Link>
        <Link to="/settings">Settings</Link>
      </nav>
    </header>
  );
}
