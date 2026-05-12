import type { RegionContribution } from "@/lib/mockApi";

export function RegionTable({ regions }: { regions: RegionContribution[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border scrollbar-blue">
      <table className="w-full min-w-[520px] text-sm">
        <thead className="bg-muted/60 text-xs uppercase tracking-wider text-muted-foreground">
          <tr>
            <th className="text-left px-4 py-2.5">Region</th>
            <th className="text-left px-4 py-2.5">Side</th>
            <th className="text-left px-4 py-2.5">Contribution</th>
            <th className="text-left px-4 py-2.5">Note</th>
          </tr>
        </thead>
        <tbody>
          {regions.map((r, i) => (
            <tr key={i} className="border-t hover:bg-accent/30">
              <td className="px-4 py-2.5 font-medium">{r.region}</td>
              <td className="px-4 py-2.5 text-muted-foreground">{r.side ?? "—"}</td>
              <td className="px-4 py-2.5">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-24 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-teal to-primary"
                      style={{ width: `${r.contribution * 100}%` }}
                    />
                  </div>
                  <span className="text-xs tabular-nums text-muted-foreground">
                    {(r.contribution * 100).toFixed(0)}%
                  </span>
                </div>
              </td>
              <td className="px-4 py-2.5 text-muted-foreground">{r.note ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
