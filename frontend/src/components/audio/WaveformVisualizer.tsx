interface WaveformVisualizerProps {
  data?: number[];
  height?: number;
  barCount?: number;
  className?: string;
  animated?: boolean;
  color?: "primary" | "secondary" | "electric";
}

export function WaveformVisualizer({
  data = [],
  height = 40,
  barCount = 20,
  className = "",
  animated = true,
  color = "primary"
}: WaveformVisualizerProps) {
  // Generate sample data if none provided
  const waveformData = data.length > 0
    ? data.slice(0, barCount)
    : Array.from({ length: barCount }, (_, i) => Math.sin(i * 0.3) * 0.5 + 0.5);

  const colorClasses = {
    primary: "from-primary via-primary/80 to-primary/60",
    secondary: "from-secondary via-secondary/80 to-secondary/60",
    electric: "from-electric via-electric/80 to-electric/60"
  };

  return (
    <div
      className={`flex items-center justify-center gap-1 ${className}`}
      style={{ height: `${height}px` }}
    >
      {waveformData.map((amplitude, i) => {
        const barHeight = Math.max(amplitude * 100, 8); // Minimum 8% height

        return (
          <div
            key={i}
            className={`bg-gradient-to-t ${colorClasses[color]} rounded-full transition-all duration-300 ${
              animated ? "hover:scale-110 group-hover:animate-pulse" : ""
            }`}
            style={{
              width: 'var(--waveform-bar-width)',
              height: `${barHeight}%`,
              animationDelay: `${i * 0.05}s`
            }}
          />
        );
      })}
    </div>
  );
}

export default WaveformVisualizer;