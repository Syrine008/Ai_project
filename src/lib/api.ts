import { apiFetch } from "@/lib/http";
import { AXES, type AxisId } from "./axes";

/**
 * Typed client for the Django analysis API. Never fabricates analysis results.
 */

export interface AnalysisRequest {
  axisId: AxisId;
  fileName: string;
  patient: {
    id?: string;
    age?: number;
    sex?: "M" | "F";
    mmse?: number;
    cdr?: number;
    notes?: string;
    /** Optional — used only for “send report to patient”; also sent in analyze metadata when set. */
    email?: string;
  };
}

export interface RegionContribution {
  region: string;
  contribution: number; // 0..1
  side?: "L" | "R" | "B";
  note?: string;
}

export interface ConfidenceItem {
  label: string;
  value: number; // 0..1
}

export interface SignalPoint {
  t: number;
  v: number;
}

export interface TimelineMarker {
  t: number; // seconds
  label: string;
  severity: "low" | "moderate" | "high";
}

export interface NetworkEdge {
  from: string;
  to: string;
  weight: number;
}

export interface AnalysisResult {
  cerebellum?: {
    stage1: { predictedClass: string; topConfidence: number; confidence: ConfidenceItem[] };
    stage2: { predictedClass: string; topConfidence: number; confidence: ConfidenceItem[] } | null;
    inputSpace: string;
    explainabilityStage: number;
    images: { title: string; dataUrl: string }[];
    sliceIndex: number;
    explanation: string;
  };
  axisId: AxisId;
  caseId: string;
  generatedAt: string;
  predictedClass: string;
  topConfidence?: number | null;
  summary: string;
  disclaimer: string;
  confidence: ConfidenceItem[];
  regions?: RegionContribution[];
  signal?: SignalPoint[];
  timeline?: TimelineMarker[];
  network?: { nodes: string[]; edges: NetworkEdge[] };
  metrics?: { label: string; value: string; hint?: string }[];
  /** Axis 4: PNG data URL of slice + Grad-CAM overlay when backend inference runs. */
  gradCamDataUrl?: string;
  modelLoaded?: boolean;
  anomalyScore?: number;
  threshold?: number;
  isAnomaly?: boolean;
  percentileOfNormal?: number;
  heatmapB64?: string;
  nFrames?: number;
  hw?: number;
  seriesInfo?: {
    selectedSeries?: string;
    seriesDescription?: string;
    modality?: string;
    numberOfSlices?: number;
    reasonSelected?: string;
    ignoredSeries?: string[];
  };
  availableSeries?: {
    seriesDescription?: string;
    modality?: string;
    numberOfSlices?: number;
    status?: "selected" | "candidate" | "rejected";
    reason?: string;
  }[];
  warnings?: string[];
  featureImportance?: { feature: string; label?: string; importance: number; std?: number }[];
  probabilities?: {
    alzheimerProbability?: number;
    healthyProbability?: number;
    cnnAlzheimerProbability?: number;
    probability_PD?: number;
    probability_atypical?: number;
    decisionThreshold?: number;
    confidenceLevel?: "Low" | "Moderate" | "High";
  };
  mriFeatures?: {
    label: string;
    value: string | number;
    unit?: string;
    description?: string;
  }[];
  gradCam?: {
    available: boolean;
    imageDataUrl?: string;
    sliceIndex?: number;
    message?: string;
    explanation?: string;
    reportPath?: string;
  };
  explainability?: Record<string, unknown>;
  explainabilityWarning?: string;
  technicalDetails?: Record<string, unknown>;
  researchInsights?: {
    mmseCorrelation?: string;
    longitudinal?: string;
  };
  metadataUsed?: string[];
  metadataExcluded?: string[];
  uploadedExamName?: string;
  patientId?: string;
  clinicalMetadata?: {
    sex?: string | null;
    age?: number | null;
    mmse?: number | null;
    cdr?: number | null;
    notes?: string | null;
  };
}

export type RunAnalysisOptions = {
  inputSpace?: "raw" | "mni" | "notebook_crop";
  file?: File | null;
  /** Analyze 7.5 second part (.hdr or .img) → multipart ``file_analyze_pair``. Axis 4 only. */
  analyzePairFile?: File | null;
  /** When true, backend receives `metadata.demo=true` and no file upload. */
  demo?: boolean;
};

/**
 * If `VITE_API_BASE_URL` is set (e.g. `http://127.0.0.1:8000`), POSTs multipart
 * to the axis Django endpoint; otherwise reports a configuration error.
 */
