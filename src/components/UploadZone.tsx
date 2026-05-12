import { useCallback, useRef, useState } from "react";
import { UploadCloud, FileCheck2, X } from "lucide-react";
import { cn } from "@/lib/utils";

export function UploadZone({
  accept,
  hint,
  onFile,
}: {
  accept: string;
  hint?: string;
  onFile?: (f: File | null) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [file, setFile] = useState<File | null>(null);

  const handleFile = useCallback(
    (f: File | null) => {
      setFile(f);
      onFile?.(f);
    },
    [onFile],
  );

  return (
    <div>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files?.[0];
          if (f) handleFile(f);
        }}
        className={cn(
          "relative cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-all",
          "bg-card/40 hover:bg-card",
          drag
            ? "border-primary bg-accent/40 scale-[1.01]"
            : "border-border",
        )}
      >
        {file ? (
          <div className="flex items-center justify-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-teal/20 grid place-items-center">
              <FileCheck2 className="h-5 w-5 text-teal" />
            </div>
            <div className="text-left">
              <div className="text-sm font-medium">{file.name}</div>
              <div className="text-xs text-muted-foreground">
                {(file.size / 1024 / 1024).toFixed(2)} MB · ready to analyze
              </div>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                handleFile(null);
              }}
              className="ml-2 h-8 w-8 grid place-items-center rounded-md hover:bg-accent"
              aria-label="Remove file"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <>
            <div className="mx-auto h-12 w-12 rounded-full bg-gradient-hero grid place-items-center shadow-glow">
              <UploadCloud className="h-6 w-6 text-white" />
            </div>
            <p className="mt-3 text-sm font-medium">
              Drop your file here, or <span className="text-primary">browse</span>
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {hint ?? `Accepted: ${accept}`}
            </p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
        />
      </div>
    </div>
  );
}
