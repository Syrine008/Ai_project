import { Link } from "@tanstack/react-router";
import { Layout } from "@/components/Layout";
import { AxisCard } from "@/components/AxisCard";
import { RecentCasesTable } from "@/components/RecentCasesTable";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AXES } from "@/lib/axes";
import { MOCK_CASES } from "@/lib/mockApi";
import { ArrowRight, Activity, FileText, FlaskConical, Sparkles } from "lucide-react";

const STATS = [
  { label: "Cases analyzed", value: "1,284", hint: "+24 this week", icon: Activity },
  { label: "Axes available", value: "7", hint: "Across 4 modalities", icon: Sparkles },
  { label: "Reports generated", value: "962", hint: "+18 this week", icon: FileText },
  { label: "Models in production", value: "7", hint: "All explainable", icon: FlaskConical },
];

export function DashboardPage() {
  return (
    <Layout title="Dashboard" subtitle="Decision-support workspace">
      {/* Welcome */}
      <div className="rounded-2xl border bg-gradient-hero text-white p-8 shadow-elegant relative overflow-hidden">
        <div className="absolute -top-20 -right-10 h-72 w-72 rounded-full bg-white/10 blur-3xl" />
        <div className="relative max-w-2xl">
          <div className="text-[11px] uppercase tracking-wider opacity-80">Welcome back</div>
          <h2 className="mt-1 text-2xl md:text-3xl font-semibold tracking-tight text-balance">
            Ready to surface hidden brain dynamics?
          </h2>
          <p className="mt-2 text-sm text-white/80 max-w-xl">
            Pick an axis to start a new analysis or pick up where you left off in your case history.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <Button asChild variant="secondary" className="gap-1.5">
              <Link to="/axes">
                Start new analysis <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="ghost" className="text-white hover:bg-white/15">
              <Link to="/cases">View case history</Link>
            </Button>
          </div>
        </div>
      </div>

      {/* Quick stats */}
      <div className="mt-6 grid grid-cols-2 lg:grid-cols-4 gap-4">
        {STATS.map((s) => (
          <Card key={s.label} className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
                  {s.label}
                </div>
                <div className="mt-1.5 text-2xl font-semibold tabular-nums">{s.value}</div>
                <div className="text-[11px] text-muted-foreground mt-0.5">{s.hint}</div>
              </div>
              <div className="h-9 w-9 rounded-lg bg-primary/10 grid place-items-center text-primary">
                <s.icon className="h-4 w-4" />
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Axes */}
      <section className="mt-10">
        <div className="flex items-end justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold tracking-tight">7 Axes</h3>
            <p className="text-sm text-muted-foreground">Pick an axis to upload data and run analysis.</p>
          </div>
          <Button asChild variant="ghost" size="sm" className="gap-1">
            <Link to="/axes">View all <ArrowRight className="h-3.5 w-3.5" /></Link>
          </Button>
        </div>
        <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-5">
          {AXES.map((a) => (
            <AxisCard key={a.id} axis={a} />
          ))}
        </div>
      </section>

      {/* Recent cases + reports shortcut */}
      <section className="mt-10 grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="flex items-end justify-between mb-3">
            <h3 className="text-lg font-semibold tracking-tight">Recent cases</h3>
            <Button asChild variant="ghost" size="sm" className="gap-1">
              <Link to="/cases">All cases <ArrowRight className="h-3.5 w-3.5" /></Link>
            </Button>
          </div>
          <RecentCasesTable cases={MOCK_CASES.slice(0, 4)} />
        </div>

        <Card className="p-6 bg-gradient-card flex flex-col">
          <div className="text-sm font-semibold">Reports</div>
          <p className="text-xs text-muted-foreground mt-0.5">
            Decision-support reports across all axes. Export, share or print.
          </p>
          <div className="mt-4 space-y-2 text-sm flex-1">
            {MOCK_CASES.filter((c) => c.status === "completed")
              .slice(0, 3)
              .map((c) => (
                <div key={c.id} className="flex items-center gap-2 rounded-lg border bg-card p-2.5">
                  <FileText className="h-4 w-4 text-primary" />
                  <span className="font-mono text-xs">{c.id}</span>
                  <span className="text-muted-foreground text-xs ml-auto">{c.date}</span>
                </div>
              ))}
          </div>
          <Button asChild className="mt-4 w-full">
            <Link to="/reports">Open reports</Link>
          </Button>
        </Card>
      </section>
    </Layout>
  );
}
