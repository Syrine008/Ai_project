import { useMemo, useState, type ReactNode } from "react";
import { AlertTriangle, Brain, ChevronDown, Info, Sparkles } from "lucide-react";
import { Layout } from "@/components/Layout";
import { ReportExportPanel } from "@/components/ReportExportPanel";
import { UploadZone } from "@/components/UploadZone";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getAxisById } from "@/lib/axes";
import { runAnalysis, type AnalysisResult } from "@/lib/mockApi";
import { saveAnalysisReport, type SavedAnalysisReport } from "@/lib/reportStore";
import { toast } from "sonner";

type Axis1Meta = {
  patientId: string;
  sex: string;
  age: string;
  mmse: string;
  cdr: string;
  notes: string;
};

const pct = (value?: number | null) => (typeof value === "number" && Number.isFinite(value) ? `${Math.round(value * 100)}%` : "Not available");

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">{label}</Label>
      {children}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value?: string | number | string[] }) {
  const shown = Array.isArray(value) ? value.join(", ") : value;
  return (
    <div className="rounded-md border bg-card/60 p-3">
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm font-medium">{shown || "Not available"}</div>
    </div>
  );
}

function buildCognitiveInterpretation(result: AnalysisResult, meta: Axis1Meta): string {
  if (result.predictedClass === "MRI could not be processed") {
    return "Because the MRI could not be processed, the cognitive score cannot be compared with a valid MRI model output.";
  }

  const mmse = meta.mmse ? Number(meta.mmse) : undefined;
  const cdr = meta.cdr ? Number(meta.cdr) : undefined;
  const cognitiveImpairment =
    (typeof mmse === "number" && mmse < 24) || (typeof cdr === "number" && cdr >= 0.5);
  const finalProbability = result.probabilities?.alzheimerProbability ?? result.probabilities?.cnnAlzheimerProbability;
  const decisionThreshold = result.probabilities?.decisionThreshold;
  const alzheimerLike =
    result.predictedClass.toLowerCase().includes("alzheimer-like") ||
    (typeof finalProbability === "number" &&
      typeof decisionThreshold === "number" &&
      finalProbability >= decisionThreshold);

  if (cognitiveImpairment && alzheimerLike) {
    return "The cognitive score and the MRI model output are clinically consistent: the entered score suggests cognitive impairment, and the MRI model detected an Alzheimer-like pattern. MMSE/CDR were not used by the prediction model; they are shown only to support interpretation.";
  }
  if (cognitiveImpairment && !alzheimerLike) {
    return "The cognitive score suggests cognitive impairment, but the MRI model did not detect an Alzheimer-like pattern. This discordance should be reviewed clinically, and the selected MRI series should be verified.";
  }
  if (!cognitiveImpairment && !alzheimerLike) {
    return "The cognitive score and the MRI model output are broadly consistent with a non-demented pattern. This remains a decision-support result and not a standalone diagnosis.";
  }
  return "The MRI model detected an Alzheimer-like pattern while the entered cognitive score does not suggest strong impairment. This may reflect early/subtle MRI changes or a discordant result requiring clinical review.";
}

function buildSavedAxis1Report(
  result: AnalysisResult,
  meta: Axis1Meta,
  uploadedExamName: string,
  cognitiveScoreInterpretation: string | null,
): SavedAnalysisReport {
  return {
    caseId: result.caseId,
    axisId: "axis1-alzheimer-dementia",
    axisTitle: "A1 Alzheimer MRI",
    patientId: meta.patientId || result.patientId || null,
    prediction: result.predictedClass,
    probabilities: {
      alzheimerProbability: result.probabilities?.alzheimerProbability,
      healthyProbability: result.probabilities?.healthyProbability,
      decisionThreshold: result.probabilities?.decisionThreshold,
      confidenceLevel: result.probabilities?.confidenceLevel,
    },
    uploadedExamName: result.uploadedExamName || uploadedExamName,
    generatedAt: result.generatedAt || new Date().toISOString(),
    selectedSeries: result.seriesInfo,
    clinicalMetadata: {
      sex: result.clinicalMetadata?.sex ?? (meta.sex || null),
      age: result.clinicalMetadata?.age ?? (meta.age ? Number(meta.age) : null),
      mmse: result.clinicalMetadata?.mmse ?? (meta.mmse ? Number(meta.mmse) : null),
      cdr: result.clinicalMetadata?.cdr ?? (meta.cdr ? Number(meta.cdr) : null),
      notes: result.clinicalMetadata?.notes ?? (meta.notes || null),
    },
    cognitiveScoreInterpretation,
    mriFeatures: result.mriFeatures,
    gradCamAvailable: Boolean(result.gradCam?.available && result.gradCam.imageDataUrl),
    payload: result,
  };
}

