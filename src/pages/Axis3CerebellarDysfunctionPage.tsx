import { useState } from "react";
import { Layout } from "@/components/Layout";
import { UploadZone } from "@/components/UploadZone";
import { AnalysisStatusCard } from "@/components/AnalysisStatusCard";
import { ResultCard } from "@/components/ResultCard";
import { ConfidenceBars } from "@/components/ConfidenceBars";
import { MetadataForm, type PatientMeta } from "@/components/MetadataForm";
import { ReportExportPanel } from "@/components/ReportExportPanel";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { runAnalysis, type AnalysisResult } from "@/lib/api";
import { getAxisById } from "@/lib/axes";

export function Axis3CerebellarDysfunctionPage() {
  const axis = getAxisById("axis3-cerebellar-dysfunction");
  const [file, setFile] = useState<File | null>(null);
  const [meta, setMeta] = useState<PatientMeta>({ id: "", age: "", sex: "", notes: "", email: "" });
  const [inputSpace, setInputSpace] = useState<"raw" | "mni" | "notebook_crop">("raw");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const detail = result?.cerebellum;

  async function analyze() {
    if (!file || running) return;
    const validExtension = inputSpace === "notebook_crop" ? /\.npy$/i : /\.nii(\.gz)?$/i;
    if (!validExtension.test(file.name) || file.size > 128 * 1024 * 1024) {
      setError("Choose a file matching the selected input preparation, up to 128 MB.");
      return;
    }
    setRunning(true);
    setError("");
    setResult(null);
    try {
      const response = await runAnalysis(
        {
          axisId: axis.id,
          fileName: file.name,
          patient: {
            id: meta.id || undefined,
            age: meta.age ? Number(meta.age) : undefined,
            sex: meta.sex === "M" || meta.sex === "F" ? meta.sex : undefined,
            notes: meta.notes,
            email: meta.email.trim() || undefined,
          },
        },
        { file, inputSpace },
      );
      if (!response.modelLoaded || !response.cerebellum) {
        throw new Error(
          "The analysis service returned an incompatible response. Contact your workspace administrator.",
        );
      }
      setResult(response);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Cerebellum analysis failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <Layout title="Cerebellum MRI analysis" subtitle={axis.purpose}>
      <Card className="p-6 bg-gradient-card">
        <h2 className="text-2xl font-semibold">Prepare. Analyze. Review.</h2>
        <p className="mt-2 text-muted-foreground max-w-3xl">
          Upload a scan, review healthy versus anomalous patterns, and inspect the model attention
          images. Anomalous patterns receive a second assessment for motor or cognitive patterns.
        </p>
      </Card>
      <p className="mt-4 text-sm text-muted-foreground">
        Research use only. Use a de-identified scan and case reference. A qualified clinician must
        review the findings alongside the examination.
      </p>
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="p-5 space-y-5 self-start">
          <h3 className="font-semibold">1 · Prepare the examination</h3>
          <fieldset
            disabled={running}
            className={`space-y-4 ${running ? "pointer-events-none opacity-60" : ""}`}
          >
            <label className="block text-sm" htmlFor="cerebellum-space">
              Scan preparation
            </label>
            <select
              id="cerebellum-space"
              className="w-full rounded-md border bg-background p-2 text-sm"
              value={inputSpace}
              onChange={(event) => {
                setInputSpace(event.target.value as typeof inputSpace);
                setFile(null);
                setResult(null);
                setError("");
              }}
            >
              <option value="raw">Standard 3D MRI (.nii or .nii.gz)</option>
              <option value="mni">Advanced: MRI aligned to the model template</option>
              <option value="notebook_crop">Advanced: preprocessed research crop (.npy)</option>
            </select>
            <UploadZone
              key={inputSpace}
              accept={inputSpace === "notebook_crop" ? ".npy" : ".nii,.nii.gz"}
              hint={
                inputSpace === "notebook_crop"
                  ? "Research input: 128 × 128 × 64 preprocessed crop; no skull stripping"
                  : "NIfTI (.nii or .nii.gz) · maximum 128 MB"
              }
              onFile={(next) => {
                setFile(next);
                setResult(null);
                setError("");
              }}
            />
          </fieldset>
          <fieldset disabled={running} className="space-y-3">
            <legend className="text-sm font-semibold mb-3">Case details (optional)</legend>
            <MetadataForm
              value={meta}
              onChange={(value) => {
                setMeta(value);
                setResult(null);
              }}
            />
          </fieldset>
          <p className="text-xs text-muted-foreground">
            Raw MRI processing includes bias correction and alignment to the training template and
            can take several minutes.
          </p>
          <Button className="w-full" disabled={!file || running} onClick={analyze}>
            {running ? "Analyzing MRI…" : "Analyze MRI"}
          </Button>
          {error && (
            <p role="alert" className="text-sm text-destructive break-words">
              {error}
            </p>
          )}
        </Card>
        <div className="lg:col-span-2 space-y-5" aria-live="polite" aria-busy={running}>
          {running && (
            <AnalysisStatusCard stage="Preparing the MRI and running the models. This can take several minutes." />
          )}
          {!running && !result && (
            <Card className="p-10 text-center border-dashed">
              <h3 className="font-semibold">Your cerebellum assessment will appear here</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Upload a scan to see both classification stages and MRI attention images.
              </p>
            </Card>
          )}
          {result && detail && (
            <>
              <ResultCard result={result} />
              <ReportExportPanel
                result={result}
                axisId={axis.id}
                axisTitle={axis.title}
                patientEmail={meta.email}
                patient={{
                  id: meta.id || undefined,
                  age: meta.age ? Number(meta.age) : undefined,
                  sex: meta.sex === "M" || meta.sex === "F" ? meta.sex : undefined,
                }}
              />
              <div className="grid gap-4 md:grid-cols-2">
                <Card className="p-5 space-y-3">
                  <h3 className="font-semibold">Stage 1 · Pattern screening</h3>
                  <p>{detail.stage1.predictedClass}</p>
                  <ConfidenceBars items={detail.stage1.confidence} />
                </Card>
                <Card className="p-5 space-y-3">
                  <h3 className="font-semibold">Stage 2 · Anomaly classification</h3>
                  {detail.stage2 ? (
                    <>
                      <p>{detail.stage2.predictedClass}</p>
                      <ConfidenceBars items={detail.stage2.confidence} />
                      <p className="text-xs text-muted-foreground">
                        These model scores apply only after Stage 1 detects an anomaly; they are not
                        clinical probabilities.
                      </p>
                    </>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Not run: Stage 1 classified this scan as healthy.
                    </p>
                  )}
                </Card>
              </div>
              <Card className="p-5 space-y-4">
                <h3 className="font-semibold">
                  Model attention · Stage {detail.explainabilityStage}
                </h3>
                <div className="grid gap-4 sm:grid-cols-2">
                  {detail.images.map((image) => (
                    <figure key={image.title}>
                      <img
                        src={image.dataUrl}
                        alt={image.title}
                        className="w-full rounded-lg bg-black"
                      />
                      <figcaption className="mt-2 text-sm">{image.title}</figcaption>
                    </figure>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">{detail.explanation}</p>
              </Card>
            </>
          )}
        </div>
      </div>
    </Layout>
  );
}
