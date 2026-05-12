import { ShieldAlert } from "lucide-react";
import type { AnalysisResult } from "@/lib/mockApi";
import { ConfidenceBars } from "./ConfidenceBars";

export function ResultCard({ result }: { result: AnalysisResult }) {
  return (
    <div className="rounded-xl border bg-gradient-card p-6 shadow-elegant animate-fade-in">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-bluegray">
            AI-detected pattern
          </div>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-balance">
            {result.predictedClass}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground max-w-2xl leading-relaxed">
            {result.summary}
          </p>
        </div>
        <div className="text-right">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
            Top confidence
          </div>
          <div className="text-3xl font-semibold tabular-nums bg-gradient-to-br from-primary to-teal bg-clip-text text-transparent">
            {(result.topConfidence * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      {result.metrics && result.metrics.length > 0 && (
        <div className="mt-5 grid grid-cols-2 sm:grid-cols-3 gap-3">
          {result.metrics.map((m) => (
            <div key={m.label} className="rounded-lg border bg-card/60 p-3">
              <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
                {m.label}
              </div>
              <div className="text-lg font-semibold mt-0.5">{m.value}</div>
              {m.hint && (
                <div className="text-[11px] text-muted-foreground mt-0.5">{m.hint}</div>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="mt-6">
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">
          Confidence distribution
        </div>
        <ConfidenceBars items={result.confidence} />
      </div>

      <div className="mt-6 flex items-start gap-2 rounded-lg border border-lavender/40 bg-lavender/10 px-3 py-2.5 text-xs text-foreground/80">
        <ShieldAlert className="h-4 w-4 text-lavender-foreground shrink-0 mt-0.5" />
        <span>{result.disclaimer}</span>
      </div>
    </div>
  );
}