function isSuccessfulAxis1Report(result: AnalysisResult) {
  return (
    result.predictedClass !== "MRI could not be processed" &&
    result.predictedClass !== "MRI processing failed" &&
    result.probabilities?.alzheimerProbability !== undefined &&
    result.probabilities?.healthyProbability !== undefined
  );
}

export function Axis1AlzheimerDementiaPage() {
  const axis = getAxisById("axis1-alzheimer-dementia");
  const [file, setFile] = useState<File | null>(null);
  const [meta, setMeta] = useState<Axis1Meta>({
    patientId: "",
    sex: "",
    age: "",
    mmse: "",
    cdr: "",
    notes: "",
  });
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const reportPatient = useMemo(
    () => ({
      id: meta.patientId || undefined,
      age: meta.age ? Number(meta.age) : undefined,
      sex: (meta.sex as "M" | "F") || undefined,
    }),
    [meta.age, meta.patientId, meta.sex],
  );

  const update = (patch: Partial<Axis1Meta>) => setMeta((current) => ({ ...current, ...patch }));

  const hasClinicalScores = Boolean(meta.mmse || meta.cdr);
  const cognitiveInterpretation = result && hasClinicalScores ? buildCognitiveInterpretation(result, meta) : null;
  const isProcessingFailure = result?.predictedClass === "MRI could not be processed";
  const showGradCam = !isProcessingFailure && result?.gradCam?.available === true && Boolean(result.gradCam.imageDataUrl);
  const showMriFeatures = !isProcessingFailure && Boolean(result?.mriFeatures?.length);
  const showCognitiveInterpretation = !isProcessingFailure && Boolean(cognitiveInterpretation);

  const handleRun = async () => {
    if (!file) {
      toast.error("Please upload the MRI exam first.");
      return;
    }

    setRunning(true);
    setResult(null);
    try {
      const response = await runAnalysis(
        {
          axisId: axis.id,
          fileName: file.name,
          patient: {
            id: meta.patientId || undefined,
            sex: (meta.sex as "M" | "F") || undefined,
            age: meta.age ? Number(meta.age) : undefined,
            mmse: meta.mmse ? Number(meta.mmse) : undefined,
            cdr: meta.cdr ? Number(meta.cdr) : undefined,
            notes: meta.notes || undefined,
          },
        },
        { file, demo: false },
      );
      setResult(response);
      if (isSuccessfulAxis1Report(response)) {
        const interpretation = meta.mmse || meta.cdr ? buildCognitiveInterpretation(response, meta) : null;
        saveAnalysisReport(buildSavedAxis1Report(response, meta, file.name, interpretation));
      }
      toast.success("Analysis complete", { description: response.predictedClass });
    } catch (error) {
      toast.error("Analysis failed", {
        description: error instanceof Error ? error.message : "Please check the uploaded exam.",
      });
    } finally {
      setRunning(false);
    }
  };

  return (
    <Layout
      title="Axis 1 - Alzheimer MRI Pattern Analysis"
      subtitle="Structural MRI decision-support analysis for Alzheimer-like patterns, supported by explainability and cognitive-score correlation."
    >
      <div className="rounded-xl border bg-gradient-card p-6 shadow-soft">
        <div className="flex items-start gap-4">
          <div className="grid h-12 w-12 shrink-0 place-items-center rounded-lg bg-primary/10">
            <Brain className="h-6 w-6 text-primary" />
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-wider text-bluegray">MRI decision-support output</div>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight">Alzheimer-like vs Non-demented MRI Pattern</h2>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted-foreground">
              Upload the patient MRI exam folder or ZIP file exported from the MRI CD. The system will automatically
              detect the compatible structural MRI series.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6">
          <Card className="p-5">
            <div className="text-sm font-semibold">Upload MRI exam</div>
            <p className="mt-1 text-xs text-muted-foreground">Upload MRI CD ZIP / DICOM folder / NIfTI volume</p>
            <div className="mt-4">
              <UploadZone
                accept=".nii,.nii.gz,.dcm,.zip"
                hint="Accepted formats: .nii, .nii.gz, .dcm, .zip containing DICOM files"
                onFile={setFile}
              />
            </div>
            <div className="mt-4 rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs leading-relaxed">
              <div className="flex gap-2">
                <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                <span>
                  The model analyzes a 3D MRI exam, not a single image. If the exam contains multiple series, the
                  system selects the most compatible structural MRI series for analysis. DICOM folder support depends on
                  browser upload capability.
                </span>
              </div>
            </div>
          </Card>

          <Card className="p-5">
            <div className="text-sm font-semibold">Patient information</div>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <Field label="Patient ID">
                <Input value={meta.patientId} onChange={(e) => update({ patientId: e.target.value })} placeholder="P-0001" />
              </Field>
              <Field label="Sex">
                <Select value={meta.sex} onValueChange={(sex) => update({ sex })}>
                  <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="F">Female</SelectItem>
                    <SelectItem value="M">Male</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Age at consultation">
                <Input type="number" value={meta.age} onChange={(e) => update({ age: e.target.value })} placeholder="Clinical context only" />
              </Field>
              <Field label="MMSE optional">
                <Input type="number" value={meta.mmse} onChange={(e) => update({ mmse: e.target.value })} placeholder="0-30" />
              </Field>
              <Field label="CDR optional">
                <Input type="number" step="0.5" value={meta.cdr} onChange={(e) => update({ cdr: e.target.value })} placeholder="Clinical context" />
              </Field>
              <div className="col-span-2 rounded-lg border border-amber-300/50 bg-amber-50 p-3 text-xs text-amber-950">
                Age is collected for clinical context only and is not used by the final prediction model.
              </div>
              <div className="col-span-2">
                <Field label="Clinical notes optional">
                  <Textarea value={meta.notes} onChange={(e) => update({ notes: e.target.value })} rows={3} />
                </Field>
              </div>
            </div>
          </Card>

          <Card className="p-5">
            <Button onClick={() => handleRun()} disabled={running} className="w-full gap-2" size="lg">
              <Sparkles className="h-4 w-4" />
              {running ? "Analyzing MRI exam" : "Run MRI analysis"}
            </Button>
          </Card>
        </div>

        <div className="space-y-6 lg:col-span-2">
          {!result && (
            <Card className="border-dashed p-10 text-center">
              <Brain className="mx-auto h-10 w-10 text-bluegray" />
              <div className="mt-3 font-medium">{running ? "Analyzing MRI exam" : "No analysis yet"}</div>
              <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
                Results will show the selected MRI series, model probabilities, and patient-specific MRI measurements.
              </p>
            </Card>
          )}

          {result && (
            <>
              {result.warnings && result.warnings.length > 0 && (
                <Card className="border-amber-300/60 bg-amber-50 p-4 text-sm text-amber-950">
                  <div className="flex gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <div>{result.warnings.join(" ")}</div>
                  </div>
                </Card>
              )}

              <Card className={isProcessingFailure ? "border-amber-300/70 bg-amber-50/60 p-5" : "p-5"}>
                <div className="text-[11px] uppercase tracking-wider text-bluegray">Prediction</div>
                <h2 className="mt-1 text-2xl font-semibold">
                  {isProcessingFailure ? "MRI protocol not compatible" : result.predictedClass}
                </h2>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {isProcessingFailure
                    ? "No valid 3D structural T1 MRI series was detected. The uploaded exam cannot be analyzed by this Alzheimer MRI model. Please provide a 3D T1/MPRAGE/SPGR/TFE/BRAVO structural MRI sequence or a compatible NIfTI volume."
                    : result.summary}
                </p>
                {!isProcessingFailure && (
                  <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
                    <DetailRow label="Alzheimer-like / demented probability" value={pct(result.probabilities?.alzheimerProbability)} />
                    <DetailRow label="Healthy / non-demented probability" value={pct(result.probabilities?.healthyProbability)} />
                    <DetailRow label="Decision threshold" value={pct(result.probabilities?.decisionThreshold)} />
                    <DetailRow label="Confidence" value={result.probabilities?.confidenceLevel} />
                  </div>
                )}
                <div className="mt-4 rounded-lg border bg-card/70 p-3 text-xs">{result.disclaimer}</div>
              </Card>

              <Card className="p-5">
                <div className="text-sm font-semibold">Detected series</div>
                <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                  <DetailRow label="Selected series" value={result.seriesInfo?.selectedSeries} />
                  <DetailRow label="Series description" value={result.seriesInfo?.seriesDescription} />
                  <DetailRow label="Modality" value={result.seriesInfo?.modality} />
                  <DetailRow label="Number of slices" value={result.seriesInfo?.numberOfSlices} />
                  <DetailRow label="Reason selected" value={result.seriesInfo?.reasonSelected} />
                  <DetailRow label="Ignored series" value={result.seriesInfo?.ignoredSeries} />
                </div>
                {result.availableSeries && result.availableSeries.length > 0 && (
                  <div className="mt-5 space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Available MRI series</div>
                    {result.availableSeries.map((series, index) => (
                      <div key={`${series.seriesDescription}-${index}`} className="rounded-md border bg-card/60 p-3 text-sm">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="font-medium">{series.seriesDescription || "MRI series"}</div>
                          <div className="text-xs uppercase tracking-wider text-muted-foreground">
                            {series.status || "candidate"}
                          </div>
                        </div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {series.modality || "MRI"} · {series.numberOfSlices ?? "Unknown"} slices
                        </div>
                        <div className="mt-2 text-xs">{series.reason || "Series reviewed by the backend."}</div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              {!isProcessingFailure && (
                <Card className="p-5">
                  <div className="text-sm font-semibold">Model pipeline</div>
                  <div className="mt-4 grid gap-3 md:grid-cols-5">
                    {[
                      "MRI exam selection",
                      "Structural MRI analysis",
                      "Image-based AI probability",
                      "Doctor-facing probability",
                      "Explainable report",
                    ].map((step, index) => (
                      <div key={step} className="rounded-md border bg-card/60 p-3 text-sm">
                        <div className="text-[11px] uppercase text-muted-foreground">Step {index + 1}</div>
                        <div className="mt-1 font-medium">{step}</div>
                      </div>
                    ))}
                  </div>
                  <details className="mt-4 rounded-lg border bg-card/60 p-3 text-xs">
                    <summary className="flex cursor-pointer items-center gap-2 font-medium">
                      <ChevronDown className="h-4 w-4" /> Technical details
                    </summary>
                    <p className="mt-2 text-muted-foreground">
                      MRI - ConvNeXt-Tiny 2.5D - CNN probability. Age is excluded from the final prediction model.
                    </p>
                  </details>
                </Card>
              )}

              {(showGradCam || showMriFeatures) && (
                <Card className="p-5">
                  <div className="text-sm font-semibold">
                    {showGradCam ? "Explainability" : "Patient-specific MRI measurements"}
                  </div>
                  <div className="mt-4 space-y-5">
                    {showGradCam && (
                      <div className="rounded-lg border bg-card/50 p-4">
                        <div className="flex justify-center">
                          <img
                            src={result.gradCam?.imageDataUrl}
                            alt="Grad-CAM heatmap for Alzheimer-like MRI probability"
                            className="mx-auto max-h-[360px] w-full max-w-[560px] rounded-md border object-contain"
                          />
                        </div>
                        <p className="mt-3 text-sm text-muted-foreground">
                          {result.gradCam?.explanation ||
                            "This heatmap shows image regions that influenced the CNN probability for the Alzheimer-like class. It is not a clinical localization of disease."}
                        </p>
                        {typeof result.gradCam?.sliceIndex === "number" && (
                          <p className="mt-1 text-xs text-muted-foreground">Slice index: {result.gradCam.sliceIndex}</p>
                        )}
                      </div>
                    )}
                    {showMriFeatures && (
                      <div>
                        {showGradCam && <div className="text-sm font-semibold">Patient-specific MRI measurements</div>}
                        <p className="mt-1 text-xs text-muted-foreground">
                          These values are automatically extracted from the uploaded MRI and used as model-supporting measurements.
                          They are not standalone diagnostic biomarkers.
                        </p>
                        <div className="mt-3 grid gap-3 md:grid-cols-2">
                          {result.mriFeatures?.map((feature) => (
                            <div key={feature.label} className="rounded-md border bg-card/60 p-3">
                              <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{feature.label}</div>
                              <div className="mt-1 text-sm font-medium">
                                {feature.value}
                                {feature.unit ? ` ${feature.unit}` : ""}
                              </div>
                              {feature.description && <p className="mt-1 text-xs text-muted-foreground">{feature.description}</p>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </Card>
              )}

              {showCognitiveInterpretation && (
                <Card className="p-5">
                  <div className="text-sm font-semibold">Cognitive score interpretation</div>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {cognitiveInterpretation}
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    MMSE/CDR are not used by the prediction model.
                  </p>
                </Card>
              )}

              <ReportExportPanel result={result} axisId={axis.id} axisTitle={axis.title} patient={reportPatient} />
            </>
          )}
        </div>
      </div>
    </Layout>
  );
}

