import { useRef, useState, useEffect } from "react";
import { Play, Pause, Volume2 } from "lucide-react";

interface AudioPlayerProps {
  src: string;
  compact?: boolean;
}

export function AudioPlayer({ src, compact }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    setPlaying(false);
    setProgress(0);
  }, [src]);

  const toggle = () => {
    const el = audioRef.current;
    if (!el) return;
    if (playing) {
      el.pause();
    } else {
      el.play();
    }
    setPlaying(!playing);
  };

  const onTimeUpdate = () => {
    const el = audioRef.current;
    if (!el) return;
    setProgress(el.currentTime);
    setDuration(el.duration || 0);
  };

  const onEnded = () => setPlaying(false);

  const seek = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = audioRef.current;
    if (!el || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    el.currentTime = pct * duration;
  };

  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <div className={`flex items-center gap-3 ${compact ? "" : "rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-3"}`}>
      <audio ref={audioRef} src={src} onTimeUpdate={onTimeUpdate} onEnded={onEnded} onLoadedMetadata={onTimeUpdate} />
      <button
        onClick={toggle}
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-500 text-white hover:bg-primary-600"
      >
        {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 ml-0.5" />}
      </button>
      <div className="flex flex-1 items-center gap-2">
        <span className="w-10 text-xs text-[var(--color-text-secondary)]">{fmt(progress)}</span>
        <div
          className="relative h-1.5 flex-1 cursor-pointer rounded-full bg-gray-200 dark:bg-gray-700"
          onClick={seek}
        >
          <div
            className="absolute inset-y-0 left-0 rounded-full bg-primary-500"
            style={{ width: duration ? `${(progress / duration) * 100}%` : "0%" }}
          />
        </div>
        <span className="w-10 text-xs text-[var(--color-text-secondary)]">{fmt(duration)}</span>
      </div>
      <Volume2 className="h-4 w-4 text-[var(--color-text-secondary)]" />
    </div>
  );
}