export async function runAnalysis(
  req: AnalysisRequest,
  options: RunAnalysisOptions = {},
): Promise<AnalysisResult> {
  const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
  const file = options.file ?? null;
  const demo = options.demo ?? false;

  if (
    (req.axisId === "axis1-alzheimer-dementia" || req.axisId === "axis3-cerebellar-dysfunction") &&
    !baseUrl
  ) {
    throw new Error(
      "Real backend analysis is not connected. Please start the Django backend or configure the API URL.",
    );
  }

  if (baseUrl) {
    const axis = AXES.find((a) => a.id === req.axisId)!;
    const url = `${baseUrl.replace(/\/$/, "")}${axis.endpoint}`;
    const fd = new FormData();
    const metadata =
      req.axisId === "axis2-parkinson-atypical"
        ? demo
          ? { demo: true }
          : {}
        : {
            demo,
            ...(req.axisId === "axis3-cerebellar-dysfunction"
              ? { inputSpace: options.inputSpace ?? "raw" }
              : {}),
            age: req.patient.age ?? null,
            sex: req.patient.sex ?? null,
            mmse: req.patient.mmse ?? null,
            cdr: req.patient.cdr ?? null,
            patientId: req.patient.id ?? null,
            notes: req.patient.notes ?? null,
            patientEmail: req.patient.email?.trim() || null,
          };
    fd.append("metadata", JSON.stringify(metadata));
    if (file && !demo) {
      fd.append("file", file);
    }
    const pair = options.analyzePairFile ?? null;
    if (pair && !demo && req.axisId === "axis4-brain-aging") {
      fd.append("file_analyze_pair", pair);
    }
    let res: Response;
    try {
      res = await apiFetch(url, { method: "POST", body: fd });
    } catch (error) {
      if (req.axisId === "axis1-alzheimer-dementia") {
        throw new Error(
          "Real backend analysis is not connected. Please start the Django backend or configure the API URL.",
        );
      }
      throw error;
    }
    if (!res.ok) {
      const t = await res.text();
      if (req.axisId === "axis3-cerebellar-dysfunction") {
        let message = `Cerebellum analysis failed (${res.status}).`;
        try {
          message = JSON.parse(t).detail || message;
        } catch {
          /* non-JSON server response */
        }
        throw new Error(message);
      }
      throw new Error(t || res.statusText);
    }
    const data = (await res.json()) as AnalysisResult;
    if (!data.generatedAt) {
      data.generatedAt = new Date().toISOString();
    }
    return data;
  }

  throw new Error("The analysis service is not configured. Contact your workspace administrator.");
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Payload safe to POST (drops huge Grad-CAM data URL). */
export function analysisResultForEmail(result: AnalysisResult): AnalysisResult {
  const { gradCamDataUrl: _, ...rest } = result;
  return rest;
}

export async function sendReportToPatient(payload: {
  to: string;
  axisId: AxisId;
  axisTitle: string;
  patient?: AnalysisRequest["patient"];
  result: AnalysisResult;
}): Promise<{ followUpNote: boolean }> {
  const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
  const to = payload.to.trim();
  if (!EMAIL_RE.test(to)) {
    throw new Error("Invalid email address.");
  }
  if (!baseUrl) {
    throw new Error(
      "Email sending requires the Django API. Set VITE_API_BASE_URL (e.g. http://127.0.0.1:8000) in .env and restart Vite.",
    );
  }
  const url = `${baseUrl.replace(/\/$/, "")}/api/send-report-email/`;
  const res = await apiFetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      to,
      axis_id: payload.axisId,
      axis_title: payload.axisTitle,
      patient: {
        id: payload.patient?.id,
        age: payload.patient?.age,
        sex: payload.patient?.sex,
      },
      result: analysisResultForEmail(payload.result),
    }),
  });
  const raw = await res.text();
  let data = {} as { detail?: string; followUpNote?: boolean };
  try {
    data = JSON.parse(raw) as typeof data;
  } catch {
    /* Django HTML error page etc. */
  }
  if (!res.ok) {
    if (typeof data.detail === "string" && data.detail.trim()) {
      throw new Error(data.detail);
    }
    throw new Error(
      res.status >= 500
        ? `Server error (${res.status}). Check the Django terminal for the traceback.`
        : `${res.status} ${res.statusText || "Send failed"}`,
    );
  }
  return { followUpNote: Boolean(data.followUpNote) };
}
