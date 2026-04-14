import { useEffect, useState } from "react";

interface AudioReactiveBackgroundProps {
  intensity?: "subtle" | "medium" | "high";
  className?: string;
}

export function AudioReactiveBackground({
  intensity = "subtle",
  className = ""
}: AudioReactiveBackgroundProps) {
  const [bars, setBars] = useState<number[]>([]);

  useEffect(() => {
    // Generate initial random heights for waveform bars
    const initialBars = Array.from({ length: 50 }, () => Math.random() * 60 + 10);
    setBars(initialBars);

    // Animate bars periodically
    const interval = setInterval(() => {
      setBars(prev => prev.map(() => Math.random() * 60 + 10));
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const intensityClasses = {
    subtle: "opacity-[0.03]",
    medium: "opacity-[0.06]",
    high: "opacity-[0.12]"
  };

  return (
    <div aria-hidden="true" className={`fixed inset-0 pointer-events-none overflow-hidden ${className}`}>
      {/* Gradient overlay */}
      <div className={`absolute inset-0 bg-gradient-radial from-primary/20 via-transparent to-electric/10 animate-pulse-slow ${intensityClasses[intensity]}`} />

      {/* Animated waveform bars */}
      <div className={`flex items-end justify-center h-full gap-1 px-8 ${intensityClasses[intensity]}`}>
        {bars.map((height, i) => (
          <div
            key={i}
            className="bg-gradient-to-t from-primary/40 via-secondary/30 to-electric/60 rounded-t-full animate-bounce-random transition-all duration-1000"
            style={{
              width: 'var(--waveform-bar-width)',
              height: `${height}%`,
              animationDelay: `${i * 0.05}s`,
              animationDuration: `${0.8 + Math.random() * 0.4}s`
            }}
          />
        ))}
      </div>

      {/* Floating particles */}
      <div className="absolute inset-0">
        {Array.from({ length: 12 }, (_, i) => (
          <div
            key={`particle-${i}`}
            className="absolute w-1 h-1 bg-primary/30 rounded-full animate-bounce-random"
            style={{
              left: `${10 + (i * 7)}%`,
              top: `${20 + Math.random() * 60}%`,
              animationDelay: `${i * 0.3}s`,
              animationDuration: `${2 + Math.random() * 2}s`
            }}
          />
        ))}
      </div>
    </div>
  );
}

export default AudioReactiveBackground;