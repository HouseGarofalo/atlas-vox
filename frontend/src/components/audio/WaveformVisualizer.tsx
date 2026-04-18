import { useMemo } from "react";
import { useAudioPeaks } from "../../hooks/useAudioPeaks";

interface WaveformVisualizerProps {
  /**
   * Pre-computed peaks (normalized [0, 1]). Pass this when you've already
   * decoded the audio upstream or have peaks from the server.
   */
  data?: number[];
  /**
   * URL or Blob for an audio file. When provided (and no `data` is set),
   * the component decodes the audio via Web Audio API and renders real peaks.
   * A clipping indicator is shown when any sample is near full-scale.
   */
  source?: string | Blob | null;
  height?: number;
  barCount?: number;
  className?: string;
  animated?: boolean;
  color?: "primary" | "secondary" | "electric";
  /**
   * When true and no source/data is provided, falls back to a synthetic
   * sine shape (old behaviour). Useful for skeleton loaders.
   */
  synthetic?: boolean;
}

export function WaveformVisualizer({
  data,
  source,
  height = 40,
  barCount = 20,
  className = "",
  animated = true,
  color = "primary",
  synthetic = false,
}: WaveformVisualizerProps) {
  // Decode audio when a source was supplied and no caller-provided data.
  const decoded = useAudioPeaks(source ?? null, {
    barCount,
    enabled: !!source && !data,
  });

  const { peaks, clipping, silent, loading } = useMemo(() => {
    if (data && data.length > 0) {
      return {
        peaks: data.slice(0, barCount),
        clipping: false,
        silent: false,
        loading: false,
      };
    }
    if (decoded.peaks && decoded.peaks.length > 0) {
      return {
        peaks: decoded.peaks,
        clipping: decoded.clipping ?? false,
        silent: decoded.silent ?? false,
        loading: false,
      };
    }
    if (synthetic) {
      return {
        peaks: Array.from({ length: barCount }, (_, i) => Math.sin(i * 0.3) * 0.5 + 0.5),
        clipping: false,
        silent: false,
        loading: false,
      };
    }
    return {
      peaks: [] as number[],
      clipping: false,
      silent: false,
      loading: decoded.loading,
    };
  }, [data, decoded.peaks, decoded.clipping, decoded.silent, decoded.loading, synthetic, barCount]);

  const colorClasses = {
    primary: "from-primary via-primary/80 to-primary/60",
    secondary: "from-secondary via-secondary/80 to-secondary/60",
    electric: "from-electric via-electric/80 to-electric/60",
  };
  const gradientClass = clipping ? "from-red-500 via-red-400 to-red-300" : colorClasses[color];

  // Skeleton: show a flat low strip while decoding so height doesn't jump.
  const displayPeaks =
    peaks.length > 0
      ? peaks
      : Array.from({ length: barCount }, () => (loading ? 0.15 : 0.05));

  const ariaLabel = clipping
    ? "Audio waveform (clipping detected)"
    : silent
      ? "Audio waveform (silent)"
      : "Audio waveform";

  return (
    <div
      role="img"
      aria-label={ariaLabel}
      aria-hidden={!source && !data}
      className={`flex items-center justify-center gap-1 ${className}`}
      style={{ height: `${height}px` }}
      title={clipping ? "Clipping detected — audio exceeds full scale" : undefined}
    >
      {displayPeaks.map((amplitude, i) => {
        const barHeight = Math.max(amplitude * 100, 8); // Minimum 8% height
        return (
          <div
            key={i}
            className={`bg-gradient-to-t ${gradientClass} rounded-full transition-all duration-300 ${
              animated && !source && !data ? "hover:scale-110 group-hover:animate-pulse" : ""
            } ${loading ? "opacity-40 animate-pulse" : ""}`}
            style={{
              width: "var(--waveform-bar-width)",
              height: `${barHeight}%`,
              animationDelay: `${i * 0.05}s`,
            }}
          />
        );
      })}
    </div>
  );
}

export default WaveformVisualizer;
