import { useState } from "react";
import { Layout } from "@/components/Layout";
import { UploadZone } from "@/components/UploadZone";
import { MetadataForm, type PatientMeta } from "@/components/MetadataForm";
import { AnalysisStatusCard } from "@/components/AnalysisStatusCard";
import { ResultCard } from "@/components/ResultCard";
import { ReportExportPanel } from "@/components/ReportExportPanel";
import { ExplainabilityViewer } from "@/components/ExplainabilityViewer";
import { RegionTable } from "@/components/RegionTable";
// import { SignalChart } from "@/components/SignalChart"; // hidden for medical-focused demo (restore if needed)
import { VideoInsightPanel } from "@/components/VideoInsightPanel";
import { NetworkGraph } from "@/components/NetworkGraph";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { runAnalysis, type AnalysisResult } from "@/lib/mockApi";
import type { AxisDef } from "@/lib/axes";
import { Sparkles, ArrowRight } from "lucide-react";
// import { FlaskConical } from "lucide-react"; // used by commented “Try demo input” button
import { toast } from "sonner";

type Stage = "idle" | "running" | "done";

export function AxisPageTemplate({ axis }: { axis: AxisDef }) {
  const [file, setFile] = useState<File | null>(null);
  const [analyzePairFile, setAnalyzePairFile] = useState<File | null>(null);
  const [meta, setMeta] = useState<PatientMeta>({ id: "", age: "", sex: "", notes: "", email: "" });
  const [stage, setStage] = useState<Stage>("idle");
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const Icon = axis.icon;
  const anomalyScore = typeof result?.anomalyScore === "number" ? result.anomalyScore : null;
  const anomalyThreshold = typeof result?.threshold === "number" ? result.threshold : null;
  const showAnomalyPanel =
    result?.axisId === "axis5-functional-connectivity" &&
    anomalyScore !== null &&
    anomalyThreshold !== null;
  const anomalyRatio =
    showAnomalyPanel && anomalyThreshold > 0
      ? anomalyScore / anomalyThreshold
      : null;
  const anomalyPercent = anomalyRatio !== null ? Math.min(100, anomalyRatio * 100) : 0;
  const anomalyStatus = result?.isAnomaly ? "Atypical pattern detected" : "Normal brain pattern";
  const frames = result?.nFrames ?? 16;
  const hw = result?.hw ?? 64;

  const handleRun = async (demo = false) => {
    if (!demo && !file) {
      toast.error("Please upload a file first.");
      return;
    }
    const nm = file?.name.toLowerCase() ?? "";
    const needsAnalyzeSidecar =
      axis.id === "axis4-brain-aging" &&
      !demo &&
      (nm.endsWith(".hdr") || nm.endsWith(".img")) &&
      !nm.endsWith(".zip");
    if (needsAnalyzeSidecar && !analyzePairFile) {
      toast.error(
        'Analyze MRI needs both parts: add the matching file in "Analyze pair" (.hdr + .img), or upload one .zip containing both.',
      );
      return;
    }
    setStage("running");
    setResult(null);
    try {
      const r = await runAnalysis(
        {
          axisId: axis.id,
          fileName: file?.name ?? "demo-input",
          patient: {
            id: meta.id || undefined,
            age: meta.age ? Number(meta.age) : undefined,
            sex: (meta.sex as "M" | "F" | "Other") || undefined,
            notes: meta.notes,
            email: meta.email.trim() || undefined,
          },
        },
        {
          file: demo ? null : file,
          demo,
          analyzePairFile: demo ? null : analyzePairFile,
        },
      );
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
              onFile={(f) => {
                setFile(f);
                if (!f) setAnalyzePairFile(null);
              }}
            />
            {axis.id === "axis4-brain-aging" && (
              <div className="mt-4 pt-4 border-t border-border">
                <div className="text-xs font-semibold mb-2 text-muted-foreground">
                  Analyze 7.5 pair (optional)
                </div>
                <p className="text-[11px] text-muted-foreground mb-2 leading-relaxed">
                  If your scan is two files (.hdr + .img): upload one above and the other here — order does not matter. Or zip both as{" "}
                  <span className="font-mono">basename.hdr</span> +{" "}
                  <span className="font-mono">basename.img</span> and upload the .zip once.
                </p>
                <UploadZone
                  accept=".hdr,.img,.HDR,.IMG"
                  hint=".hdr or .img (second half of Analyze pair)"
                  onFile={setAnalyzePairFile}
                />
              </div>
            )}
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
            {/* Demo / dev-only — uncomment for mock walkthrough + backend URL hint
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
              {import.meta.env.VITE_API_BASE_URL ? (
                <>
                  Backend: <span className="font-mono">{String(import.meta.env.VITE_API_BASE_URL)}</span>
                  <span className="font-mono ml-1">{axis.endpoint}</span>
                </>
              ) : (
                <>
                  Mock mode. Set <span className="font-mono">VITE_API_BASE_URL</span> for Django (
                  <span className="font-mono">{axis.endpoint}</span>).
                </>
              )}
            </p>
            */}
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

              {showAnomalyPanel && (
                <Card className="p-5 space-y-4">
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div>
                      <div className="text-sm font-semibold">Anomaly score</div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Mean squared reconstruction error across {frames} frames x {hw}x{hw}.
                      </p>
                    </div>
                    <span
                      className={
                        result?.isAnomaly
                          ? "px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/15 text-red-600"
                          : "px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-600"
                      }
                    >
                      {anomalyStatus}
                    </span>
                  </div>

                  <div className="grid gap-4 md:grid-cols-[1.1fr_0.9fr]">
                    <div>
                      <div className="text-xs text-muted-foreground">
                        Anomaly score: {anomalyScore?.toFixed(6)} | Threshold:{" "}
                        {anomalyThreshold?.toFixed(6)}
                      </div>
                      <div className="mt-2 h-2 w-full rounded-full bg-muted overflow-hidden">
                        <div
                          className={result?.isAnomaly ? "h-full bg-red-500" : "h-full bg-emerald-500"}
                          style={{ width: `${anomalyPercent}%` }}
                        />
                      </div>
                      <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-muted-foreground">
                        <span>
                          Score/threshold: {anomalyRatio ? `${anomalyRatio.toFixed(2)}x` : "n/a"}
                        </span>
                        {typeof result.percentileOfNormal === "number" && (
                          <span>Percentile: {result.percentileOfNormal.toFixed(1)}</span>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">
                        Reconstruction error map
                      </div>
                      {result.heatmapB64 ? (
                        <img
                          src={`data:image/png;base64,${result.heatmapB64}`}
                          alt="Reconstruction error heatmap"
                          className="w-full rounded-lg border"
                        />
                      ) : (
                        <div className="rounded-lg border bg-muted/30 p-6 text-xs text-muted-foreground">
                          Heatmap not available for this run.
                        </div>
                      )}
                      <div className="mt-2 text-[11px] text-muted-foreground">
                        Brighter pixels indicate higher deviation from the learned healthy baseline.
                      </div>
                    </div>
                  </div>
                </Card>
              )}

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
                    {axis.id === "axis4-brain-aging" && result.gradCamDataUrl ? (
                      <div className="rounded-xl border bg-card overflow-hidden">
                        <img
                          src={result.gradCamDataUrl}
                          alt="Grad-CAM overlay on input slice"
                          className="w-full h-auto object-contain max-h-[320px]"
                        />
                        <div className="px-3 py-2 text-[10px] text-muted-foreground border-t">
                          Grad-CAM (EfficientNet-B0) — saliency on the preprocessed slice
                        </div>
                      </div>
                    ) : (
                      <ExplainabilityViewer
                        variant={axis.id === "axis2-parkinson-atypical" ? "sagittal" : "axial"}
                        hotspots={Math.min(6, result.regions.length)}
                      />
                    )}
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

              {/* Medical-focused demo: synthetic signal chart hidden for axes that return placeholder waveforms
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
              */}

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

              <ReportExportPanel
                result={result}
                axisId={axis.id}
                axisTitle={axis.title}
                patientEmail={meta.email}
                patient={{
                  id: meta.id || undefined,
                  age: meta.age ? Number(meta.age) : undefined,
                  sex: (meta.sex as "M" | "F" | "Other") || undefined,
                }}
              />
            </>
          )}
        </div>
      </div>
    </Layout>
  );
}
