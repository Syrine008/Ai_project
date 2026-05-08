/**
 * Stylized brain-scan with synthetic heatmap overlay.
 * Pure SVG — no real medical imaging required for the demo.
 */
export function ExplainabilityViewer({
  variant = "axial",
  hotspots = 4,
}: {
  variant?: "axial" | "sagittal";
  hotspots?: number;
}) {
  const points = Array.from({ length: hotspots }, (_, i) => ({
    cx: 100 + Math.cos((i / hotspots) * Math.PI * 2) * 35 + (i % 2 ? 10 : -10),
    cy: 100 + Math.sin((i / hotspots) * Math.PI * 2) * 30 + (i % 3 ? -6 : 6),
    r: 18 + (i % 3) * 6,
    o: 0.55 - i * 0.07,
  }));

  return (
    <div className="relative aspect-square w-full max-w-md mx-auto rounded-xl border bg-[oklch(0.12_0.02_255)] overflow-hidden shadow-soft">
      <svg viewBox="0 0 200 200" className="w-full h-full">
        <defs>
          <radialGradient id="brainGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="oklch(0.55 0.04 250)" />
            <stop offset="60%" stopColor="oklch(0.30 0.03 250)" />
            <stop offset="100%" stopColor="oklch(0.16 0.02 255)" />
          </radialGradient>
          <radialGradient id="hot" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="oklch(0.78 0.18 30)" stopOpacity="0.95" />
            <stop offset="60%" stopColor="oklch(0.72 0.16 60)" stopOpacity="0.5" />
            <stop offset="100%" stopColor="oklch(0.72 0.10 200)" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Skull silhouette */}
        {variant === "axial" ? (
          <ellipse cx="100" cy="100" rx="78" ry="62" fill="url(#brainGrad)" />
        ) : (
          <path
            d="M40 100 Q40 30 110 30 Q175 30 170 95 Q168 145 120 165 Q70 175 50 145 Q35 125 40 100 Z"
            fill="url(#brainGrad)"
          />
        )}

        {/* Sulci lines */}
        {Array.from({ length: 7 }).map((_, i) => (
          <path
            key={i}
            d={`M ${30 + i * 5} ${60 + i * 8} Q 100 ${50 + (i % 2) * 30} ${170 - i * 5} ${70 + i * 7}`}
            fill="none"
            stroke="oklch(0.65 0.04 250 / 0.25)"
            strokeWidth="0.6"
          />
        ))}

        {/* Hotspots */}
        {points.map((p, i) => (
          <circle
            key={i}
            cx={p.cx}
            cy={p.cy}
            r={p.r}
            fill="url(#hot)"
            opacity={p.o}
            className="animate-pulse-soft"
            style={{ animationDelay: `${i * 0.4}s` }}
          />
        ))}

        {/* Crosshair */}
        <line x1="0" y1="100" x2="200" y2="100" stroke="oklch(0.72 0.10 200 / 0.25)" strokeWidth="0.4" strokeDasharray="2 3" />
        <line x1="100" y1="0" x2="100" y2="200" stroke="oklch(0.72 0.10 200 / 0.25)" strokeWidth="0.4" strokeDasharray="2 3" />
      </svg>

      <div className="absolute top-2 left-3 text-[10px] uppercase tracking-wider text-white/60">
        {variant === "axial" ? "Axial · T1w" : "Sagittal · T1w"}
      </div>
      <div className="absolute bottom-2 right-3 flex items-center gap-1.5 text-[10px] text-white/60">
        <span>Low</span>
        <div className="h-1.5 w-20 rounded-full bg-gradient-to-r from-[oklch(0.72_0.10_200)] via-[oklch(0.78_0.16_70)] to-[oklch(0.78_0.18_30)]" />
        <span>High</span>
      </div>
    </div>
  );
}
