import { useState } from "react";
import { Layout } from "@/components/Layout";
import { UploadZone } from "@/components/UploadZone";
import { AnalysisStatusCard } from "@/components/AnalysisStatusCard";
import { RegionTable } from "@/components/RegionTable";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getAxisById } from "@/lib/axes";
import type { AnalysisResult, ConfidenceItem } from "@/lib/mockApi";
import {
  downloadReportPdf,
  saveAnalysisReport,
  type SavedAnalysisReport,
} from "@/lib/reportStore";
import { ArrowRight, FileDown, Maximize2, ShieldAlert, Sparkles } from "lucide-react";
import { toast } from "sonner";

type Stage = "idle" | "running" | "done";

const DISCLAIMER = "Research decision-support output only. This result is not a clinical diagnosis.";
const PD_LABEL = "PD pattern";
const ATYPICAL_LABEL = "Atypical parkinsonian pattern";
const BACKEND_FALLBACK_BASE_URL = "http://127.0.0.1:8000";
const BACKEND_ERROR =
  "Backend connection failed. Make sure Django is running on http://127.0.0.1:8000.";

function formatProbability(value?: number | null) {
  return typeof value === "number" && Number.isFinite(value)
    ? `${(value * 100).toFixed(1)}%`
    : "Not available";
}

function findConfidence(items: ConfidenceItem[] | undefined, label: string) {
  return items?.find((item) => item.label.toLowerCase() === label.toLowerCase())?.value ?? null;
}

function getThreshold(result: AnalysisResult) {
  return result.probabilities?.decisionThreshold ?? result.threshold ?? null;
}

function getGradCamUrl(result: AnalysisResult) {
  return result.gradCamDataUrl || result.gradCam?.imageDataUrl || null;
}

async function runAxis2BackendAnalysis(file: File): Promise<AnalysisResult> {
  const baseUrl =
    (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ||
    BACKEND_FALLBACK_BASE_URL;
  const url = `${baseUrl.replace(/\/$/, "")}/api/axis2-parkinson-atypical/analyze/`;
  const formData = new FormData();
  formData.append("file", file);
  formData.append("metadata", JSON.stringify({ demo: true }));

  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new Error(BACKEND_ERROR);
  }

  if (!response.ok) {
    throw new Error(BACKEND_ERROR);
  }

  const data = (await response.json()) as AnalysisResult;
  return {
    ...data,
    axisId: data.axisId || "axis2-parkinson-atypical",
    caseId: data.caseId || `AXIS2-${Date.now()}`,
    generatedAt: data.generatedAt || new Date().toISOString(),
    disclaimer: data.disclaimer || DISCLAIMER,
    confidence: Array.isArray(data.confidence) ? data.confidence : [],
  };
}

function buildSavedAxis2Report(
  result: AnalysisResult,
  axisTitle: string,
  uploadedExamName?: string,
): SavedAnalysisReport {
  const generatedAt = result.generatedAt || new Date().toISOString();
  const caseId = result.caseId || `AXIS2-${Date.now()}`;
  const payload = {
    ...result,
    axisId: "axis2-parkinson-atypical" as const,
    caseId,
    generatedAt,
  };

  return {
    caseId,
    axisId: "axis2-parkinson-atypical",
    axisTitle,
    patientId: result.patientId || null,
    prediction: result.predictedClass || "Result unavailable",
    probabilities: result.probabilities,
    uploadedExamName,
    generatedAt,
    pdfExportedAt: new Date().toISOString(),
    pdfFilename: `${caseId}-axis2-gradcam-report.pdf`,
    gradCamAvailable: Boolean(getGradCamUrl(result)),
    payload,
  };
}

