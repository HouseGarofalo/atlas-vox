import { forwardRef, type TextareaHTMLAttributes } from "react";
import { clsx } from "clsx";

interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ className, label, error, id, ...props }, ref) => (
    <div className="space-y-1">
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-[var(--color-text)]">
          {label}
        </label>
      )}
      <textarea
        ref={ref}
        id={id}
        className={clsx(
          "w-full rounded-lg border bg-[var(--color-bg)] px-3 py-2 text-sm text-[var(--color-text)] transition-colors",
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

TextArea.displayName = "TextArea";
