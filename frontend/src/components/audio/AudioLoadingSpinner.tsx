interface AudioLoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  color?: "primary" | "secondary" | "electric";
  className?: string;
}

export function AudioLoadingSpinner({
  size = "md",
  color = "primary",
  className = ""
}: AudioLoadingSpinnerProps) {
  const sizeClasses = {
    sm: "h-4",
    md: "h-6",
    lg: "h-8"
  };

  const colorClasses = {
    primary: "from-primary-500 to-primary-600",
    secondary: "from-secondary-400 to-secondary-500",
    electric: "from-electric-500 to-electric-600"
  };

  const barCount = size === "sm" ? 5 : size === "md" ? 7 : 9;

  return (
    <div className={`flex items-end gap-1 ${className}`}>
      {Array.from({ length: barCount }, (_, i) => (
        <div
          key={i}
          className={`w-1 bg-gradient-to-t ${colorClasses[color]} rounded-full animate-bounce-random ${sizeClasses[size]}`}
          style={{
            animationDelay: `${i * 0.1}s`,
            animationDuration: `${0.6 + Math.random() * 0.2}s`
          }}
        />
      ))}
    </div>
  );
}

interface SynthesisProgressProps {
  progress: number;
  label?: string;
  className?: string;
}

export function SynthesisProgress({
  progress,
  label = "Processing",
  className = ""
}: SynthesisProgressProps) {
  return (
    <div className={`relative ${className}`}>
      <div className="h-20 bg-studio-obsidian/50 rounded-xl overflow-hidden border border-studio-slate/30">
        {/* Animated waveform background */}
        <div className="absolute inset-0 flex items-center justify-center gap-1">
          {Array.from({ length: 40 }, (_, i) => (
            <div
              key={i}
              className="bg-gradient-to-t from-primary-500/30 to-electric-500/50 rounded-full animate-pulse transition-all duration-300"
              style={{
                width: 'var(--waveform-bar-width)',
                height: `${Math.sin(i * 0.2) * 30 + 35}%`,
                animationDelay: `${i * 0.05}s`,
                opacity: i < (progress / 100) * 40 ? 1 : 0.3
              }}
            />
          ))}
        </div>

        {/* Progress overlay */}
        <div
          className="absolute inset-0 bg-gradient-to-r from-primary-500 via-secondary-400 to-electric-500 opacity-80 transition-all duration-500"
          style={{ width: `${Math.max(progress, 5)}%` }}
        />

        {/* Progress text */}
        <div className="relative flex items-center justify-center h-full z-10">
          <div className="text-center">
            <div className="font-display font-bold text-white text-lg mb-1">
              {progress.toFixed(0)}%
            </div>
            <div className="text-xs font-mono text-studio-silver uppercase tracking-wider">
              {label}
            </div>
          </div>
        </div>
      </div>

      {/* Processing status */}
      {progress > 0 && progress < 100 && (
        <div className="mt-3 flex items-center justify-center gap-2">
          <AudioLoadingSpinner size="sm" color="primary" />
          <span className="text-sm text-[var(--color-text-secondary)] font-mono">
            Processing audio stream...
          </span>
        </div>
      )}
    </div>
  );
}

export default AudioLoadingSpinner;