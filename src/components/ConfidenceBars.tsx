import type { ConfidenceItem } from "@/lib/mockApi";

export function ConfidenceBars({ items }: { items: ConfidenceItem[] }) {
  return (
    <div className="space-y-3">
      {items.map((c) => (
        <div key={c.label}>
          <div className="flex items-baseline justify-between text-sm">
            <span className="font-medium">{c.label}</span>
            <span className="tabular-nums text-muted-foreground">
              {(c.value * 100).toFixed(1)}%
            </span>
          </div>
          <div className="mt-1.5 h-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-primary to-teal transition-all duration-700"
              style={{ width: `${c.value * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
