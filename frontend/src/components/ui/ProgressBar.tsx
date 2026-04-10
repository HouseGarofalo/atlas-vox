import { clsx } from "clsx";
import WaveformVisualizer from "../audio/WaveformVisualizer";

interface ProgressBarProps {
  percent: number;
  label?: string;
  className?: string;
  variant?: "default" | "studio" | "waveform";
  animated?: boolean;
}

export function ProgressBar({
  percent,
  label,
  className,
  variant = "default",
  animated = true
}: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, percent));

  if (variant === "studio") {
    return (
      <div className={clsx("space-y-3", className)}>
        {label && (
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-[var(--color-text)]">{label}</span>
            <span className="text-sm font-mono text-[var(--color-text-secondary)]">
              {Math.round(clamped)}%
            </span>
          </div>
        )}

        <div className="relative h-6 bg-studio-obsidian/50 rounded-xl overflow-hidden border border-studio-slate/30">
          {/* Background waveform */}
          <div className="absolute inset-0 flex items-center justify-center">
            <WaveformVisualizer
              height={24}
              barCount={20}
              animated={animated && clamped > 0}
              color="primary"
              className="w-full opacity-30"
            />
          </div>

          {/* Progress fill */}
          <div
            className="absolute inset-0 bg-gradient-to-r from-primary-500 via-secondary-400 to-electric-500 transition-all duration-500 ease-out"
            style={{ width: `${Math.max(clamped, 5)}%` }}
          />

          {/* Progress text overlay */}
          <div className="relative flex items-center justify-center h-full z-10">
            <span className="font-display font-bold text-white text-sm">
              {Math.round(clamped)}%
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (variant === "waveform") {
    return (
      <div className={clsx("space-y-2", className)}>
        {label && (
          <div className="flex justify-between text-xs text-[var(--color-text-secondary)]">
            <span>{label}</span>
            <span>{Math.round(clamped)}%</span>
          </div>
        )}

        <div className="relative h-12 bg-[var(--color-bg-secondary)] rounded-lg overflow-hidden border border-[var(--color-border)]">
          {/* Animated waveform bars */}
          <div className="absolute inset-0 flex items-end gap-px px-2 py-1">
            {Array.from({ length: 30 }, (_, i) => {
              const isActive = (i / 30) * 100 <= clamped;
              return (
                <div
                  key={i}
                  className={`flex-1 rounded-t transition-all duration-200 ${
                    isActive
                      ? "bg-gradient-to-t from-primary-500 to-primary-400 opacity-100"
                      : "bg-studio-slate/20 opacity-50"
                  }`}
                  style={{
                    height: `${isActive ? Math.sin(i * 0.3) * 40 + 60 : 20}%`,
                    animationDelay: `${i * 0.05}s`
                  }}
                />
              );
            })}
          </div>

          {/* Progress percentage */}
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="font-mono font-bold text-[var(--color-text)] text-sm">
              {Math.round(clamped)}%
            </span>
          </div>
        </div>
      </div>
    );
  }

  // Default variant
  return (
    <div className={clsx("space-y-2", className)}>
      {label && (
        <div className="flex justify-between text-sm text-[var(--color-text-secondary)]">
          <span className="font-medium">{label}</span>
          <span className="font-mono">{Math.round(clamped)}%</span>
        </div>
      )}
      <div className="h-3 overflow-hidden rounded-full bg-[var(--color-bg-secondary)] border border-[var(--color-border)]">
        <div
          className="h-full rounded-full bg-gradient-studio transition-all duration-500 ease-out relative overflow-hidden"
          style={{ width: `${clamped}%` }}
        >
          {animated && (
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse" />
          )}
        </div>
      </div>
    </div>
  );
}
