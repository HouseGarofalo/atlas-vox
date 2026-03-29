import { useRef, useState, useEffect, useCallback } from "react";
import { Play, Pause, Volume2, VolumeX } from "lucide-react";
import { createLogger } from "../../utils/logger";

const logger = createLogger("AudioPlayer");

interface AudioPlayerProps {
  src: string;
  compact?: boolean;
}

export function AudioPlayer({ src, compact }: AudioPlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<any>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [muted, setMuted] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;

    let ws: any;
    let destroyed = false;

    const init = async () => {
      try {
        const WaveSurfer = (await import("wavesurfer.js")).default;
        if (destroyed) return;

        ws = WaveSurfer.create({
          container: containerRef.current!,
          waveColor: "rgba(99, 102, 241, 0.4)",
          progressColor: "rgba(99, 102, 241, 1)",
          cursorColor: "rgba(99, 102, 241, 0.8)",
          barWidth: 2,
          barGap: 1,
          barRadius: 2,
          height: compact ? 32 : 48,
          normalize: true,
          url: src,
        });

        ws.on("ready", () => {
          if (destroyed) return;
          setDuration(ws.getDuration());
          setReady(true);
          logger.info("waveform_ready", { duration: ws.getDuration() });
        });

        ws.on("timeupdate", (time: number) => {
          if (!destroyed) setCurrentTime(time);
        });

        ws.on("play", () => { if (!destroyed) setPlaying(true); });
        ws.on("pause", () => { if (!destroyed) setPlaying(false); });
        ws.on("finish", () => {
          if (!destroyed) { setPlaying(false); logger.info("audio_ended"); }
        });
        ws.on("error", (err: any) => {
          logger.error("waveform_error", { error: String(err), src });
        });

        wavesurferRef.current = ws;
      } catch (err) {
        logger.error("wavesurfer_init_error", { error: String(err) });
      }
    };

    init();

    return () => {
      destroyed = true;
      if (ws) {
        try { ws.destroy(); } catch {}
      }
      wavesurferRef.current = null;
      setReady(false);
      setPlaying(false);
      setCurrentTime(0);
      setDuration(0);
    };
  }, [src, compact]);

  const toggle = useCallback(() => {
    const ws = wavesurferRef.current;
    if (!ws || !ready) return;
    ws.playPause();
  }, [ready]);

  const toggleMute = useCallback(() => {
    const ws = wavesurferRef.current;
    if (!ws) return;
    const next = !muted;
    ws.setMuted(next);
    setMuted(next);
  }, [muted]);

  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <div className={`flex items-center gap-3 ${compact ? "" : "rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-3"}`}>
      <button
        onClick={toggle}
        disabled={!ready}
        aria-label={playing ? "Pause" : "Play"}
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-500 text-white hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 ml-0.5" />}
      </button>
      <div className="flex flex-1 flex-col gap-1 min-w-0">
        <div ref={containerRef} className="w-full" />
        <div className="flex justify-between text-xs text-[var(--color-text-secondary)]">
          <span>{fmt(currentTime)}</span>
          <span>{fmt(duration)}</span>
        </div>
      </div>
      <button
        onClick={toggleMute}
        className="shrink-0 rounded p-1 text-[var(--color-text-secondary)] hover:bg-gray-100 dark:hover:bg-gray-800"
        aria-label={muted ? "Unmute" : "Mute"}
      >
        {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
      </button>
    </div>
  );
}
