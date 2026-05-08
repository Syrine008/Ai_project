import { Link } from "@tanstack/react-router";
import { ArrowUpRight } from "lucide-react";
import type { CaseRecord } from "@/lib/mockApi";
import { cn } from "@/lib/utils";
import { getAxisById } from "@/lib/axes";

const statusStyle: Record<CaseRecord["status"], string> = {
  completed: "bg-teal/15 text-teal-foreground border-teal/30",
  in_progress: "bg-lavender/20 text-lavender-foreground border-lavender/40",
  queued: "bg-muted text-muted-foreground border-border",
};

export function RecentCasesTable({ cases }: { cases: CaseRecord[] }) {
  return (
    <div className="overflow-hidden rounded-xl border bg-card">
      <table className="w-full text-sm">
        <thead className="bg-muted/60 text-xs uppercase tracking-wider text-muted-foreground">
          <tr>
            <th className="text-left px-4 py-3">Case</th>
            <th className="text-left px-4 py-3">Patient</th>
            <th className="text-left px-4 py-3">Axis</th>
            <th className="text-left px-4 py-3">Result</th>
            <th className="text-left px-4 py-3">Confidence</th>
            <th className="text-left px-4 py-3">Status</th>
            <th className="px-2 py-3" />
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => {
            const axis = getAxisById(c.axisId);
            return (
              <tr key={c.id} className="border-t hover:bg-accent/30 transition-colors">
                <td className="px-4 py-3 font-mono text-xs">{c.id}</td>
                <td className="px-4 py-3">{c.patient}</td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-1.5">
                    <axis.icon className="h-3.5 w-3.5 text-bluegray" />
                    {c.axisTitle}
                  </span>
                </td>
                <td className="px-4 py-3 text-muted-foreground">{c.topResult}</td>
                <td className="px-4 py-3 tabular-nums">
                  {c.confidence > 0 ? `${(c.confidence * 100).toFixed(0)}%` : "—"}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      "px-2 py-0.5 rounded-full text-xs border capitalize",
                      statusStyle[c.status],
                    )}
                  >
                    {c.status.replace("_", " ")}
                  </span>
                </td>
                <td className="px-2 py-3">
                  <Link
                    to={`/axes/${axis.slug}`}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-accent"
                    aria-label="Open axis"
                  >
                    <ArrowUpRight className="h-4 w-4" />
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
