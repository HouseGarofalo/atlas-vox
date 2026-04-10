import { useState } from "react";
import { clsx } from "clsx";

interface RotaryKnobProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  label?: string;
  colorFrom?: string;
  colorTo?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
  disabled?: boolean;
}

const sizeClasses = {
  sm: "w-12 h-12",
  md: "w-16 h-16",
  lg: "w-20 h-20"
};

export function RotaryKnob({
  value,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  label,
  colorFrom = "hsl(var(--studio-primary))",
  colorTo = "hsl(var(--studio-accent))",
  size = "md",
  className = "",
  disabled = false
}: RotaryKnobProps) {
  const [isDragging, setIsDragging] = useState(false);

  // Convert value to angle (270 degrees total range)
  const percentage = (value - min) / (max - min);
  const angle = percentage * 270 - 135; // -135 to +135 degrees

  const handleMouseDown = (e: React.MouseEvent) => {
    if (disabled) return;
    setIsDragging(true);
    e.preventDefault();
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || disabled) return;

    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    // Calculate angle from center
    const deltaX = e.clientX - centerX;
    const deltaY = e.clientY - centerY;
    let mouseAngle = Math.atan2(deltaY, deltaX) * (180 / Math.PI);

    // Normalize to 0-270 range
    mouseAngle = ((mouseAngle + 135 + 360) % 360);
    if (mouseAngle > 270) mouseAngle = 270;

    // Convert back to value
    const newPercentage = mouseAngle / 270;
    const newValue = Math.round((min + newPercentage * (max - min)) / step) * step;

    onChange(Math.max(min, Math.min(max, newValue)));
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  return (
    <div className={clsx("flex flex-col items-center gap-2", className)}>
      <div
        className={clsx(
          "rotary-knob",
          sizeClasses[size],
          isDragging && "cursor-grabbing",
          !disabled && "cursor-grab hover:shadow-lg",
          disabled && "opacity-50 cursor-not-allowed"
        )}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{
          "--from-color": colorFrom,
          "--to-color": colorTo
        } as React.CSSProperties}
      >
        {/* Knob gradient center */}
        <div className="knob-gradient" />

        {/* Indicator dot */}
        <div
          className="knob-indicator transition-transform duration-200"
          style={{
            transform: `translateX(-50%) rotate(${angle}deg) translateY(-${size === 'sm' ? '20' : size === 'md' ? '24' : '28'}px)`
          }}
        />

        {/* Center highlight */}
        <div className="absolute inset-4 rounded-full bg-gradient-to-br from-white/20 to-transparent" />
      </div>

      {label && (
        <div className="text-center">
          <label className="text-xs font-mono text-studio-silver uppercase tracking-wider">
            {label}
          </label>
          <div className="text-sm font-bold text-[var(--color-text)] mt-1">
            {typeof value === 'number' ? value.toFixed(step < 1 ? 2 : 0) : value}
          </div>
        </div>
      )}
    </div>
  );
}

export default RotaryKnob;