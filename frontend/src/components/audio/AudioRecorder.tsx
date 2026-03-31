import { useState, useRef, useCallback } from "react";
import { Mic, Square, Play, Pause, Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../ui/Button";
import { AudioLevelMeter } from "./AudioLevelMeter";
import { createLogger } from "../../utils/logger";

const logger = createLogger("AudioRecorder");

interface AudioRecorderProps {
  onRecorded: (blob: Blob, filename: string) => void;
}

export function AudioRecorder({ onRecorded }: AudioRecorderProps) {
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [preview, setPreview] = useState<{ url: string; blob: Blob; name: string } | null>(null);
  const [playing, setPlaying] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval>>();
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const start = useCallback(async () => {
    logger.info("recording_start");
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setStream(mediaStream);
      const mr = new MediaRecorder(mediaStream, { mimeType: "audio/webm" });
      chunksRef.current = [];

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mr.onstop = () => {
        mediaStream.getTracks().forEach((t) => t.stop());
        setStream(null);
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const name = `recording_${Date.now()}.webm`;
        logger.info("recording_complete", { filename: name, size_bytes: blob.size });
        // Show preview instead of immediately uploading
        if (preview?.url) URL.revokeObjectURL(preview.url);
        setPreview({ url: URL.createObjectURL(blob), blob, name });
      };

      mediaRef.current = mr;
      mr.start(100);
      setRecording(true);
      setPreview(null);
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    } catch {
      logger.error("microphone_permission_denied");
      toast.error("Microphone access denied. Please allow microphone permissions and try again.");
    }
  }, [preview?.url]);

  const stop = useCallback(() => {
    logger.info("recording_stop", { elapsed_seconds: elapsed });
    mediaRef.current?.stop();
    setRecording(false);
    clearInterval(timerRef.current);
  }, [elapsed]);

  const handlePreviewPlay = useCallback(() => {
    if (!preview) return;
    if (!audioRef.current) {
      audioRef.current = new Audio(preview.url);
      audioRef.current.onended = () => setPlaying(false);
    }
    if (playing) {
      audioRef.current.pause();
      setPlaying(false);
    } else {
      audioRef.current.play();
      setPlaying(true);
    }
  }, [preview, playing]);

  const handleAccept = useCallback(() => {
    if (!preview) return;
    onRecorded(preview.blob, preview.name);
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    URL.revokeObjectURL(preview.url);
    setPreview(null);
    setPlaying(false);
  }, [preview, onRecorded]);

  const handleDiscard = useCallback(() => {
    if (!preview) return;
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    URL.revokeObjectURL(preview.url);
    setPreview(null);
    setPlaying(false);
  }, [preview]);

  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <div className="space-y-2">
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

      {recording && (
        <>
          <AudioLevelMeter stream={stream} />
          <p className="text-xs text-[var(--color-text-secondary)]">
            Speak clearly, keep 6-12 inches from mic. Minimize background noise.
          </p>
        </>
      )}

      {preview && !recording && (
        <div className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary,var(--color-bg))] p-3">
          <Button variant="ghost" size="sm" onClick={handlePreviewPlay} aria-label={playing ? "Pause preview" : "Play preview"}>
            {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </Button>
          <span className="flex-1 text-sm text-[var(--color-text-secondary)]">Preview recording</span>
          <Button variant="secondary" size="sm" onClick={handleDiscard}>Discard</Button>
          <Button size="sm" onClick={handleAccept}>
            <Upload className="h-3 w-3" /> Upload
          </Button>
        </div>
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
