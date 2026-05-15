import { AXES, type AxisId } from "./axes";

/**
 * Mock API layer.
 * Each function maps 1:1 to a future Django REST endpoint.
 * Replace fetch URLs when the backend is wired in.
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

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

const rand = (min: number, max: number) => +(Math.random() * (max - min) + min).toFixed(3);

const buildSignal = (n = 200, seed = 1): SignalPoint[] =>
  Array.from({ length: n }, (_, i) => ({
    t: i,
    v:
      Math.sin(i / 6 + seed) * 0.4 +
      Math.sin(i / 2.3 + seed * 1.7) * 0.25 +
      (Math.random() - 0.5) * 0.3,
  }));

function buildResultFor(req: AnalysisRequest): AnalysisResult {
  const axis = AXES.find((a) => a.id === req.axisId)!;
  const caseId = `BRN-${Date.now().toString().slice(-6)}`;
  const base = {
    axisId: req.axisId,
    caseId,
    generatedAt: new Date().toISOString(),
    disclaimer:
      "Decision-support output. Not a standalone diagnosis — to be interpreted by a qualified clinician.",
  };

  switch (req.axisId) {
    case "axis1-alzheimer-dementia":
      throw new Error(
        "Real backend analysis is not connected. Please start the Django backend or configure the API URL.",
      );
    case "axis2-parkinson-atypical":
      return {
        ...base,
        disclaimer: "Research decision-support output only. This result is not a clinical diagnosis.",
        predictedClass: "PD pattern",
        topConfidence: 0.5,
        summary:
          "Backend response unavailable. Start Django to run the Parkinson vs atypical parkinsonism CNN.",
        confidence: [
          { label: "PD pattern", value: 0.5 },
          { label: "Atypical parkinsonian pattern", value: 0.5 },
        ],
        probabilities: {
          probability_PD: 0.5,
          probability_atypical: 0.5,
          decisionThreshold: 0.52,
        },
        modelLoaded: false,
        gradCam: {
          available: false,
          message: "Explainability output is not available for this case yet.",
        },
      };

    case "axis3-cerebellar-dysfunction":
      return {
        ...base,
        predictedClass: "Mild cerebellar involvement detected",
        topConfidence: 0.66,
        summary:
          "Suggestive volume loss in posterior cerebellar lobules. Findings may contribute to motor and cognitive symptoms — interpretation support only.",
        confidence: [
          { label: "No involvement", value: 0.22 },
          { label: "Mild involvement", value: 0.66 },
          { label: "Marked involvement", value: 0.12 },
        ],
        regions: [
          { region: "Lobule VI", side: "B", contribution: 0.72 },
          { region: "Crus I", side: "L", contribution: 0.58 },
          { region: "Vermis", side: "B", contribution: 0.40 },
          { region: "Dentate nucleus", side: "R", contribution: 0.33 },
        ],
        metrics: [{ label: "Cerebellar score", value: "0.66 / 1.0" }],
      };

    case "axis4-brain-aging":
      return {
        ...base,
        predictedClass: "Brain-age gap: +6.4 years",
        topConfidence: 0.79,
        summary:
          "Frontal and temporal regions appear older than chronological age. Pattern suggests uneven aging — consider lifestyle and vascular risk factors.",
        confidence: [
          { label: "Accelerated aging", value: 0.79 },
          { label: "Typical aging", value: 0.18 },
          { label: "Younger-than-age", value: 0.03 },
        ],
        regions: [
          { region: "Prefrontal cortex", side: "B", contribution: 0.81 },
          { region: "Temporal pole", side: "L", contribution: 0.62 },
          { region: "Insula", side: "R", contribution: 0.47 },
          { region: "Occipital", side: "B", contribution: 0.21, note: "Within expected range" },
        ],
        metrics: [
          { label: "Predicted age", value: "68.4 y" },
          { label: "Chronological", value: "62.0 y" },
          { label: "Δ Brain-age gap", value: "+6.4 y" },
        ],
      };

    case "axis5-functional-connectivity":
      return {
        ...base,
        predictedClass: "Elevated cognitive effort signature detected",
        topConfidence: 0.74,
        summary:
          "Default mode network shows reduced integration while frontoparietal control network shows compensatory hyperconnectivity — pattern consistent with hidden cognitive effort.",
        confidence: [
          { label: "Hidden effort pattern", value: 0.74 },
          { label: "Typical pattern", value: 0.21 },
          { label: "Atypical / other", value: 0.05 },
        ],
        network: {
          nodes: ["DMN", "FPN", "DAN", "SAL", "VIS", "MOT"],
          edges: [
            { from: "DMN", to: "FPN", weight: 0.82 },
            { from: "FPN", to: "DAN", weight: 0.74 },
            { from: "SAL", to: "FPN", weight: 0.69 },
            { from: "DMN", to: "SAL", weight: 0.31 },
            { from: "VIS", to: "DAN", weight: 0.55 },
            { from: "MOT", to: "DAN", weight: 0.42 },
          ],
        },
        metrics: [
          { label: "DMN integration", value: "↓ 18%" },
          { label: "FPN load", value: "↑ 27%" },
        ],
      };

    case "axis6-neuromotor-video":
      return {
        ...base,
        predictedClass: "Movement anomalies suggestive of bradykinesia",
        topConfidence: 0.69,
        summary:
          "Asymmetric arm swing and reduced step length detected. Findings are suggestive of bradykinetic gait — clinical examination required.",
        confidence: [
          { label: "Bradykinesia-like", value: 0.69 },
          { label: "Ataxic-like", value: 0.18 },
          { label: "Within normal range", value: 0.13 },
        ],
        timeline: [
          { t: 3.2, label: "Reduced left arm swing", severity: "moderate" },
          { t: 7.8, label: "Step length asymmetry", severity: "high" },
          { t: 12.1, label: "Postural sway peak", severity: "moderate" },
          { t: 18.5, label: "Hesitation episode", severity: "low" },
        ],
        metrics: [
          { label: "Anomaly score", value: "0.69" },
          { label: "Cadence", value: "98 spm" },
          { label: "Step asymmetry", value: "14%" },
        ],
      };

    case "axis7-epilepsy-network":
      return {
        ...base,
        predictedClass: "Network instability windows detected",
        topConfidence: 0.77,
        summary:
          "Multiple instability windows in temporal channels. Pattern suggests elevated network vulnerability — interpretation support only, not a seizure prediction.",
        confidence: [
          { label: "Elevated vulnerability", value: 0.77 },
          { label: "Borderline", value: 0.16 },
          { label: "Stable", value: 0.07 },
        ],
        signal: buildSignal(240, 2),
        timeline: [
          { t: 22, label: "T7 instability burst", severity: "high" },
          { t: 58, label: "F8 spike-wave", severity: "moderate" },
          { t: 104, label: "T8 desynchronization", severity: "moderate" },
        ],
        metrics: [
          { label: "Vulnerability index", value: "0.77" },
          { label: "Unstable channels", value: "T7, F8, T8" },
        ],
      };
  }

  return {
    ...base,
    predictedClass: "Result",
    topConfidence: 0.5,
    summary: "Mock result.",
    confidence: [{ label: "Result", value: 0.5 }],
  };
}

export type RunAnalysisOptions = {
  file?: File | null;
  /** Analyze 7.5 second part (.hdr or .img) → multipart ``file_analyze_pair``. Axis 4 only. */
  analyzePairFile?: File | null;
  /** When true, backend receives `metadata.demo=true` and no file upload. */
  demo?: boolean;
};

