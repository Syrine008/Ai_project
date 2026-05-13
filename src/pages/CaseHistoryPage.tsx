import { useEffect, useMemo, useState } from "react";
import { Download, FileText, Search, Trash2 } from "lucide-react";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  downloadReportJson,
  deleteSavedReport,
  loadSavedReports,
  reportSearchText,
  type SavedAnalysisReport,
} from "@/lib/reportStore";
import { toast } from "sonner";

const pct = (value?: number) =>
  typeof value === "number" && Number.isFinite(value) ? `${Math.round(value * 100)}%` : "Not available";

function confidence(report: SavedAnalysisReport) {
  return report.probabilities?.confidenceLevel || "Not available";
}

function primaryProbability(report: SavedAnalysisReport) {
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

export function CaseHistoryPage() {
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

  const handleDeleteReport = (caseId: string) => {
    if (!window.confirm("Delete this report? This action cannot be undone.")) {
      return;
    }
    setReports(deleteSavedReport(caseId));
    toast.success("Report deleted");
  };

  return (
    <Layout title="Case History" subtitle="All saved real analyses across patients and axes.">
      <div className="relative mb-5 max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          className="pl-9"
          placeholder="Search by case ID, patient, axis, prediction, or exam"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
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
          <div className="mt-3 font-medium">No matching analyses found.</div>
          <p className="mt-1 text-sm text-muted-foreground">Adjust the search to view saved real analyses.</p>
        </Card>
      ) : (
        <div className="overflow-hidden rounded-xl border bg-card">
          <table className="w-full text-sm">
            <thead className="bg-muted/60 text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-3 text-left">Case</th>
                <th className="px-4 py-3 text-left">Patient</th>
                <th className="px-4 py-3 text-left">Axis</th>
                <th className="px-4 py-3 text-left">Result</th>
                <th className="px-4 py-3 text-left">Probability</th>
                <th className="px-4 py-3 text-left">Confidence</th>
                <th className="px-4 py-3 text-left">Generated</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {filteredReports.map((report) => (
                <tr key={report.caseId} className="border-t transition-colors hover:bg-accent/30">
                  <td className="px-4 py-3 font-mono text-xs">{report.caseId}</td>
                  <td className="px-4 py-3">{report.patientId || "Unknown patient"}</td>
                  <td className="px-4 py-3">{report.axisTitle}</td>
                  <td className="px-4 py-3 text-muted-foreground">{report.prediction}</td>
                  <td className="px-4 py-3 tabular-nums">{primaryProbability(report)}</td>
                  <td className="px-4 py-3">{confidence(report)}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{reportDate(report.generatedAt)}</td>
                  <td className="px-4 py-3 text-right">
                    <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => downloadReportJson(report)}>
                      <Download className="h-4 w-4" /> JSON
                    </Button>
                    <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => handleDeleteReport(report.caseId)}>
                      <Trash2 className="h-4 w-4" /> Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
