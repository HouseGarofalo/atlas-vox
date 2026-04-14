import { forwardRef, useId, type TextareaHTMLAttributes } from "react";
import { clsx } from "clsx";

interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
  showCount?: boolean;
}

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ className, label, error, helperText, required, maxLength, showCount, value, id, ...props }, ref) => {
    const autoId = useId();
    const textareaId = id ?? autoId;
    const hasFooter = error || helperText || (showCount && maxLength);

    return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={textareaId} className="block text-sm font-medium text-[var(--color-text)]">
          {label}
          {required && <span className="text-[var(--color-error)] ml-0.5">*</span>}
        </label>
      )}
      <textarea
        ref={ref}
        id={textareaId}
        value={value}
        maxLength={maxLength}
        required={required}
        aria-required={required ? "true" : undefined}
        aria-invalid={error ? "true" : undefined}
        className={clsx(
          "w-full rounded-lg border bg-[var(--color-bg)] px-3 py-2 text-sm text-[var(--color-text)] transition-colors",
          "focus:outline-none focus:ring-1",
          error
            ? "border-[var(--color-error)] focus:border-[var(--color-error)] focus:ring-[var(--color-error)]"
            : "border-[var(--color-border)] focus:border-primary-500 focus:ring-primary-500",
          className
        )}
        {...props}
      />
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

TextArea.displayName = "TextArea";
