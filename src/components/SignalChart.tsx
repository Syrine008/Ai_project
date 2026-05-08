import {
  LineChart,
  Line,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceArea,
} from "recharts";
import type { SignalPoint, TimelineMarker } from "@/lib/mockApi";

export function SignalChart({
  data,
  markers,
}: {
  data: SignalPoint[];
  markers?: TimelineMarker[];
}) {
  return (
    <div className="h-64 w-full rounded-lg border bg-card p-3">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.85 0.02 240 / 0.4)" />
          <XAxis dataKey="t" tick={{ fontSize: 10 }} stroke="var(--muted-foreground)" />
          <YAxis tick={{ fontSize: 10 }} stroke="var(--muted-foreground)" />
          <Tooltip
            contentStyle={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          {markers?.map((m, i) => (
            <ReferenceArea
              key={i}
              x1={Math.max(0, m.t - 4)}
              x2={m.t + 4}
              fill={
                m.severity === "high"
                  ? "oklch(0.78 0.18 30 / 0.18)"
                  : m.severity === "moderate"
                    ? "oklch(0.78 0.16 70 / 0.15)"
                    : "oklch(0.72 0.10 200 / 0.12)"
              }
            />
          ))}
          <Line
            type="monotone"
            dataKey="v"
            stroke="var(--primary)"
            strokeWidth={1.5}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
