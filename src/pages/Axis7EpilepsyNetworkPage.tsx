import { useEffect, useRef, useState } from "react";
import { ArrowRight, FileCheck2, FolderOpen, Sparkles, X } from "lucide-react";
import { toast } from "sonner";
import { Layout } from "@/components/Layout";
import { AnalysisStatusCard } from "@/components/AnalysisStatusCard";
import { ResultCard } from "@/components/ResultCard";
import { RegionTable } from "@/components/RegionTable";
import { ConfidenceBars } from "@/components/ConfidenceBars";
import { SignalChart } from "@/components/SignalChart";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { getAxisById } from "@/lib/axes";
import { type AnalysisResult } from "@/lib/mockApi";
import { cn } from "@/lib/utils";

type Stage = "idle" | "running" | "done";

type Axis7Context = {
  subjectId: string;
  session: string;
  run: string;
  localFolderPath: string;
  notes: string;
};

type Axis7Xai = {
  dominantEegChannel?: string;
  igDominantEegChannel?: string;
  importantTimeSegment?: { start: number; end: number } | null;
  attentionWeights?: Array<{ label: string; value: number }>;
  modalityOcclusion?: Array<{ label: string; value: number; ablatedProbability?: number }>;
  gradcam?: Array<{ t: number; v: number }>;
  integratedGradients?: {
    channelImportance?: Array<{ label: string; value: number }>;
    heatmap?: Array<{ channel: string; t: number; v: number }>;
  };
  fmri?: {
    table?: Array<{ feature: string; value: string | number }>;
    meanTopVoxels?: Array<Record<string, string | number>>;
    stdTopVoxels?: Array<Record<string, string | number>>;
    images?: Array<{ title: string; dataUrl: string }>;
    temporalProfile?: Array<{ t: number; v: number }>;
    interpretation?: string;
  };
  peakWindow?: { start: number; midpoint: number; probability: number };
};

type Axis7Result = AnalysisResult & {
  xai?: Axis7Xai;
};

type SelectedAxis7File = File & {
  axis7RelativePath?: string;
  webkitRelativePath?: string;
};

const SUPPORTED_IMPORT_RE = /\.(edf|bdf|csv|json|tsv|zip|nii|nii\.gz)$/i;

function relativePathFor(file: File): string {
  const selected = file as SelectedAxis7File;
  return selected.axis7RelativePath || selected.webkitRelativePath || file.name;
}

function withRelativePath(file: File, relativePath: string): File {
  (file as SelectedAxis7File).axis7RelativePath = relativePath.replace(/^\/+/, "");
  return file;
}

function parseIdentityFromName(name: string): Partial<Axis7Context> {
  const subject = name.match(/(sub-[A-Za-z0-9]+)/i)?.[1] ?? "";
  const session = name.match(/(ses-[A-Za-z0-9]+)/i)?.[1] ?? "";
  const runPart = name.match(/run-([A-Za-z0-9]+)/i)?.[1] ?? "";
  return {
    subjectId: subject,
    session,
    run: runPart ? `run-${runPart}` : "",
  };
}

function severityClasses(severity: "low" | "moderate" | "high") {
  if (severity === "high") return "bg-destructive/10 text-destructive border-destructive/20";
  if (severity === "moderate") {
    return "bg-[oklch(0.78_0.16_70/0.12)] text-foreground border-[oklch(0.78_0.16_70/0.28)]";
  }
  return "bg-teal/10 text-foreground border-teal/20";
}

