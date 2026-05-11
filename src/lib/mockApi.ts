import { AXES, type AxisId } from "./axes";

/**
 * Mock API layer.
 * Each function maps 1:1 to a future Django REST endpoint.
 * Replace fetch URLs when the backend is wired in.
 */

export interface AnalysisRequest {
  axisId: AxisId;
  fileName: string;
  file?: File;
  demo?: boolean;
  patient: {
    id?: string;
    age?: number;
    sex?: "M" | "F" | "Other";
    notes?: string;
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
  topConfidence: number;
  summary: string;
  disclaimer: string;
  confidence: ConfidenceItem[];
  regions?: RegionContribution[];
  signal?: SignalPoint[];
  timeline?: TimelineMarker[];
  network?: { nodes: string[]; edges: NetworkEdge[] };
  metrics?: { label: string; value: string; hint?: string }[];
  modelLoaded?: boolean;
  anomalyScore?: number;
  threshold?: number;
  isAnomaly?: boolean;
  percentileOfNormal?: number;
  heatmapB64?: string;
  nFrames?: number;
  hw?: number;
}

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://localhost:8000";

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
      return {
        ...base,
        predictedClass: "Profile more consistent with Alzheimer's-type pattern",
        topConfidence: 0.82,
        summary:
          "AI-detected pattern shows medial temporal atrophy with hippocampal asymmetry, more consistent with an Alzheimer's-type profile than vascular dementia. Suggestive findings — clinical correlation required.",
        confidence: [
          { label: "Alzheimer's-type", value: 0.82 },
          { label: "Vascular dementia", value: 0.11 },
          { label: "Other dementia", value: 0.07 },
        ],
        regions: [
          { region: "Hippocampus", side: "L", contribution: 0.91, note: "Marked atrophy" },
          { region: "Hippocampus", side: "R", contribution: 0.78 },
          { region: "Entorhinal cortex", side: "B", contribution: 0.74 },
          { region: "Posterior cingulate", side: "B", contribution: 0.55 },
          { region: "Parietal lobe", side: "L", contribution: 0.41 },
        ],
        metrics: [
          { label: "Pattern strength", value: "High", hint: "Composite score 0.82" },
          { label: "Asymmetry index", value: "0.18", hint: "L > R atrophy" },
        ],
      };

    case "axis2-parkinson-atypical":
      return {
        ...base,
        predictedClass: "Profile more consistent with idiopathic Parkinson's disease",
        topConfidence: 0.71,
        summary:
          "Substantia nigra and putaminal cues align more with idiopathic PD than MSA/PSP. Atypical features remain possible — recommend longitudinal follow-up.",
        confidence: [
          { label: "Parkinson's disease", value: 0.71 },
          { label: "MSA", value: 0.16 },
          { label: "PSP", value: 0.09 },
          { label: "Other", value: 0.04 },
        ],
        regions: [
          { region: "Substantia nigra", side: "B", contribution: 0.88 },
          { region: "Putamen", side: "L", contribution: 0.62 },
          { region: "Midbrain", side: "B", contribution: 0.49, note: "Hummingbird sign absent" },
          { region: "Pons", side: "B", contribution: 0.31 },
        ],
        metrics: [
          { label: "Midbrain/Pons ratio", value: "0.61", hint: "Within PD-typical range" },
        ],
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

export async function runAnalysis(req: AnalysisRequest): Promise<AnalysisResult> {
  if (req.axisId === "axis5-functional-connectivity") {
    return runAxis5Analysis(req);
  }

  // Simulate network + inference time
  await wait(1800 + Math.random() * 1200);
  return buildResultFor(req);
}

async function runAxis5Analysis(req: AnalysisRequest): Promise<AnalysisResult> {
  if (req.demo || !req.file) {
    await wait(1600 + Math.random() * 800);
    return buildResultFor(req);
  }

  const axis = AXES.find((a) => a.id === req.axisId);
  if (!axis) {
    throw new Error("Axis not found");
  }

  const formData = new FormData();
  formData.append("file", req.file);
  formData.append(
    "metadata",
    JSON.stringify({
      id: req.patient.id,
      age: req.patient.age,
      sex: req.patient.sex,
      notes: req.patient.notes,
      demo: !!req.demo,
    }),
  );

  const response = await fetch(`${BACKEND_URL}${axis.endpoint}`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let detail = "Prediction failed";
    try {
      const err = (await response.json()) as { detail?: string };
      detail = err.detail ?? detail;
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(detail);
  }

  const data = (await response.json()) as AnalysisResult;
  return {
    ...data,
    generatedAt: data.generatedAt ?? new Date().toISOString(),
  };
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
