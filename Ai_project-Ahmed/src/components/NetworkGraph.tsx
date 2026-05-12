import type { AnalysisResult } from "@/lib/mockApi";

/**
 * Lightweight network graph (no extra deps).
 * Renders nodes on a circle and weighted edges between them.
 */
export function NetworkGraph({
  network,
}: {
  network: NonNullable<AnalysisResult["network"]>;
}) {
  const { nodes, edges } = network;
  const cx = 150;
  const cy = 150;
  const r = 110;
  const positions = Object.fromEntries(
    nodes.map((n, i) => {
      const a = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
      return [n, { x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r }];
    }),
  );

  return (
    <div className="rounded-xl border bg-card p-4 shadow-soft">
      <svg viewBox="0 0 300 300" className="w-full h-auto">
        {edges.map((e, i) => {
          const a = positions[e.from];
          const b = positions[e.to];
          if (!a || !b) return null;
          return (
            <line
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={
                e.weight > 0.7
                  ? "oklch(0.55 0.18 30)"
                  : e.weight > 0.5
                    ? "oklch(0.72 0.10 200)"
                    : "oklch(0.65 0.03 250)"
              }
              strokeOpacity={0.55 + e.weight * 0.4}
              strokeWidth={1 + e.weight * 3}
            />
          );
        })}
        {nodes.map((n) => {
          const p = positions[n];
          return (
            <g key={n}>
              <circle
                cx={p.x}
                cy={p.y}
                r={18}
                fill="var(--primary)"
                className="drop-shadow"
              />
              <text
                x={p.x}
                y={p.y + 4}
                textAnchor="middle"
                fontSize="10"
                fill="var(--primary-foreground)"
                fontWeight="600"
              >
                {n}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="mt-2 text-xs text-muted-foreground text-center">
        Network nodes represent canonical resting-state networks.
      </div>
    </div>
  );
}
