import { useState } from "react";
import { Download, FileText, Mail, Printer, Share2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { sendReportToPatient, type AnalysisResult } from "@/lib/mockApi";
import type { AxisId } from "@/lib/axes";

export function ReportExportPanel({
  result,
  axisId,
  axisTitle,
  patientEmail,
  patient,
}: {
  result: AnalysisResult;
  axisId?: AxisId;
  axisTitle?: string;
  patientEmail?: string;
  patient?: { id?: string; age?: number; sex?: "M" | "F" | "Other" };
}) {
  const [sending, setSending] = useState(false);
  const showPatientEmail =
    Boolean(patientEmail?.trim()) && Boolean(axisId) && Boolean(axisTitle);

  const handleSendPatientEmail = async () => {
    if (!axisId || !axisTitle || !patientEmail?.trim()) return;
    setSending(true);
    try {
      const { followUpNote } = await sendReportToPatient({
        to: patientEmail.trim(),
        axisId,
        axisTitle,
        patient,
        result,
      });
      toast.success("Summary sent", {
        description: followUpNote
          ? "Email included a gentle note to discuss results with a clinician."
          : `Delivered to ${patientEmail.trim()}`,
      });
    } catch (e) {
      toast.error("Could not send email", {
        description: e instanceof Error ? e.message : "Unknown error",
      });
    } finally {
      setSending(false);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${result.caseId}-report.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Report downloaded", { description: result.caseId });
  };
  return (
    <div className="rounded-xl border bg-gradient-card p-5 shadow-soft">
      <div className="flex items-start gap-3">
        <div className="h-10 w-10 rounded-lg bg-primary/10 grid place-items-center">
          <FileText className="h-5 w-5 text-primary" />
        </div>
        <div className="flex-1">
          <div className="font-medium">Decision-support report</div>
          <p className="text-xs text-muted-foreground mt-0.5">
            Includes prediction, confidence, explainability and clinician disclaimer.
          </p>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button onClick={handleDownload} className="gap-1.5">
          <Download className="h-4 w-4" /> Download report
        </Button>
        <Button variant="outline" onClick={() => window.print()} className="gap-1.5">
          <Printer className="h-4 w-4" /> Print
        </Button>
        {showPatientEmail && (
          <Button
            variant="default"
            className="gap-1.5 bg-teal-700 hover:bg-teal-800"
            disabled={sending}
            onClick={handleSendPatientEmail}
          >
            <Mail className="h-4 w-4" />
            {sending ? "Sending…" : "Send analysis to patient"}
          </Button>
        )}
        <Button
          variant="ghost"
          onClick={() => toast("Share link copied (demo)")}
          className="gap-1.5"
        >
          <Share2 className="h-4 w-4" /> Share
        </Button>
      </div>
    </div>
  );
}
