interface VUMeterProps {
  level?: number; // 0-100
  barCount?: number;
  height?: number;
  className?: string;
  animated?: boolean;
  decorative?: boolean;
  label?: string;
}

export function VUMeter({
  level = 0,
  barCount = 10,
  height = 20,
  className = "",
  decorative = false,
  label = "Volume level",
}: VUMeterProps) {
  const bars = Array.from({ length: barCount }, (_, i) => {
    const barLevel = (i + 1) / barCount * 100;
    const isActive = level >= barLevel;

    let color = "bg-led-green";
    if (barLevel > 70) color = "bg-led-yellow";
    if (barLevel > 85) color = "bg-led-red";

    return { isActive, color, level: barLevel };
  });

  const ariaProps = decorative
    ? { "aria-hidden": true as const }
    : {
        role: "meter" as const,
        "aria-label": label,
        "aria-valuenow": Math.round(level),
        "aria-valuemin": 0,
        "aria-valuemax": 100,
        "aria-valuetext": `${Math.round(level)} percent`,
      };

  return (
    <div
      className={`vu-meter ${className}`}
      style={{ height: `${height}px` }}
      {...ariaProps}
    >
      {bars.map((bar, i) => (
        <div
          key={i}
          className={`bar transition-all duration-75 ${
            bar.isActive
              ? `${bar.color} opacity-100`
              : "bg-studio-slate opacity-20"
          }`}
          style={{
            height: bar.isActive ? `${60 + bar.level * 0.4}%` : "20%"
          }}
        />
      ))}
    </div>
  );
}

export default VUMeter;
