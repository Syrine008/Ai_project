import { useState } from "react";
import { Layout } from "@/components/Layout";
import { UploadZone } from "@/components/UploadZone";
import { MetadataForm, type PatientMeta } from "@/components/MetadataForm";
import { AnalysisStatusCard } from "@/components/AnalysisStatusCard";
import { ResultCard } from "@/components/ResultCard";
import { ReportExportPanel } from "@/components/ReportExportPanel";
import { ExplainabilityViewer } from "@/components/ExplainabilityViewer";
import { RegionTable } from "@/components/RegionTable";
import { SignalChart } from "@/components/SignalChart";
import { VideoInsightPanel } from "@/components/VideoInsightPanel";
import { NetworkGraph } from "@/components/NetworkGraph";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { runAnalysis, type AnalysisResult } from "@/lib/mockApi";
import type { AxisDef } from "@/lib/axes";
import { Sparkles, FlaskConical, ArrowRight } from "lucide-react";
import { toast } from "sonner";

type Stage = "idle" | "running" | "done";

export function AxisPageTemplate({ axis }: { axis: AxisDef }) {
  const [file, setFile] = useState<File | null>(null);
  const [meta, setMeta] = useState<PatientMeta>({ id: "", age: "", sex: "", notes: "" });
  const [stage, setStage] = useState<Stage>("idle");
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const Icon = axis.icon;

  const handleRun = async (demo = false) => {
    if (!demo && !file) {
      toast.error("Please upload a file first.");
      return;
    }
    setStage("running");
    setResult(null);
    try {
      const r = await runAnalysis({
        axisId: axis.id,
        fileName: file?.name ?? "demo-input",
        patient: {
          id: meta.id || undefined,
          age: meta.age ? Number(meta.age) : undefined,
          sex: (meta.sex as "M" | "F" | "Other") || undefined,
          notes: meta.notes,
        },
      });
      setResult(r);
      setStage("done");
      toast.success("Analysis complete", { description: r.predictedClass });
    } catch {
      setStage("idle");
      toast.error("Analysis failed");
    }
  };

  return (
    <Layout
      title={`Axis ${axis.number} · ${axis.title}`}
      subtitle={axis.purpose}
    >
      {/* Hero */}
      <div className="rounded-2xl border bg-gradient-card p-6 lg:p-8 shadow-soft">
        <div className="flex items-start gap-5">
          <div className={`h-14 w-14 rounded-2xl bg-gradient-to-br ${axis.accent} grid place-items-center shadow-glow text-white`}>
            <Icon className="h-7 w-7" />
          </div>
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-wider text-bluegray">
              Axis {String(axis.number).padStart(2, "0")} · {axis.input}
            </div>
            <h2 className="mt-0.5 text-2xl font-semibold tracking-tight text-balance">
              {axis.title}
            </h2>
            <p className="mt-2 text-sm text-muted-foreground max-w-3xl leading-relaxed">
              {axis.description}
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span className="px-2 py-0.5 rounded-full bg-accent/60">{axis.acceptedFormats}</span>
              <span className="px-2 py-0.5 rounded-full bg-accent/60 font-mono">{axis.endpoint}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: input */}
        <div className="lg:col-span-1 space-y-6">
          <Card className="p-5">
            <div className="text-sm font-semibold mb-3">1. Upload data</div>
            <UploadZone
              accept={axis.acceptedFormats}
              hint={`${axis.input} · ${axis.acceptedFormats}`}
              onFile={setFile}
            />
          </Card>

          <Card className="p-5">
            <div className="text-sm font-semibold mb-3">2. Patient metadata</div>
            <MetadataForm value={meta} onChange={setMeta} />
          </Card>

          <Card className="p-5">
            <div className="text-sm font-semibold mb-3">3. Run</div>
            <Button
              onClick={() => handleRun(false)}
              disabled={stage === "running"}
              className="w-full gap-2"
              size="lg"
            >
              <Sparkles className="h-4 w-4" />
              Run analysis
              <ArrowRight className="h-4 w-4 ml-auto" />
            </Button>
            <Button
              variant="outline"
              onClick={() => handleRun(true)}
              disabled={stage === "running"}
              className="w-full mt-2 gap-2"
            >
              <FlaskConical className="h-4 w-4" />
              Try demo input
            </Button>
            <p className="text-[11px] text-muted-foreground mt-3 leading-relaxed">
              Mock inference for demo. Production wiring: <span className="font-mono">{axis.endpoint}</span>
            </p>
          </Card>
        </div>

        {/* Right: results / explainability */}
        <div className="lg:col-span-2 space-y-6">
          {stage === "idle" && !result && (
            <Card className="p-10 text-center bg-gradient-card border-dashed">
              <Icon className="h-10 w-10 mx-auto text-bluegray" />
              <div className="mt-3 font-medium">No analysis yet</div>
              <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
                Upload a {axis.input} file or use demo input to see prediction, confidence and explainability outputs.
              </p>
            </Card>
          )}

          {stage === "running" && (
            <AnalysisStatusCard stage={`${axis.input} preprocessing → model inference → explainability`} />
          )}

          {result && (
            <>
              <ResultCard result={result} />

              {/* Axis-specific explainability */}
              {result.regions && (
                <Card className="p-5 space-y-4">
                  <div>
                    <div className="text-sm font-semibold">Explainability — region contributions</div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Heatmap overlay highlights regions most informative to the AI-detected pattern.
                    </p>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <ExplainabilityViewer
                      variant={axis.id === "axis2-parkinson-atypical" ? "sagittal" : "axial"}
                      hotspots={Math.min(6, result.regions.length)}
                    />
                    <RegionTable regions={result.regions} />
                  </div>
                </Card>
              )}

              {result.network && (
                <Card className="p-5 space-y-4">
                  <div>
                    <div className="text-sm font-semibold">Functional connectivity network</div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Edge weight reflects estimated connectivity strength between resting-state networks.
                    </p>
                  </div>
                  <NetworkGraph network={result.network} />
                </Card>
              )}

              {result.signal && (
                <Card className="p-5 space-y-4">
                  <div>
                    <div className="text-sm font-semibold">Signal explainability</div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Highlighted windows correspond to detected instability segments.
                    </p>
                  </div>
                  <SignalChart data={result.signal} markers={result.timeline} />
                </Card>
              )}

              {axis.input === "Video" && result.timeline && (
                <Card className="p-5 space-y-4">
                  <div>
                    <div className="text-sm font-semibold">Video insight panel</div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Timestamped markers indicate detected movement anomalies.
                    </p>
                  </div>
                  <VideoInsightPanel markers={result.timeline} />
                </Card>
              )}

              <ReportExportPanel result={result} />
            </>
          )}
        </div>
      </div>
    </Layout>
  );
}