function Axis2ResultPanel({
  result,
  axisTitle,
  uploadedExamName,
}: {
  result: AnalysisResult;
  axisTitle: string;
  uploadedExamName?: string;
}) {
  const [explainabilityOpen, setExplainabilityOpen] = useState(false);
  const probabilityPD =
    findConfidence(result.confidence, PD_LABEL) ?? result.probabilities?.probability_PD ?? null;
  const probabilityAtypical =
    findConfidence(result.confidence, ATYPICAL_LABEL) ??
    result.probabilities?.probability_atypical ??
    null;
  const threshold = getThreshold(result);
  const gradCamUrl = getGradCamUrl(result);
  const hasRegions = Array.isArray(result.regions) && result.regions.length > 0;
  const modelStatus =
    typeof result.modelLoaded === "boolean"
      ? result.modelLoaded
        ? "Loaded"
        : "Not loaded"
      : "Not reported";

  const handleExportPdf = () => {
    const report = buildSavedAxis2Report(result, axisTitle, uploadedExamName);
    try {
      saveAnalysisReport(report);
    } catch (error) {
      toast.error("Could not save report", {
        description: error instanceof Error ? error.message : "Browser storage rejected the report.",
      });
      return;
    }

    const opened = downloadReportPdf(report);
    if (opened) {
      toast.success("PDF export opened", { description: "The report was also saved to Reports." });
    } else {
      toast.error("Could not open PDF export", {
        description: "Allow pop-ups for this site and try again.",
      });
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <Card className="p-6 bg-gradient-card shadow-elegant">
        <div className="flex items-start gap-4 flex-wrap">
          <div className="min-w-0 flex-1">
            <div className="text-[11px] uppercase tracking-wider text-bluegray">
              AI-detected pattern
            </div>
            <h2 className="mt-1 text-xl font-semibold tracking-tight text-balance">
              {result.predictedClass || "Result unavailable"}
            </h2>
            {result.summary && (
              <p className="mt-2 text-sm text-muted-foreground max-w-2xl leading-relaxed">
                {result.summary}
              </p>
            )}
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3">
          <div className="rounded-lg border bg-card/60 p-3">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
              Top confidence
            </div>
            <div className="text-lg font-semibold mt-0.5">
              {formatProbability(result.topConfidence)}
            </div>
          </div>
          <div className="rounded-lg border bg-card/60 p-3">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
              {PD_LABEL}
            </div>
            <div className="text-lg font-semibold mt-0.5">
              {formatProbability(probabilityPD)}
            </div>
          </div>
          <div className="rounded-lg border bg-card/60 p-3">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
              {ATYPICAL_LABEL}
            </div>
            <div className="text-lg font-semibold mt-0.5">
              {formatProbability(probabilityAtypical)}
            </div>
          </div>
          <div className="rounded-lg border bg-card/60 p-3">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
              Threshold
            </div>
            <div className="text-lg font-semibold mt-0.5">
              {typeof threshold === "number" ? threshold.toFixed(2) : "Not reported"}
            </div>
          </div>
          <div className="rounded-lg border bg-card/60 p-3">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
              Model status
            </div>
            <div className="text-lg font-semibold mt-0.5">{modelStatus}</div>
          </div>
        </div>

        {result.confidence.length > 0 && (
          <div className="mt-5 rounded-lg border bg-card/60 p-3">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-3">
              Confidence array
            </div>
            <div className="space-y-2">
              {result.confidence.map((item) => (
                <div key={item.label} className="grid grid-cols-[minmax(0,1fr)_auto] gap-3 items-center">
                  <div className="min-w-0">
                    <div className="flex items-center justify-between gap-3 text-xs">
                      <span className="truncate">{item.label}</span>
                      <span className="tabular-nums text-muted-foreground">
                        {formatProbability(item.value)}
                      </span>
                    </div>
                    <div className="mt-1.5 h-1.5 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-teal to-primary"
                        style={{ width: `${Math.max(0, Math.min(100, item.value * 100))}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-6 flex items-start gap-2 rounded-lg border border-lavender/40 bg-lavender/10 px-3 py-2.5 text-xs text-foreground/80">
          <ShieldAlert className="h-4 w-4 text-lavender-foreground shrink-0 mt-0.5" />
          <span>{result.disclaimer || DISCLAIMER}</span>
        </div>
      </Card>

      <Card className="p-5 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-sm font-semibold">Grad-CAM explainability preview</div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Heatmap highlights image regions that influenced the CNN prediction.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {gradCamUrl && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => setExplainabilityOpen(true)}
              >
                <Maximize2 className="h-4 w-4" />
                Expand
              </Button>
            )}
            <Button type="button" variant="outline" size="sm" className="gap-1.5" onClick={handleExportPdf}>
              <FileDown className="h-4 w-4" />
              Export PDF
            </Button>
          </div>
        </div>

        {gradCamUrl ? (
          <div className="rounded-xl border bg-card overflow-hidden">
            <img
              src={gradCamUrl}
              alt="Grad-CAM heatmap preview"
              className="w-full h-auto object-contain max-h-[520px]"
            />
          </div>
        ) : !hasRegions ? (
          <div className="rounded-lg border bg-muted/30 p-6 text-sm text-muted-foreground">
            Explainability output is not available for this case yet.
          </div>
        ) : null}

        {hasRegions && (
          <div className="space-y-2">
            <div className="text-xs font-semibold text-muted-foreground">
              Backend region output
            </div>
            <RegionTable regions={result.regions!} />
          </div>
        )}

        {result.warnings && result.warnings.length > 0 && (
          <div className="rounded-lg border bg-card/60 p-3 text-xs text-muted-foreground space-y-1">
            {result.warnings.map((warning, index) => (
              <div key={`${warning}-${index}`}>{warning}</div>
            ))}
          </div>
        )}

        <Dialog open={explainabilityOpen} onOpenChange={setExplainabilityOpen}>
          <DialogContent className="max-h-[94vh] w-[96vw] max-w-6xl overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Grad-CAM explainability preview</DialogTitle>
              <DialogDescription>
                Heatmap highlights image regions that influenced the CNN prediction.
              </DialogDescription>
            </DialogHeader>
            {gradCamUrl && (
              <div className="rounded-lg border bg-card overflow-hidden">
                <img
                  src={gradCamUrl}
                  alt="Expanded Grad-CAM heatmap preview"
                  className="w-full h-auto object-contain max-h-[76vh]"
                />
              </div>
            )}
            {hasRegions && (
              <div className="space-y-2">
                <div className="text-xs font-semibold text-muted-foreground">
                  Backend region output
                </div>
                <RegionTable regions={result.regions!} />
              </div>
            )}
          </DialogContent>
        </Dialog>
      </Card>
    </div>
  );
}

export function Axis2ParkinsonAtypicalPage() {
  const axis = getAxisById("axis2-parkinson-atypical");
  const Icon = axis.icon;
  const [file, setFile] = useState<File | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    if (!file) {
      toast.error("Please upload an MRI file first.");
      return;
    }

    setStage("running");
    setResult(null);
    setError(null);
    try {
      const response = await runAxis2BackendAnalysis(file);
      setResult(response);
      setStage("done");
      toast.success("Analysis complete", { description: response.predictedClass });
    } catch (caught) {
      setStage("idle");
      const message = caught instanceof Error ? caught.message : BACKEND_ERROR;
      setError(message);
      toast.error(message);
    }
  };

  return (
    <Layout title={`Axis ${axis.number} · ${axis.title}`} subtitle={axis.purpose}>
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
              <span className="px-2 py-0.5 rounded-full bg-accent/60">
                {axis.acceptedFormats}
              </span>
              <span className="px-2 py-0.5 rounded-full bg-accent/60 font-mono">
                {axis.endpoint}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
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
            <div className="text-sm font-semibold mb-3">2. Run analysis</div>
            <Button
              onClick={handleRun}
              disabled={stage === "running"}
              className="w-full gap-2"
              size="lg"
            >
              <Sparkles className="h-4 w-4" />
              Generate AI insight
              <ArrowRight className="h-4 w-4 ml-auto" />
            </Button>
          </Card>
        </div>

        <div className="lg:col-span-2 space-y-6">
          {stage === "idle" && !result && (
            <Card className="p-10 text-center bg-gradient-card border-dashed">
              <Icon className="h-10 w-10 mx-auto text-bluegray" />
              <div className="mt-3 font-medium">No analysis yet</div>
              <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
                Upload an MRI file to generate the AI pattern estimate and Grad-CAM preview.
              </p>
            </Card>
          )}

          {error && (
            <Card className="p-5 border-destructive/40 bg-destructive/5 text-sm text-destructive">
              {error}
            </Card>
          )}

          {stage === "running" && (
            <AnalysisStatusCard stage="MRI preprocessing → model inference → explainability" />
          )}

          {result && (
            <Axis2ResultPanel
              result={result}
              axisTitle={`A${axis.number} ${axis.title}`}
              uploadedExamName={file?.name}
            />
          )}
        </div>
      </div>
    </Layout>
  );
}
