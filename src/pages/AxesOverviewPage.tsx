import { Layout } from "@/components/Layout";
import { AxisCard } from "@/components/AxisCard";
import { AXES } from "@/lib/axes";

export function AxesOverviewPage() {
  return (
    <Layout
      title="All Axes"
      subtitle="Seven independent neurological decision-support modules."
    >
      <div className="rounded-2xl border bg-gradient-card p-6 shadow-soft">
        <h2 className="text-xl font-semibold tracking-tight">Choose an axis to start</h2>
        <p className="mt-1 text-sm text-muted-foreground max-w-2xl">
          Each axis is a standalone module: input modality, model, explainability output and
          downloadable report. Pick the axis matching your data.
        </p>
      </div>
      <div className="mt-6 grid sm:grid-cols-2 xl:grid-cols-3 gap-5">
        {AXES.map((a) => (
          <AxisCard key={a.id} axis={a} />
        ))}
      </div>
    </Layout>
  );
}
