import { useState, useRef, useCallback } from "react";
import { Mic, Square, Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../ui/Button";
import { createLogger } from "../../utils/logger";

const logger = createLogger("AudioRecorder");

interface AudioRecorderProps {
  onRecorded: (blob: Blob, filename: string) => void;
}

export function AudioRecorder({ onRecorded }: AudioRecorderProps) {
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  const start = useCallback(async () => {
    logger.info("recording_start");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mr.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const name = `recording_${Date.now()}.webm`;
        logger.info("recording_complete", { filename: name, size_bytes: blob.size });
        onRecorded(blob, name);
      };

      mediaRef.current = mr;
      mr.start(100);
      setRecording(true);
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    } catch {
      logger.error("microphone_permission_denied");
      toast.error("Microphone access denied. Please allow microphone permissions and try again.");
    }
  }, [onRecorded]);

  const stop = useCallback(() => {
    logger.info("recording_stop", { elapsed_seconds: elapsed });
    mediaRef.current?.stop();
    setRecording(false);
    clearInterval(timerRef.current);
  }, [elapsed]);

  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <div className="flex items-center gap-3 rounded-lg border border-dashed border-[var(--color-border)] p-4">
      {recording ? (
        <>
          <div className="h-3 w-3 animate-pulse rounded-full bg-red-500" />
          <span className="text-sm font-mono">{fmt(elapsed)}</span>
          <Button variant="danger" size="sm" onClick={stop} aria-label="Stop recording">
            <Square className="h-3 w-3" /> Stop
          </Button>
        </>
      ) : (
        <Button variant="secondary" size="sm" onClick={start} aria-label="Start recording">
          <Mic className="h-4 w-4" /> Record Audio
        </Button>
      )}
    </div>
  );
}

interface FileUploaderProps {
  onFiles: (files: File[]) => void;
  accept?: string;
}

export function FileUploader({ onFiles, accept = "audio/*" }: FileUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files).filter((f) => f.type.startsWith("audio/"));
    if (files.length) {
      logger.info("file_upload_drop", { count: files.length });
      onFiles(files);
    }
  };

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      role="button"
      aria-label="Upload audio files"
      tabIndex={0}
      className="flex flex-col items-center gap-2 rounded-lg border-2 border-dashed border-[var(--color-border)] p-6 text-center hover:border-primary-400 transition-colors cursor-pointer"
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
    >
      <Upload className="h-8 w-8 text-[var(--color-text-secondary)]" />
      <p className="text-sm text-[var(--color-text-secondary)]">
        Drop audio files here or click to browse
      </p>
      <p className="text-xs text-[var(--color-text-secondary)]">WAV, MP3, FLAC, OGG</p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple
        aria-label="Choose audio files"
        className="hidden"
        onChange={(e) => {
          const files = Array.from(e.target.files || []);
          if (files.length) {
            logger.info("file_upload_browse", { count: files.length });
            onFiles(files);
          }
          e.target.value = "";
        }}
      />
    </div>
  );
}
