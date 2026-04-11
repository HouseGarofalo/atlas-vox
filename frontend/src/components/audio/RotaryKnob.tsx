import { useState, useCallback, useEffect, useRef } from "react";
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
  const knobRef = useRef<HTMLDivElement>(null);

  // Clamp and round value to step
  const clampValue = useCallback(
    (v: number) => Math.max(min, Math.min(max, Math.round(v / step) * step)),
    [min, max, step]
  );

  // Convert value to angle (270 degrees total range)
  const percentage = (value - min) / (max - min);
  const angle = percentage * 270 - 135; // -135 to +135 degrees

  // Calculate value from pointer position relative to knob center
  const valueFromPointer = useCallback(
    (clientX: number, clientY: number) => {
      const el = knobRef.current;
      if (!el) return value;
      const rect = el.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const deltaX = clientX - centerX;
      const deltaY = clientY - centerY;
      let mouseAngle = Math.atan2(deltaY, deltaX) * (180 / Math.PI);
      mouseAngle = ((mouseAngle + 135 + 360) % 360);
      if (mouseAngle > 270) mouseAngle = 270;
      const pct = mouseAngle / 270;
      return clampValue(min + pct * (max - min));
    },
    [min, max, value, clampValue]
  );

  // --- Mouse handlers (attached to document during drag) ---
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (disabled) return;
      e.preventDefault();
      setIsDragging(true);
      onChange(valueFromPointer(e.clientX, e.clientY));
    },
    [disabled, onChange, valueFromPointer]
  );

  useEffect(() => {
    if (!isDragging) return;
    const handleMouseMove = (e: MouseEvent) => {
      onChange(valueFromPointer(e.clientX, e.clientY));
    };
    const handleMouseUp = () => setIsDragging(false);
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, onChange, valueFromPointer]);

  // --- Touch handlers (attached to document during drag) ---
  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      if (disabled) return;
      e.preventDefault();
      setIsDragging(true);
      const touch = e.touches[0];
      onChange(valueFromPointer(touch.clientX, touch.clientY));
    },
    [disabled, onChange, valueFromPointer]
  );

  useEffect(() => {
    if (!isDragging) return;
    const handleTouchMove = (e: TouchEvent) => {
      const touch = e.touches[0];
      if (touch) onChange(valueFromPointer(touch.clientX, touch.clientY));
    };
    const handleTouchEnd = () => setIsDragging(false);
    document.addEventListener("touchmove", handleTouchMove, { passive: true });
    document.addEventListener("touchend", handleTouchEnd);
    document.addEventListener("touchcancel", handleTouchEnd);
    return () => {
      document.removeEventListener("touchmove", handleTouchMove);
      document.removeEventListener("touchend", handleTouchEnd);
      document.removeEventListener("touchcancel", handleTouchEnd);
    };
  }, [isDragging, onChange, valueFromPointer]);

  // --- Keyboard handler ---
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (disabled) return;
      let newValue: number | null = null;
      const bigStep = step * 10;
      switch (e.key) {
        case "ArrowUp":
        case "ArrowRight":
          newValue = clampValue(value + step);
          break;
        case "ArrowDown":
        case "ArrowLeft":
          newValue = clampValue(value - step);
          break;
        case "PageUp":
          newValue = clampValue(value + bigStep);
          break;
        case "PageDown":
          newValue = clampValue(value - bigStep);
          break;
        case "Home":
          newValue = min;
          break;
        case "End":
          newValue = max;
          break;
        default:
          return; // Don't prevent default for unhandled keys
      }
      e.preventDefault();
      if (newValue !== null) onChange(newValue);
    },
    [disabled, value, step, min, max, clampValue, onChange]
  );

  return (
    <div className={clsx("flex flex-col items-center gap-2", className)}>
      <div
        ref={knobRef}
        role="slider"
        tabIndex={disabled ? -1 : 0}
        aria-label={label}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
        aria-disabled={disabled}
        className={clsx(
          "rotary-knob",
          sizeClasses[size],
          isDragging && "cursor-grabbing",
          !disabled && "cursor-grab hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2",
          disabled && "opacity-50 cursor-not-allowed"
        )}
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
        onKeyDown={handleKeyDown}
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
          <span className="text-xs font-mono text-studio-silver uppercase tracking-wider">
            {label}
          </span>
          <div className="text-sm font-bold text-[var(--color-text)] mt-1">
            {typeof value === 'number' ? value.toFixed(step < 1 ? 2 : 0) : value}
          </div>
        </div>
      )}
    </div>
  );
}

export default RotaryKnob;
