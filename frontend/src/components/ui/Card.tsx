import { clsx } from "clsx";
import type { HTMLAttributes } from "react";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        "rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-4",
        className
      )}
      {...props}
    />
  );
}
