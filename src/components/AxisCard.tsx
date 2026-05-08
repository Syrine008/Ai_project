import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import type { AxisDef } from "@/lib/axes";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export function AxisCard({ axis }: { axis: AxisDef }) {
  const Icon = axis.icon;
  return (
    <Card className="group relative overflow-hidden p-6 bg-gradient-card border hover:shadow-elegant transition-all duration-300 hover:-translate-y-1">
      <div
        className={`absolute -top-12 -right-12 h-40 w-40 rounded-full opacity-20 blur-2xl bg-gradient-to-br ${axis.accent}`}
      />
      <div className="flex items-start justify-between gap-4 relative">
        <div
          className={`h-12 w-12 rounded-xl bg-gradient-to-br ${axis.accent} text-white grid place-items-center shadow-soft`}
        >
          <Icon className="h-6 w-6" />
        </div>
        <span className="text-xs font-medium text-bluegray tabular-nums">
          AXIS {String(axis.number).padStart(2, "0")}
        </span>
      </div>

      <h3 className="mt-5 text-lg font-semibold tracking-tight relative">{axis.title}</h3>
      <p className="mt-1.5 text-sm text-muted-foreground leading-relaxed relative">
        {axis.purpose}
      </p>

      <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground relative">
        <span className="px-2 py-0.5 rounded-full bg-accent/60 text-accent-foreground">
          {axis.input}
        </span>
        <span className="truncate">{axis.acceptedFormats}</span>
      </div>

      <div className="mt-5 flex items-center justify-between relative">
        <Button asChild variant="ghost" size="sm" className="gap-1.5 -ml-2">
          <Link to={`/axes/${axis.slug}`}>
            Run analysis
            <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </Button>
      </div>
    </Card>
  );
}
