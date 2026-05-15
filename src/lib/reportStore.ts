import type { AxisId } from "./axes";
import type { AnalysisResult } from "./mockApi";

export const REPORTS_STORAGE_KEY = "brain_axis_reports";

export interface SavedAnalysisReport {
  caseId: string;
  axisId: AxisId;
  axisTitle: string;
  patientId?: string | null;
  prediction: string;
  probabilities?: AnalysisResult["probabilities"];
  uploadedExamName?: string;
  generatedAt: string;
  pdfExportedAt?: string;
  pdfFilename?: string;
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
  downloadJson(report.payload, `${sanitizeFilePart(report.axisId)}_${sanitizeFilePart(report.caseId)}_${patient}.json`);
}

export function downloadReportPdf(report: SavedAnalysisReport) {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return false;
  }

  const reportWindow = window.open("", "_blank", "width=980,height=1200");
  if (!reportWindow) {
    return false;
  }

  reportWindow.document.open();
  reportWindow.document.write(buildPrintableReportHtml(report));
  reportWindow.document.close();
  reportWindow.focus();
  reportWindow.setTimeout(() => {
    reportWindow.print();
  }, 250);
  return true;
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

function buildPrintableReportHtml(report: SavedAnalysisReport) {
  const payload = report.payload;
  const gradCamUrl = payload.gradCamDataUrl || payload.gradCam?.imageDataUrl;
  const confidenceRows = (payload.confidence || [])
    .map(
      (item) => `
        <tr>
          <td>${escapeHtml(item.label)}</td>
          <td>${formatPercent(item.value)}</td>
        </tr>`,
    )
    .join("");
  const regionRows = (payload.regions || [])
    .map(
      (region) => `
        <tr>
          <td>${escapeHtml(region.region)}</td>
          <td>${escapeHtml(region.side || "-")}</td>
          <td>${formatPercent(region.contribution)}</td>
          <td>${escapeHtml(region.note || "-")}</td>
        </tr>`,
    )
    .join("");

  return `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>${escapeHtml(report.pdfFilename || `${report.caseId}-report.pdf`)}</title>
    <style>
      body { font-family: Arial, sans-serif; color: #111827; margin: 32px; }
      h1 { font-size: 24px; margin: 0 0 8px; }
      h2 { font-size: 16px; margin: 24px 0 8px; }
      p { line-height: 1.45; }
      .meta { color: #4b5563; font-size: 12px; margin-bottom: 18px; }
      .summary { border: 1px solid #d1d5db; padding: 14px; border-radius: 8px; }
      table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12px; }
      th, td { border: 1px solid #d1d5db; padding: 8px; text-align: left; vertical-align: top; }
      th { background: #f3f4f6; }
      img { max-width: 100%; height: auto; border: 1px solid #d1d5db; border-radius: 8px; }
      .disclaimer { margin-top: 24px; font-size: 11px; color: #4b5563; }
      @page { margin: 18mm; }
    </style>
  </head>
  <body>
    <h1>${escapeHtml(report.axisTitle)}</h1>
    <div class="meta">
      Case ${escapeHtml(report.caseId)} | Patient ${escapeHtml(report.patientId || "Unknown")} | ${escapeHtml(formatDate(report.generatedAt))}
    </div>
    <div class="summary">
      <strong>${escapeHtml(report.prediction)}</strong>
      <p>${escapeHtml(payload.summary || "")}</p>
    </div>
    <h2>Confidence</h2>
    <table>
      <thead><tr><th>Label</th><th>Value</th></tr></thead>
      <tbody>${confidenceRows || `<tr><td colspan="2">Not available</td></tr>`}</tbody>
    </table>
    <h2>Grad-CAM Explainability Preview</h2>
    <p>Heatmap highlights image regions that influenced the CNN prediction.</p>
    ${gradCamUrl ? `<img src="${escapeAttribute(gradCamUrl)}" alt="Grad-CAM heatmap preview" />` : `<p>Explainability output is not available for this case yet.</p>`}
    <h2>Backend Region Output</h2>
    <table>
      <thead><tr><th>Region</th><th>Side</th><th>Contribution</th><th>Note</th></tr></thead>
      <tbody>${regionRows || `<tr><td colspan="4">Not available</td></tr>`}</tbody>
    </table>
    <div class="disclaimer">${escapeHtml(payload.disclaimer || "")}</div>
  </body>
</html>`;
}

function formatPercent(value?: number | null) {
  return typeof value === "number" && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : "Not available";
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function escapeHtml(value: string) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttribute(value: string) {
  return escapeHtml(value).replace(/`/g, "&#96;");
}

function isSavedReport(value: unknown): value is SavedAnalysisReport {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<SavedAnalysisReport>;
  return Boolean(candidate.caseId && candidate.axisId && candidate.axisTitle && candidate.prediction && candidate.payload);
}
