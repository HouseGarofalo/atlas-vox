import { clsx } from "clsx";
import type { HTMLAttributes } from "react";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        "rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg)] p-3 sm:p-4 card-styled",
        className
      )}
      {...props}
    />
  );
}
