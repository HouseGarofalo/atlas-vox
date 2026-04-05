import { useRef, useState, useEffect, useCallback } from "react";
import { Play, Pause, Square, SkipBack, Scissors, ZoomIn, ZoomOut } from "lucide-react";
import { Button } from "../ui/Button";
import { createLogger } from "../../utils/logger";

const logger = createLogger("AudioTimeline");

export interface Region {
  start: number;
  end: number;
}

interface AudioTimelineProps {
  src: string;
  onRegionChange?: (region: Region | null) => void;
  onReady?: (duration: number) => void;
}

export function AudioTimeline({ src, onRegionChange, onReady }: AudioTimelineProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<import("wavesurfer.js").default | null>(null);
  const regionsRef = useRef<ReturnType<typeof import("wavesurfer.js/dist/plugins/regions.js").default.create> | null>(null);
  const activeRegionRef = useRef<{ id: string; start: number; end: number; remove: () => void } | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [ready, setReady] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [region, setRegion] = useState<Region | null>(null);

  // Debounced region change callback
  const emitRegion = useCallback(
    (r: Region | null) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        setRegion(r);
        onRegionChange?.(r);
      }, 100);
    },
    [onRegionChange],
  );

  useEffect(() => {
    if (!containerRef.current) return;

    let ws: import("wavesurfer.js").default | undefined;
    let destroyed = false;

    const init = async () => {
      try {
        const [{ default: WaveSurfer }, { default: RegionsPlugin }] = await Promise.all([
          import("wavesurfer.js"),
          import("wavesurfer.js/dist/plugins/regions.js"),
        ]);
        if (destroyed) return;

        const regions = RegionsPlugin.create();
        regionsRef.current = regions;

        ws = WaveSurfer.create({
          container: containerRef.current!,
          waveColor: "rgba(99, 102, 241, 0.35)",
          progressColor: "rgba(99, 102, 241, 0.85)",
          cursorColor: "rgba(99, 102, 241, 0.9)",
          barWidth: 2,
          barGap: 1,
          barRadius: 2,
          height: 96,
          normalize: true,
          url: src,
          plugins: [regions],
        });

        ws.on("ready", () => {
          if (destroyed) return;
          const dur = ws!.getDuration();
          setDuration(dur);
          setReady(true);
          onReady?.(dur);
          logger.info("timeline_ready", { duration: dur });
        });

        ws.on("timeupdate", (time: number) => {
          if (!destroyed) setCurrentTime(time);
        });

        ws.on("play", () => { if (!destroyed) setPlaying(true); });
        ws.on("pause", () => { if (!destroyed) setPlaying(false); });
        ws.on("finish", () => { if (!destroyed) setPlaying(false); });
        ws.on("error", (err: Error) => {
          logger.error("timeline_error", { error: String(err) });
        });

        regions.enableDragSelection({
          color: "rgba(99, 102, 241, 0.15)",
        });

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        regions.on("region-created", (r: any) => {
          if (activeRegionRef.current && activeRegionRef.current.id !== r.id) {
            activeRegionRef.current.remove();
          }
          activeRegionRef.current = r;
          emitRegion({ start: r.start, end: r.end });
          logger.info("region_created", { start: r.start, end: r.end });
        });

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        regions.on("region-updated", (r: any) => {
          emitRegion({ start: r.start, end: r.end });
        });

        wsRef.current = ws;
      } catch (err) {
        logger.error("timeline_init_error", { error: String(err) });
      }
    };

    init();

    return () => {
      destroyed = true;
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (ws) { try { ws.destroy(); } catch { /* ignore */ } }
      wsRef.current = null;
      regionsRef.current = null;
      activeRegionRef.current = null;
      setReady(false);
      setPlaying(false);
      setCurrentTime(0);
      setDuration(0);
      setRegion(null);
    };
  }, [src]); // eslint-disable-line react-hooks/exhaustive-deps

  // Keyboard shortcuts
  useEffect(() => {
    const el = wrapperRef.current;
    if (!el) return;

    const handleKey = (e: KeyboardEvent) => {
      if (!ready) return;
      const ws = wsRef.current;
      if (!ws) return;

      switch (e.key) {
        case " ":
          e.preventDefault();
          ws.playPause();
          break;
        case "Home":
          e.preventDefault();
          ws.seekTo(0);
          break;
        case "End":
          e.preventDefault();
          ws.seekTo(1);
          break;
        case "ArrowLeft":
          e.preventDefault();
          ws.skip(-1);
          break;
        case "ArrowRight":
          e.preventDefault();
          ws.skip(1);
          break;
        case "Escape":
          clearRegion();
          break;
      }
    };

    el.addEventListener("keydown", handleKey);
    return () => el.removeEventListener("keydown", handleKey);
  }, [ready]); // eslint-disable-line react-hooks/exhaustive-deps

  const togglePlay = useCallback(() => {
    wsRef.current?.playPause();
  }, []);

  const stop = useCallback(() => {
    wsRef.current?.stop();
  }, []);

  const seekStart = useCallback(() => {
    wsRef.current?.seekTo(0);
  }, []);

  const zoomIn = useCallback(() => {
    setZoom((z) => {
      const next = Math.min(z * 1.5, 10);
      wsRef.current?.zoom(next * 50);
      return next;
    });
  }, []);

  const zoomOut = useCallback(() => {
    setZoom((z) => {
      const next = Math.max(z / 1.5, 1);
      wsRef.current?.zoom(next === 1 ? 0 : next * 50);
      return next;
    });
  }, []);

  const clearRegion = useCallback(() => {
    if (activeRegionRef.current) {
      activeRegionRef.current.remove();
      activeRegionRef.current = null;
    }
    setRegion(null);
    onRegionChange?.(null);
    logger.info("region_cleared");
  }, [onRegionChange]);

  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    const ms = Math.floor((s % 1) * 10);
    return `${m}:${sec.toString().padStart(2, "0")}.${ms}`;
  };

  return (
    <div
      ref={wrapperRef}
      className="space-y-3"
      tabIndex={0}
      role="application"
      aria-label="Audio waveform timeline. Use Space to play/pause, arrow keys to seek, Escape to clear selection."
    >
      {/* Waveform */}
      <div
        ref={containerRef}
        className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-2 overflow-x-auto"
        aria-label="Audio waveform"
      />

      {/* Transport controls */}
      <div className="flex items-center gap-2 flex-wrap" role="toolbar" aria-label="Playback controls">
        <Button variant="ghost" size="sm" onClick={seekStart} disabled={!ready} aria-label="Go to start">
          <SkipBack className="h-4 w-4" />
        </Button>
        <Button
          variant="primary"
          size="sm"
          onClick={togglePlay}
          disabled={!ready}
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 ml-0.5" />}
        </Button>
        <Button variant="ghost" size="sm" onClick={stop} disabled={!ready} aria-label="Stop">
          <Square className="h-3.5 w-3.5" />
        </Button>

        <span className="text-sm font-mono text-[var(--color-text-secondary)] min-w-[120px]" aria-live="polite" aria-label="Current time">
          {fmt(currentTime)} / {fmt(duration)}
        </span>

        <div className="flex items-center gap-1 ml-auto" role="group" aria-label="Zoom controls">
          <Button variant="ghost" size="sm" onClick={zoomOut} disabled={zoom <= 1} aria-label="Zoom out">
            <ZoomOut className="h-4 w-4" />
          </Button>
          <span className="text-xs text-[var(--color-text-secondary)] w-10 text-center">{zoom.toFixed(1)}x</span>
          <Button variant="ghost" size="sm" onClick={zoomIn} disabled={zoom >= 10} aria-label="Zoom in">
            <ZoomIn className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Region info */}
      {region && (
        <div className="flex items-center gap-3 rounded-lg border border-primary-200 bg-primary-50 dark:border-primary-800 dark:bg-primary-900/20 px-3 py-2 text-sm" role="status" aria-label="Selection range">
          <Scissors className="h-4 w-4 text-primary-500 shrink-0" />
          <span className="text-[var(--color-text-secondary)]">Selection:</span>
          <span className="font-mono">{fmt(region.start)} — {fmt(region.end)}</span>
          <span className="text-[var(--color-text-secondary)]">
            ({(region.end - region.start).toFixed(2)}s)
          </span>
          <Button variant="ghost" size="sm" onClick={clearRegion} className="ml-auto" aria-label="Clear selection">
            Clear
          </Button>
        </div>
      )}

      {!ready && (
        <div className="flex items-center justify-center h-12 text-sm text-[var(--color-text-secondary)]" role="status">
          Loading waveform...
        </div>
      )}
    </div>
  );
}
