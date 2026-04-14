import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from "react";
import { clsx } from "clsx";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  success?: boolean;
  helperText?: string;
  leftIcon?: ReactNode;
  showCount?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, success, helperText, leftIcon, required, maxLength, showCount, value, id, ...props }, ref) => {
    const autoId = useId();
    const inputId = id ?? autoId;
    const hasFooter = error || helperText || (showCount && maxLength);

    return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-[var(--color-text)]">
          {label}
          {required && <span className="text-[var(--color-error)] ml-0.5">*</span>}
        </label>
      )}
      <div className="relative">
        {leftIcon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)]">
            {leftIcon}
          </div>
        )}
        <input
          ref={ref}
          id={inputId}
          value={value}
          maxLength={maxLength}
          required={required}
          aria-required={required ? "true" : undefined}
          aria-invalid={error ? "true" : undefined}
          className={clsx(
            "h-10 w-full rounded-[var(--radius)] border bg-[var(--color-bg)] px-3 text-sm text-[var(--color-text)] transition-colors",
            "focus:outline-none focus:ring-1",
            error
              ? "border-[var(--color-error)] focus:border-[var(--color-error)] focus:ring-[var(--color-error)]"
              : success
                ? "border-[var(--color-success)] focus:border-[var(--color-success)] focus:ring-[var(--color-success)]"
                : "border-[var(--color-border)] focus:border-primary-500 focus:ring-primary-500",
            leftIcon && "pl-10",
            className
          )}
          {...props}
        />
      </div>
      {hasFooter && (
        <div className="flex justify-between gap-2">
          <div className="flex-1">
            {error && <p className="text-xs text-[var(--color-error)]">{error}</p>}
            {!error && helperText && <p className="text-xs text-[var(--color-text-tertiary)]">{helperText}</p>}
          </div>
          {showCount && maxLength && (
            <span className={clsx(
              "text-xs tabular-nums shrink-0",
              typeof value === "string" && value.length > maxLength
                ? "text-[var(--color-error)]"
                : "text-[var(--color-text-tertiary)]"
            )}>
              {typeof value === "string" ? value.length : 0}/{maxLength}
            </span>
          )}
        </div>
      )}
    </div>
    );
  }
);

Input.displayName = "Input";