/**
 * If `VITE_API_BASE_URL` is set (e.g. `http://127.0.0.1:8000`), POSTs multipart
 * to the axis Django endpoint; otherwise returns the in-browser mock.
 */
export async function runAnalysis(
  req: AnalysisRequest,
  options: RunAnalysisOptions = {},
): Promise<AnalysisResult> {
  const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
  const file = options.file ?? null;
  const demo = options.demo ?? false;

  if (req.axisId === "axis1-alzheimer-dementia" && !baseUrl) {
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
            age: req.patient.age ?? null,
            sex: req.patient.sex ?? null,
            mmse: req.patient.mmse ?? null,
            cdr: req.patient.cdr ?? null,
            patientId: req.patient.id ?? null,
            notes: req.patient.notes ?? null,
            patientEmail: req.patient.email?.trim() || null,
          };
    fd.append(
      "metadata",
      JSON.stringify(metadata),
    );
    if (file && !demo) {
      fd.append("file", file);
    }
    const pair = options.analyzePairFile ?? null;
    if (pair && !demo && req.axisId === "axis4-brain-aging") {
      fd.append("file_analyze_pair", pair);
    }
    let res: Response;
    try {
      res = await fetch(url, { method: "POST", body: fd });
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
      throw new Error(t || res.statusText);
    }
    const data = (await res.json()) as AnalysisResult;
    if (!data.generatedAt) {
      data.generatedAt = new Date().toISOString();
    }
    return data;
  }

  await wait(800 + Math.random() * 600);
  return buildResultFor(req);
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
    await wait(400);
    throw new Error(
      "Email sending requires the Django API. Set VITE_API_BASE_URL (e.g. http://127.0.0.1:8000) in .env and restart Vite.",
    );
  }
  const url = `${baseUrl.replace(/\/$/, "")}/api/send-report-email/`;
  const res = await fetch(url, {
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

export interface CaseRecord {
  id: string;
  patient: string;
  axisId: AxisId;
  axisTitle: string;
  date: string;
  status: "completed" | "in_progress" | "queued";
  topResult: string;
  confidence: number;
}

export const MOCK_CASES: CaseRecord[] = [
  {
    id: "BRN-104928",
    patient: "P-00421",
    axisId: "axis1-alzheimer-dementia",
    axisTitle: "Alzheimer & Dementias",
    date: "2026-05-07",
    status: "completed",
    topResult: "Alzheimer's-type pattern",
    confidence: 0.82,
  },
  {
    id: "BRN-104927",
    patient: "P-00417",
    axisId: "axis6-neuromotor-video",
    axisTitle: "Neuromotor Video",
    date: "2026-05-07",
    status: "completed",
    topResult: "Bradykinesia-like signature",
    confidence: 0.69,
  },
  {
    id: "BRN-104925",
    patient: "P-00410",
    axisId: "axis5-functional-connectivity",
    axisTitle: "Functional Connectivity",
    date: "2026-05-06",
    status: "completed",
    topResult: "Hidden cognitive effort",
    confidence: 0.74,
  },
  {
    id: "BRN-104924",
    patient: "P-00409",
    axisId: "axis4-brain-aging",
    axisTitle: "Brain Aging",
    date: "2026-05-06",
    status: "in_progress",
    topResult: "Estimating brain-age map…",
    confidence: 0,
  },
  {
    id: "BRN-104921",
    patient: "P-00402",
    axisId: "axis7-epilepsy-network",
    axisTitle: "Epilepsy Network",
    date: "2026-05-05",
    status: "completed",
    topResult: "Elevated vulnerability",
    confidence: 0.77,
  },
];