async function runAxis7AnalysisRequest(files: File[], context: Axis7Context): Promise<AnalysisResult> {
  const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();

  const fd = new FormData();
  fd.append(
    "metadata",
    JSON.stringify({
      subjectId: context.subjectId || null,
      session: context.session || null,
      run: context.run || null,
      localFolderPath: files.length ? null : context.localFolderPath.trim() || null,
      notes: context.notes.trim() || null,
      uploadMode: "folder",
    }),
  );
  for (const file of files) {
    fd.append("files", file, relativePathFor(file));
  }

  const endpoint = "/api/axis7-epilepsy-network/analyze/";
  const apiRoot = baseUrl || "http://127.0.0.1:8000";
  const url = `${apiRoot.replace(/\/$/, "")}${endpoint}`;
  const res = await fetch(url, { method: "POST", body: fd });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Axis 7 upload failed (${res.status}).`);
  }
  const data = (await res.json()) as AnalysisResult;
  if (!data.generatedAt) {
    data.generatedAt = new Date().toISOString();
  }
  return data;
}

function FolderUploadZone({
  files,
  onFiles,
  onFolderScan,
}: {
  files: File[];
  onFiles: (files: File[]) => void;
  onFolderScan: (files: File[]) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [readingFolder, setReadingFolder] = useState(false);
  const totalSize = files.reduce((sum, file) => sum + file.size, 0);
  const firstPath = files[0] ? relativePathFor(files[0]) : "";

  useEffect(() => {
    const input = inputRef.current;
    if (!input) return;
    (input as HTMLInputElement & { webkitdirectory?: boolean; directory?: boolean }).webkitdirectory = true;
    (input as HTMLInputElement & { webkitdirectory?: boolean; directory?: boolean }).directory = true;
    input.setAttribute("webkitdirectory", "");
    input.setAttribute("directory", "");
    input.setAttribute("mozdirectory", "");
  }, []);

  const handleFiles = (list: FileList | File[] | null) => {
    const incoming = Array.from(list ?? []);
    onFolderScan(incoming);
    const nextFiles = incoming.filter((file) => SUPPORTED_IMPORT_RE.test(relativePathFor(file)));
    if (incoming.length > 0 && nextFiles.length === 0) {
      toast.error("No supported Axis 7 files found. Use EDF/BDF/CSV, BIDS JSON/TSV, NIfTI, or ZIP.");
    }
    onFiles(nextFiles);
  };

  const collectDirectoryFiles = async (
    directoryHandle: any,
    currentPath: string,
  ): Promise<File[]> => {
    const collected: File[] = [];
    for await (const [name, handle] of directoryHandle.entries()) {
      const nextPath = `${currentPath}/${name}`;
      if (handle.kind === "file") {
        const file = await handle.getFile();
        collected.push(withRelativePath(file, nextPath));
      } else if (handle.kind === "directory") {
        collected.push(...(await collectDirectoryFiles(handle, nextPath)));
      }
    }
    return collected;
  };

  const openFolderPicker = async () => {
    const picker = (window as Window & { showDirectoryPicker?: (options?: { mode?: "read" }) => Promise<any> })
      .showDirectoryPicker;

    if (!picker) {
      inputRef.current?.click();
      return;
    }

    try {
      setReadingFolder(true);
      const directoryHandle = await picker({ mode: "read" });
      const folderFiles = await collectDirectoryFiles(directoryHandle, directoryHandle.name || "selected-folder");
      handleFiles(folderFiles);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      inputRef.current?.click();
    } finally {
      setReadingFolder(false);
    }
  };

  const readDroppedEntry = async (entry: any): Promise<File[]> => {
    if (!entry) return [];
    if (entry.isFile) {
      return new Promise((resolve) => {
        entry.file((file: File) => resolve([withRelativePath(file, entry.fullPath || file.name)]));
      });
    }
    if (!entry.isDirectory) return [];

    const reader = entry.createReader();
    const entries: any[] = [];
    let batch: any[] = [];
    do {
      batch = await new Promise<any[]>((resolve) => reader.readEntries(resolve));
      entries.push(...batch);
    } while (batch.length);

    const nested = await Promise.all(entries.map((child) => readDroppedEntry(child)));
    return nested.flat();
  };

  const handleDrop = async (items: DataTransferItemList, list: FileList) => {
    const entries = Array.from(items)
      .map((item) => ("webkitGetAsEntry" in item ? (item as any).webkitGetAsEntry() : null))
      .filter(Boolean);

    if (!entries.length) {
      handleFiles(list);
      return;
    }

    const nested = await Promise.all(entries.map((entry) => readDroppedEntry(entry)));
    handleFiles(nested.flat());
  };

  return (
    <div>
      <div
        onClick={() => {
          void openFolderPicker();
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDrag(false);
          void handleDrop(event.dataTransfer.items, event.dataTransfer.files);
        }}
        className={cn(
          "relative cursor-pointer rounded-xl border-2 border-dashed transition-all",
          "bg-card/40 hover:bg-card",
          files.length ? "p-4 text-left sm:p-5" : "p-8 text-center",
          drag ? "border-primary bg-accent/40 scale-[1.01]" : "border-border",
        )}
      >
        {files.length ? (
          <div className="flex w-full items-start gap-3">
            <div className="h-10 w-10 shrink-0 rounded-lg bg-teal/20 grid place-items-center">
              <FileCheck2 className="h-5 w-5 text-teal" />
            </div>
            <div className="min-w-0 flex-1 overflow-hidden text-left">
              <div className="font-mono text-xs font-medium leading-snug break-all text-foreground sm:text-sm">
                {firstPath.split("/")[0] || "Selected folder"}
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                {files.length} EDF/BDF files · {(totalSize / 1024 / 1024).toFixed(2)} MB
              </div>
            </div>
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onFiles([]);
              }}
              className="shrink-0 h-8 w-8 grid place-items-center rounded-md hover:bg-accent"
              aria-label="Remove folder"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <>
            <div className="mx-auto h-12 w-12 rounded-full bg-gradient-hero grid place-items-center shadow-glow">
              <FolderOpen className="h-6 w-6 text-white" />
            </div>
            <p className="mt-3 text-sm font-medium">
              {readingFolder ? "Reading patient folder…" : "Select patient run folder"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Choose the whole sub-01 folder or a patient run folder directly
            </p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onClick={(event) => {
            event.currentTarget.value = "";
          }}
          onChange={(event) => handleFiles(event.target.files)}
          {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
        />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            void openFolderPicker();
          }}
          className="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-accent"
        >
          Choose folder
        </button>
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            fileInputRef.current?.click();
          }}
          className="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-accent"
        >
          Choose files / zip
        </button>
        <span className="text-[11px] text-muted-foreground">
          Accepts folders, ZIPs, EDF/BDF, CSV, JSON/TSV, and NIfTI.
        </span>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".edf,.bdf,.csv,.json,.tsv,.zip,.nii,.nii.gz"
        className="hidden"
        onClick={(event) => {
          event.currentTarget.value = "";
        }}
        onChange={(event) => handleFiles(event.target.files)}
      />
    </div>
  );
}

function Axis7ContextForm({
  value,
  onChange,
}: {
  value: Axis7Context;
  onChange: (value: Axis7Context) => void;
}) {
  const update = (patch: Partial<Axis7Context>) => onChange({ ...value, ...patch });

  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="space-y-1.5">
        <Label htmlFor="axis7-subject" className="text-xs">Subject ID</Label>
        <Input
          id="axis7-subject"
          placeholder="sub-001"
          value={value.subjectId}
          onChange={(event) => update({ subjectId: event.target.value })}
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="axis7-session" className="text-xs">Session</Label>
        <Input
          id="axis7-session"
          placeholder="ses-01"
          value={value.session}
          onChange={(event) => update({ session: event.target.value })}
        />
      </div>
      <div className="space-y-1.5 col-span-2 sm:col-span-1">
        <Label htmlFor="axis7-run" className="text-xs">Run</Label>
        <Input
          id="axis7-run"
          placeholder="run-01"
          value={value.run}
          onChange={(event) => update({ run: event.target.value })}
        />
      </div>
      <div className="space-y-1.5 col-span-2">
        <Label htmlFor="axis7-local-folder" className="text-xs">Local folder path (optional)</Label>
        <Input
          id="axis7-local-folder"
          placeholder="/home/yassine/Bureau/PiAI/ds005873/sub-001"
          value={value.localFolderPath}
          onChange={(event) => update({ localFolderPath: event.target.value })}
        />
        <div className="text-[11px] text-muted-foreground">
          Optional dev shortcut only. For demos on another computer, use the folder or ZIP upload above.
        </div>
      </div>
      <div className="space-y-1.5 col-span-2">
        <Label htmlFor="axis7-notes" className="text-xs">Clinical context (optional)</Label>
        <Textarea
          id="axis7-notes"
          rows={3}
          placeholder="Seizure type, review notes, or why this patient/run is being analyzed…"
          value={value.notes}
          onChange={(event) => update({ notes: event.target.value })}
        />
      </div>
    </div>
  );
}

function EpilepsyTimeline({ result }: { result: AnalysisResult }) {
  if (!result.timeline?.length) return null;

  return (
    <Card className="p-5 space-y-4">
      <div>
        <div className="text-sm font-semibold">Instability timeline</div>
        <p className="text-xs text-muted-foreground mt-0.5">
          Highlighted windows mark the strongest seizure-like activity found across the uploaded recording.
        </p>
      </div>

      <div className="space-y-3">
        {result.timeline.map((marker, index) => (
          <div
            key={`${marker.label}-${index}`}
            className="flex flex-wrap items-center gap-3 rounded-xl border bg-card/70 px-4 py-3"
          >
            <div className="text-sm font-semibold tabular-nums min-w-16">
              {marker.t.toFixed(1)}s
            </div>
            <div className="min-w-0 flex-1 text-sm">{marker.label}</div>
            <span
              className={`rounded-full border px-2.5 py-1 text-[11px] font-medium capitalize ${severityClasses(marker.severity)}`}
            >
              {marker.severity}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

function EpilepsyNetworkGraph({
  network,
}: {
  network: NonNullable<AnalysisResult["network"]>;
}) {
  const { nodes, edges } = network;
  const cx = 150;
  const cy = 150;
  const r = 110;
  const positions = Object.fromEntries(
    nodes.map((node, index) => {
      const angle = (index / nodes.length) * Math.PI * 2 - Math.PI / 2;
      return [node, { x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r }];
    }),
  );

  return (
    <div className="rounded-xl border bg-card p-4 shadow-soft">
      <svg viewBox="0 0 300 300" className="w-full h-auto">
        {edges.map((edge, index) => {
          const from = positions[edge.from];
          const to = positions[edge.to];
          if (!from || !to) return null;
          return (
            <line
              key={`${edge.from}-${edge.to}-${index}`}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke={
                edge.weight > 0.7
                  ? "oklch(0.55 0.18 30)"
                  : edge.weight > 0.5
                    ? "oklch(0.72 0.10 200)"
                    : "oklch(0.65 0.03 250)"
              }
              strokeOpacity={0.55 + edge.weight * 0.4}
              strokeWidth={1 + edge.weight * 3}
            />
          );
        })}

        {nodes.map((node) => {
          const point = positions[node];
          return (
            <g key={node}>
              <circle
                cx={point.x}
                cy={point.y}
                r={18}
                fill="var(--primary)"
                className="drop-shadow"
              />
              <text
                x={point.x}
                y={point.y + 4}
                textAnchor="middle"
                fontSize="10"
                fill="var(--primary-foreground)"
                fontWeight="600"
              >
                {node.length > 10 ? `${node.slice(0, 8)}…` : node}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="mt-2 text-xs text-muted-foreground text-center">
        Nodes represent the most informative uploaded channels for this Axis 7 run.
      </div>
    </div>
  );
}

function XaiBarList({
  title,
  items,
}: {
  title: string;
  items: Array<{ label: string; value: number }>;
}) {
  if (!items.length) return null;
  const maxValue = Math.max(...items.map((item) => item.value), 0.001);

  return (
    <div className="space-y-3">
      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</div>
      {items.map((item) => (
        <div key={item.label} className="space-y-1.5">
          <div className="flex items-center justify-between gap-3 text-xs">
            <span className="font-medium">{item.label}</span>
            <span className="font-mono text-muted-foreground">{(item.value * 100).toFixed(1)}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-accent">
            <div
              className="h-full rounded-full bg-gradient-hero"
              style={{ width: `${Math.max(4, (item.value / maxValue) * 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function NotebookXaiPanel({ result }: { result: Axis7Result }) {
  const xai = result.xai;
  if (!xai) return null;

  const segmentLabel = xai.importantTimeSegment
    ? `${xai.importantTimeSegment.start.toFixed(2)}s → ${xai.importantTimeSegment.end.toFixed(2)}s`
    : "Not available";

  const occlusion = xai.modalityOcclusion ?? [];
  const attention = xai.attentionWeights ?? [];
  const igImportance = xai.integratedGradients?.channelImportance ?? [];
  const fmri = xai.fmri;

  return (
    <Card className="p-5 space-y-5">
      <div>
        <div className="text-sm font-semibold">Notebook XAI</div>
        <p className="text-xs text-muted-foreground mt-0.5">
          Same interpretation family as the notebook: dominant EEG channel, model-sensitive time segment, modality occlusion, and Grad-CAM focus.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="rounded-xl border bg-card/70 p-3">
          <div className="text-[11px] text-muted-foreground">Dominant EEG channel</div>
          <div className="mt-1 text-sm font-semibold">{xai.dominantEegChannel ?? "Not available"}</div>
        </div>
        <div className="rounded-xl border bg-card/70 p-3">
          <div className="text-[11px] text-muted-foreground">Important time segment</div>
          <div className="mt-1 text-sm font-semibold font-mono">{segmentLabel}</div>
        </div>
        <div className="rounded-xl border bg-card/70 p-3">
          <div className="text-[11px] text-muted-foreground">Peak window probability</div>
          <div className="mt-1 text-sm font-semibold">
            {xai.peakWindow ? `${(xai.peakWindow.probability * 100).toFixed(1)}%` : "Not available"}
          </div>
        </div>
      </div>

      <XaiBarList title="Modality occlusion drop" items={occlusion} />
      <XaiBarList title="Attention weights" items={attention} />
      <XaiBarList title="Integrated Gradients EEG importance" items={igImportance} />

      {xai.gradcam && xai.gradcam.length > 0 && (
        <div className="space-y-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">EEG Grad-CAM focus</div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Higher values mark the part of the peak window that most influenced the model output.
            </p>
          </div>
          <SignalChart data={xai.gradcam} />
        </div>
      )}

      {fmri && (
        <div className="space-y-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Post-hoc fMRI XAI</div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Notebook-style descriptive fMRI summary from the separate ds007313 derivative.
            </p>
          </div>

          {fmri.images && fmri.images.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {fmri.images.map((image) => (
                <div key={image.title} className="rounded-xl border bg-card/70 p-3">
                  <div className="text-xs font-medium mb-2">{image.title}</div>
                  <img src={image.dataUrl} alt={image.title} className="w-full rounded-lg border bg-black/5" />
                </div>
              ))}
            </div>
          )}

          {fmri.temporalProfile && fmri.temporalProfile.length > 0 && (
            <SignalChart data={fmri.temporalProfile} />
          )}

          {fmri.table && fmri.table.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {fmri.table.map((row) => (
                <div key={row.feature} className="rounded-lg border bg-card/70 px-3 py-2 text-xs">
                  <div className="text-muted-foreground">{row.feature}</div>
                  <div className="font-mono break-all">{String(row.value)}</div>
                </div>
              ))}
            </div>
          )}

          {fmri.interpretation && (
            <p className="text-xs leading-relaxed text-muted-foreground rounded-xl border bg-card/70 p-3">
              {fmri.interpretation}
            </p>
          )}
        </div>
      )}
    </Card>
  );
}

export function Axis7EpilepsyNetworkPage() {
  const axis = getAxisById("axis7-epilepsy-network");
  const Icon = axis.icon;

  const [files, setFiles] = useState<File[]>([]);
  const [context, setContext] = useState<Axis7Context>({
    subjectId: "",
    session: "",
    run: "",
    localFolderPath: "",
    notes: "",
  });
  const [stage, setStage] = useState<Stage>("idle");
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const handleFiles = (nextFiles: File[]) => {
    setFiles(nextFiles);
    if (!nextFiles.length) return;

    const identitySource = nextFiles
      .map((file) => relativePathFor(file))
      .join(" ");
    const parsed = parseIdentityFromName(identitySource);
    setContext((prev) => ({
      subjectId: prev.subjectId || parsed.subjectId || "",
      session: prev.session || parsed.session || "",
      run: prev.run || parsed.run || "",
      localFolderPath: prev.localFolderPath,
      notes: prev.notes,
    }));
  };

  const handleFolderScan = (scannedFiles: File[]) => {
    if (!scannedFiles.length) return;
    const identitySource = scannedFiles.map((file) => relativePathFor(file)).join(" ");
    const parsed = parseIdentityFromName(identitySource);
    setContext((prev) => ({
      subjectId: prev.subjectId || parsed.subjectId || "",
      session: prev.session || parsed.session || "",
      run: prev.run || parsed.run || "",
      localFolderPath:
        prev.localFolderPath,
      notes: prev.notes,
    }));
  };

  const handleRun = async () => {
    if (!files.length && !context.localFolderPath.trim()) {
      toast.error("Please select a folder, ZIP, or supported Axis 7 file.");
      return;
    }

    setStage("running");
    setResult(null);
    try {
      const response = await runAxis7AnalysisRequest(files, context);
      setResult(response);
      setStage("done");
      toast.success("Analysis complete", { description: response.predictedClass });
    } catch (error) {
      setStage("idle");
      const message = error instanceof Error && error.message ? error.message : "Axis 7 analysis failed.";
      toast.error(message);
    }
  };

  return (
    <Layout
      title={`Axis ${axis.number} · ${axis.title}`}
      subtitle={axis.purpose}
    >
      <div className="rounded-2xl border bg-gradient-card p-6 lg:p-8 shadow-soft">
        <div className="flex items-start gap-5">
          <div className={`h-14 w-14 rounded-2xl bg-gradient-to-br ${axis.accent} grid place-items-center shadow-glow text-white`}>
            <Icon className="h-7 w-7" />
          </div>
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-wider text-bluegray">
              Axis {String(axis.number).padStart(2, "0")} · {axis.input}
            </div>
            <h2 className="mt-0.5 text-2xl font-semibold tracking-tight text-balance">
              {axis.title}
            </h2>
            <p className="mt-2 text-sm text-muted-foreground max-w-3xl leading-relaxed">
              {axis.description}
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span className="px-2 py-0.5 rounded-full bg-accent/60">{axis.acceptedFormats}</span>
              <span className="px-2 py-0.5 rounded-full bg-accent/60 font-mono">{axis.endpoint}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <Card className="p-5">
            <div className="text-sm font-semibold mb-3">1. Select patient run folder</div>
            <FolderUploadZone files={files} onFiles={handleFiles} onFolderScan={handleFolderScan} />
            <div className="mt-3 text-[11px] text-muted-foreground leading-relaxed">
              Select a BIDS subject folder such as
              {" "}
              <span className="font-mono">sub-001</span>, a ZIP of that folder, or the signal/metadata files directly.
              Real EDF/BDF signals are used when present; metadata-only BIDS folders still produce a showcase result.
            </div>
          </Card>

          <Card className="p-5">
            <div className="text-sm font-semibold mb-3">2. Run context</div>
            <Axis7ContextForm value={context} onChange={setContext} />
          </Card>

          <Card className="p-5">
            <div className="text-sm font-semibold mb-3">3. Run</div>
            <Button
              onClick={handleRun}
              disabled={stage === "running"}
              className="w-full gap-2"
              size="lg"
            >
              <Sparkles className="h-4 w-4" />
              Run analysis
              <ArrowRight className="h-4 w-4 ml-auto" />
            </Button>
          </Card>
        </div>

        <div className="lg:col-span-2 space-y-6">
          {stage === "idle" && !result && (
            <Card className="p-10 text-center bg-gradient-card border-dashed">
              <Icon className="h-10 w-10 mx-auto text-bluegray" />
              <div className="mt-3 font-medium">No analysis yet</div>
              <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
                Select a patient run folder to visualize the epilepsy vulnerability output and notebook-style XAI.
              </p>
            </Card>
          )}

          {stage === "running" && (
            <AnalysisStatusCard stage="Patient-run parsing → multimodal model inference → vulnerability visualization" />
          )}

          {result && (
            <>
              <ResultCard result={result} />
              <NotebookXaiPanel result={result as Axis7Result} />

              <Card className="p-5 space-y-4">
                <div>
                  <div className="text-sm font-semibold">Confidence profile</div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Distribution of low, moderate, and high vulnerability interpretations for the current upload.
                  </p>
                </div>
                <ConfidenceBars items={result.confidence} />
              </Card>

              {result.signal && result.signal.length > 0 && (
                <Card className="p-5 space-y-4">
                  <div>
                    <div className="text-sm font-semibold">Signal explainability</div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Shaded spans mark the windows that contributed most strongly to the Axis 7 result.
                    </p>
                  </div>
                  <SignalChart data={result.signal} markers={result.timeline} />
                </Card>
              )}

              <EpilepsyTimeline result={result} />

              {result.regions && result.regions.length > 0 && (
                <Card className="p-5 space-y-4">
                  <div>
                    <div className="text-sm font-semibold">Channel contributions</div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Relative contribution of the most informative channels to the final vulnerability estimate.
                    </p>
                  </div>
                  <RegionTable regions={result.regions} />
                </Card>
              )}

              {result.network && result.network.nodes.length > 1 && (
                <Card className="p-5 space-y-4">
                  <div>
                    <div className="text-sm font-semibold">Epilepsy network view</div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Stronger edges indicate tighter coupling between the most informative channels in this uploaded run.
                    </p>
                  </div>
                  <EpilepsyNetworkGraph network={result.network} />
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </Layout>
  );
}
