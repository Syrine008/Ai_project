import type { AxisId } from "./axes";
import type { AnalysisResult } from "./mockApi";

export const REPORTS_STORAGE_KEY = "brain_axis_reports";

export interface SavedAnalysisReport {
  caseId: string;
  axisId: AxisId;
  axisTitle: string;
  patientId?: string | null;
  prediction: string;
  probabilities?: {
    alzheimerProbability?: number;
    healthyProbability?: number;
    decisionThreshold?: number;
    confidenceLevel?: string;
  };
  uploadedExamName?: string;
  generatedAt: string;
  selectedSeries?: {
    selectedSeries?: string;
    seriesDescription?: string;
    modality?: string;
    numberOfSlices?: number;
    reasonSelected?: string;
  };
  clinicalMetadata?: AnalysisResult["clinicalMetadata"];
  cognitiveScoreInterpretation?: string | null;
  mriFeatures?: AnalysisResult["mriFeatures"];
  gradCamAvailable?: boolean;
  payload: AnalysisResult;
}

const canUseStorage = () => typeof window !== "undefined" && typeof window.localStorage !== "undefined";

export function loadSavedReports(): SavedAnalysisReport[] {
  if (!canUseStorage()) {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(REPORTS_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isSavedReport) : [];
  } catch {
    return [];
  }
}

export function saveAnalysisReport(report: SavedAnalysisReport): SavedAnalysisReport[] {
  if (!canUseStorage()) {
    return [];
  }

  const reports = loadSavedReports();
  const existingIndex = reports.findIndex((item) => item.caseId === report.caseId);
  const nextReports =
    existingIndex >= 0
      ? reports.map((item, index) => (index === existingIndex ? report : item))
      : [report, ...reports];

  window.localStorage.setItem(REPORTS_STORAGE_KEY, JSON.stringify(nextReports));
  return nextReports;
}

export function deleteSavedReport(caseId: string): SavedAnalysisReport[] {
  if (!canUseStorage()) {
    return [];
  }

  const nextReports = loadSavedReports().filter((report) => report.caseId !== caseId);
  window.localStorage.setItem(REPORTS_STORAGE_KEY, JSON.stringify(nextReports));
  return nextReports;
}

export function downloadReportJson(report: SavedAnalysisReport) {
  const patient = sanitizeFilePart(report.patientId || "unknown");
  downloadJson(report.payload, `axis1_report_${sanitizeFilePart(report.caseId)}_${patient}.json`);
}

export function downloadAllReportsJson(reports: SavedAnalysisReport[]) {
  downloadJson(reports, `brain_axis_reports_${new Date().toISOString().slice(0, 10)}.json`);
}

export function reportSearchText(report: SavedAnalysisReport) {
  return [
    report.caseId,
    report.patientId,
    report.axisTitle,
    report.prediction,
    report.uploadedExamName,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function downloadJson(payload: unknown, filename: string) {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return;
  }

  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

function sanitizeFilePart(value: string) {
  return value.trim().replace(/[^a-zA-Z0-9_-]+/g, "_") || "unknown";
}

function isSavedReport(value: unknown): value is SavedAnalysisReport {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<SavedAnalysisReport>;
  return Boolean(candidate.caseId && candidate.axisId && candidate.axisTitle && candidate.prediction && candidate.payload);
}
