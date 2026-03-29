import { forwardRef, type InputHTMLAttributes } from "react";
import { clsx } from "clsx";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, id, ...props }, ref) => (
    <div className="space-y-1">
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-[var(--color-text)]">
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={id}
        className={clsx(
          "h-10 w-full rounded-[var(--radius)] border bg-[var(--color-bg)] px-3 text-sm text-[var(--color-text)] transition-colors",
          "focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500",
          error ? "border-red-500" : "border-[var(--color-border)]",
          className
        )}
        {...props}
      />
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  )
);

Input.displayName = "Input";
