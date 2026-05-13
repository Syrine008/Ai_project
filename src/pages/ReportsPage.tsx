import { useEffect, useMemo, useState } from "react";
import { Download, FileText, Search, Trash2 } from "lucide-react";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  downloadAllReportsJson,
  downloadReportJson,
  deleteSavedReport,
  loadSavedReports,
  reportSearchText,
  type SavedAnalysisReport,
} from "@/lib/reportStore";
import { toast } from "sonner";

const pct = (value?: number) =>
  typeof value === "number" && Number.isFinite(value) ? `${Math.round(value * 100)}%` : "Not available";

function reportMainProbability(report: SavedAnalysisReport) {
  const prediction = report.prediction.toLowerCase();
  if (prediction.includes("alzheimer-like")) {
    return pct(report.probabilities?.alzheimerProbability);
  }
  if (prediction.includes("healthy") || prediction.includes("non-demented")) {
    return pct(report.probabilities?.healthyProbability);
  }
  return pct(report.probabilities?.alzheimerProbability ?? report.probabilities?.healthyProbability);
}

function reportDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function ReportsPage() {
  const [reports, setReports] = useState<SavedAnalysisReport[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    setReports(loadSavedReports());
  }, []);

  const filteredReports = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) {
      return reports;
    }
    return reports.filter((report) => reportSearchText(report).includes(query));
  }, [reports, search]);

  const handleExportAll = () => {
    if (reports.length === 0) {
      toast.message("No real reports available yet. Run an analysis first.");
      return;
    }
    downloadAllReportsJson(reports);
  };

  const handleDeleteReport = (caseId: string) => {
    if (!window.confirm("Delete this report? This action cannot be undone.")) {
      return;
    }
    setReports(deleteSavedReport(caseId));
    toast.success("Report deleted");
  };

  return (
    <Layout title="Reports" subtitle="All decision-support reports across axes.">
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="relative min-w-64 flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Search by case ID, patient, axis, prediction, or exam"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <Button variant="outline" className="gap-1.5" onClick={handleExportAll}>
          <Download className="h-4 w-4" /> Export all
        </Button>
      </div>

      {reports.length === 0 ? (
        <Card className="border-dashed p-10 text-center">
          <FileText className="mx-auto h-10 w-10 text-bluegray" />
          <div className="mt-3 font-medium">No reports generated yet.</div>
          <p className="mt-1 text-sm text-muted-foreground">
            Run an Axis 1 MRI analysis to generate the first report.
          </p>
        </Card>
      ) : filteredReports.length === 0 ? (
        <Card className="border-dashed p-10 text-center">
          <FileText className="mx-auto h-10 w-10 text-bluegray" />
          <div className="mt-3 font-medium">No matching reports found.</div>
          <p className="mt-1 text-sm text-muted-foreground">Adjust the search to view saved real reports.</p>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredReports.map((report) => (
            <Card key={report.caseId} className="p-5 transition-shadow hover:shadow-elegant">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-[11px] uppercase tracking-wider text-bluegray">{report.axisTitle}</div>
                  <div className="mt-0.5 font-semibold">{report.prediction}</div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {report.patientId || "Unknown patient"} · {reportDate(report.generatedAt)}
                  </div>
                  {report.uploadedExamName && (
                    <div className="mt-1 text-xs text-muted-foreground">{report.uploadedExamName}</div>
                  )}
                </div>
                <div className="grid h-10 w-10 place-items-center rounded-lg bg-primary/10 text-primary">
                  <FileText className="h-5 w-5" />
                </div>
              </div>
              <div className="mt-4 flex items-center justify-between">
                <span className="font-mono text-xs">{report.caseId}</span>
                <span className="text-xs tabular-nums text-muted-foreground">
                  {reportMainProbability(report)}
                </span>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2">
                <Button variant="outline" className="gap-1.5" onClick={() => downloadReportJson(report)}>
                  <Download className="h-4 w-4" /> Download report
                </Button>
                <Button variant="outline" className="gap-1.5" onClick={() => handleDeleteReport(report.caseId)}>
                  <Trash2 className="h-4 w-4" /> Delete
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </Layout>
  );
}
