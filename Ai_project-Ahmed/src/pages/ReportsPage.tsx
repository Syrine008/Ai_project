import { Layout } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Download, FileText, Search } from "lucide-react";
import { MOCK_CASES } from "@/lib/mockApi";
import { getAxisById } from "@/lib/axes";

export function ReportsPage() {
  const completed = MOCK_CASES.filter((c) => c.status === "completed");
  return (
    <Layout title="Reports" subtitle="All decision-support reports across axes.">
      <div className="flex flex-wrap gap-3 items-center mb-5">
        <div className="relative flex-1 min-w-64">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input className="pl-9" placeholder="Search by case ID, patient or axis…" />
        </div>
        <Button variant="outline" className="gap-1.5">
          <Download className="h-4 w-4" /> Export all
        </Button>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {completed.map((c) => {
          const axis = getAxisById(c.axisId);
          return (
            <Card key={c.id} className="p-5 hover:shadow-elegant transition-shadow">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-[11px] uppercase tracking-wider text-bluegray">
                    {axis.shortTitle}
                  </div>
                  <div className="font-semibold mt-0.5">{c.topResult}</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {c.patient} · {c.date}
                  </div>
                </div>
                <div className="h-10 w-10 rounded-lg bg-primary/10 grid place-items-center text-primary">
                  <FileText className="h-5 w-5" />
                </div>
              </div>
              <div className="mt-4 flex items-center justify-between">
                <span className="font-mono text-xs">{c.id}</span>
                <span className="text-xs tabular-nums text-muted-foreground">
                  {(c.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <Button variant="outline" className="w-full mt-4 gap-1.5">
                <Download className="h-4 w-4" /> Download report
              </Button>
            </Card>
          );
        })}
      </div>
    </Layout>
  );
}
