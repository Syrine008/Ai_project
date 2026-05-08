import { Play, Pause } from "lucide-react";
import { useState } from "react";
import type { TimelineMarker } from "@/lib/mockApi";
import { cn } from "@/lib/utils";

const sevColor = (s: TimelineMarker["severity"]) =>
  s === "high"
    ? "bg-destructive/80"
    : s === "moderate"
      ? "bg-[oklch(0.78_0.16_70)]"
      : "bg-teal";

export function VideoInsightPanel({ markers }: { markers: TimelineMarker[] }) {
  const [playing, setPlaying] = useState(false);
  const total = Math.max(...markers.map((m) => m.t)) + 5;
  return (
    <div className="rounded-xl border bg-card overflow-hidden shadow-soft">
      {/* Stylized "video" surface */}
      <div className="relative aspect-video bg-[oklch(0.18_0.03_255)] grid place-items-center">
        <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_30%_40%,oklch(0.72_0.10_200/0.4),transparent_50%),radial-gradient(circle_at_70%_60%,oklch(0.78_0.07_295/0.35),transparent_50%)]" />
        <svg viewBox="0 0 200 120" className="relative w-2/3 opacity-80">
          {/* simple stick figure */}
          <circle cx="100" cy="25" r="9" fill="oklch(0.85 0.02 240)" />
          <line x1="100" y1="34" x2="100" y2="72" stroke="oklch(0.85 0.02 240)" strokeWidth="2" />
          <line x1="100" y1="45" x2="80" y2="62" stroke="oklch(0.78 0.16 70)" strokeWidth="2" />
          <line x1="100" y1="45" x2="120" y2="62" stroke="oklch(0.85 0.02 240)" strokeWidth="2" />
          <line x1="100" y1="72" x2="86" y2="100" stroke="oklch(0.85 0.02 240)" strokeWidth="2" />
          <line x1="100" y1="72" x2="114" y2="100" stroke="oklch(0.85 0.02 240)" strokeWidth="2" />
        </svg>
        <button
          onClick={() => setPlaying((p) => !p)}
          className="absolute bottom-3 left-3 h-9 w-9 grid place-items-center rounded-full bg-white/90 text-primary shadow-soft hover:scale-105 transition"
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 ml-0.5" />}
        </button>
        <div className="absolute bottom-3 right-3 text-[10px] text-white/70 tabular-nums">
          00:00 / 00:{Math.round(total).toString().padStart(2, "0")}
        </div>
      </div>

      {/* Timeline */}
      <div className="p-4">
        <div className="text-xs font-medium mb-2 text-muted-foreground uppercase tracking-wider">
          Timeline markers
        </div>
        <div className="relative h-2 rounded-full bg-muted">
          {markers.map((m, i) => (
            <div
              key={i}
              className={cn(
                "absolute -top-1 h-4 w-1.5 rounded-sm",
                sevColor(m.severity),
              )}
              style={{ left: `${(m.t / total) * 100}%` }}
              title={`${m.t}s — ${m.label}`}
            />
          ))}
        </div>
        <ul className="mt-4 space-y-2">
          {markers.map((m, i) => (
            <li key={i} className="flex items-center gap-3 text-sm">
              <span className={cn("h-2 w-2 rounded-full", sevColor(m.severity))} />
              <span className="tabular-nums text-muted-foreground w-12">
                {m.t.toFixed(1)}s
              </span>
              <span>{m.label}</span>
              <span className="ml-auto text-xs text-muted-foreground capitalize">
                {m.severity}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
