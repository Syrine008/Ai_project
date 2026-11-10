import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowRight, FileText, Brain } from "lucide-react";
import { Layout } from "@/components/Layout";
import { AxisCard } from "@/components/AxisCard";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AXES } from "@/lib/axes";
import { loadSavedReports, type SavedAnalysisReport } from "@/lib/reportStore";

export function DashboardPage() {
  const [reports, setReports] = useState<SavedAnalysisReport[]>([]);
  useEffect(() => {
    setReports(loadSavedReports());
  }, []);
  return (
    <Layout
      title="Clinical research workspace"
      subtitle="Prepare an examination, review model findings, and save a report."
    >
      <section className="rounded-2xl border bg-gradient-hero text-white p-6 sm:p-10">
        <Brain className="h-8 w-8 mb-4" />
        <p className="text-xs uppercase tracking-widest text-white/80">Cerebellum MRI</p>
        <h2 className="mt-2 text-2xl sm:text-3xl font-semibold">
          A clear path from scan to review
        </h2>
        <p className="mt-3 max-w-2xl text-white/85">
          Upload a 3D MRI, review the two-stage model output, and inspect the image regions that
          influenced the result.
        </p>
        <Button asChild className="mt-6 bg-white text-slate-900 hover:bg-white/90">
          <Link to="/axes/cerebellar-dysfunction">
            Start MRI analysis <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
      </section>
      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {[
          ["Saved reports", String(reports.length), "On this browser only"],
          ["Analysis workflows", String(AXES.length), "Availability depends on installed models"],
          ["Review required", "Research use", "Model outputs are not diagnoses"],
        ].map(([title, value, hint]) => (
          <Card key={title} className="p-5">
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-semibold mt-2">{value}</p>
            <p className="text-xs text-muted-foreground mt-2">{hint}</p>
          </Card>
        ))}
      </div>
      <section className="mt-8">
        <h2 className="text-lg font-semibold mb-4">Choose an analysis</h2>
        <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-5">
          {AXES.map((axis) => (
            <AxisCard key={axis.id} axis={axis} />
          ))}
        </div>
      </section>
      <section className="mt-8">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Recent saved reports</h2>
          <Link to="/reports" className="text-sm text-primary underline">
            View reports
          </Link>
        </div>
        {reports.length === 0 ? (
          <Card className="p-8 border-dashed text-center">
            <FileText className="mx-auto h-8 w-8 text-muted-foreground" />
            <p className="mt-3 font-medium">No saved reports yet</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Complete an analysis and choose Save report to keep it in this browser.
            </p>
          </Card>
        ) : (
          <div className="grid gap-3">
            {reports.slice(0, 4).map((report) => (
              <Card key={report.caseId} className="p-4 flex flex-wrap justify-between gap-3">
                <div>
                  <p className="font-medium">{report.axisTitle}</p>
                  <p className="text-sm text-muted-foreground">{report.prediction}</p>
                </div>
                <div className="text-xs text-muted-foreground">
                  <p>{report.caseId}</p>
                  <p>{new Date(report.generatedAt).toLocaleDateString()}</p>
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>
    </Layout>
  );
}
