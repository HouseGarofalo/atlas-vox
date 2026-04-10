import { clsx } from "clsx";
import type { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "studio" | "console" | "glass" | "standard";
  waveform?: boolean;
}

export function Card({
  className,
  variant = "studio",
  waveform = false,
  children,
  ...props
}: CardProps) {
  const variantClasses = {
    studio: "studio-card",
    console: "studio-console text-white",
    glass: "studio-card backdrop-blur-md bg-white/10 dark:bg-studio-charcoal/10 border-white/20",
    standard: "bg-[var(--color-bg)] border border-[var(--color-border)]"
  };

  return (
    <div
      className={clsx(
        "rounded-lg p-4 sm:p-6 transition-all duration-500",
        variantClasses[variant],
        waveform && "waveform-bg group",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export default Card;
