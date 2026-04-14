import { clsx } from "clsx";
import type { HTMLAttributes } from "react";

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "text" | "circular" | "rectangular" | "card";
  width?: string | number;
  height?: string | number;
  lines?: number;
  animated?: boolean;
}

export function Skeleton({
  className,
  variant = "rectangular",
  width,
  height,
  lines = 3,
  animated = true,
  ...props
}: SkeletonProps) {
  const baseClasses = clsx(
    "bg-[var(--color-border)] rounded-[var(--radius-sm)]",
    animated && "animate-pulse",
    className
  );

  const style = {
    width: typeof width === "number" ? `${width}px` : width,
    height: typeof height === "number" ? `${height}px` : height,
  };

  if (variant === "text") {
    const widths = ["100%", "92%", "76%", "84%", "68%"];
    return (
      <div role="status" aria-label="Loading" aria-busy="true" className="space-y-2" {...props}>
        {Array.from({ length: lines }, (_, i) => (
          <div
            key={i}
            className={baseClasses}
            style={{ width: widths[i % widths.length], height: "0.875rem" }}
          />
        ))}
        <span className="sr-only">Loading...</span>
      </div>
    );
  }

  if (variant === "circular") {
    return (
      <div
        role="status"
        aria-label="Loading"
        aria-busy="true"
        className={clsx(baseClasses, "rounded-full")}
        style={{ width: style.width ?? "48px", height: style.height ?? "48px" }}
        {...props}
      >
        <span className="sr-only">Loading...</span>
      </div>
    );
  }

  if (variant === "card") {
    return (
      <div
        role="status"
        aria-label="Loading"
        aria-busy="true"
        className={clsx(
          "rounded-[var(--radius)] border border-[var(--color-border)] p-6 space-y-4",
          animated && "animate-pulse",
          className
        )}
        {...props}
      >
        <div className="h-4 w-3/4 bg-[var(--color-border)] rounded-[var(--radius-sm)]" />
        <div className="h-3 w-full bg-[var(--color-border)] rounded-[var(--radius-sm)]" />
        <div className="h-3 w-5/6 bg-[var(--color-border)] rounded-[var(--radius-sm)]" />
        <span className="sr-only">Loading...</span>
      </div>
    );
  }

  // rectangular (default)
  return (
    <div
      role="status"
      aria-label="Loading"
      aria-busy="true"
      className={baseClasses}
      style={{ ...style, height: style.height ?? "2.5rem" }}
      {...props}
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
}
