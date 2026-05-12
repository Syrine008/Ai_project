import { Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { useEffect, useState } from "react";

export function AnalysisStatusCard({ stage }: { stage: string }) {
  const [pct, setPct] = useState(8);
  useEffect(() => {
    const id = setInterval(
      () => setPct((p) => (p < 92 ? p + Math.random() * 6 : p)),
      400,
    );
    return () => clearInterval(id);
  }, []);
  return (
    <div className="rounded-xl border bg-gradient-card p-6 shadow-soft">
      <div className="flex items-center gap-3">
        <Loader2 className="h-5 w-5 animate-spin text-primary" />
        <div>
          <div className="font-medium">Running analysis</div>
          <div className="text-xs text-muted-foreground">{stage}</div>
        </div>
      </div>
      <div className="mt-4">
        <Progress value={pct} />
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-[11px] text-muted-foreground">
        <div className="rounded-md bg-accent/40 px-2 py-1.5">Preprocessing</div>
        <div className="rounded-md bg-accent/40 px-2 py-1.5">Inference</div>
        <div className="rounded-md bg-accent/40 px-2 py-1.5">Explainability</div>
      </div>
    </div>
  );
}
