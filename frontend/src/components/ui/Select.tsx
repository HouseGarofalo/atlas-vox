import { forwardRef, useId, type SelectHTMLAttributes } from "react";
import { clsx } from "clsx";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: { value: string; label: string }[];
  error?: string;
  helperText?: string;
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, options, error, helperText, placeholder, required, id, ...props }, ref) => {
    const autoId = useId();
    const selectId = id ?? autoId;
    const hasFooter = error || helperText;

    return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={selectId} className="block text-sm font-medium text-[var(--color-text)]">
          {label}
          {required && <span className="text-[var(--color-error)] ml-0.5">*</span>}
        </label>
      )}
      <select
        ref={ref}
        id={selectId}
        required={required}
        aria-required={required ? "true" : undefined}
        aria-invalid={error ? "true" : undefined}
        className={clsx(
          "h-10 w-full rounded-[var(--radius)] border bg-[var(--color-bg)] px-3 text-sm text-[var(--color-text)]",
          "focus:outline-none focus:ring-1",
          error
            ? "border-[var(--color-error)] focus:border-[var(--color-error)] focus:ring-[var(--color-error)]"
            : "border-[var(--color-border)] focus:border-primary-500 focus:ring-primary-500",
          className
        )}
        {...props}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {hasFooter && (
        <div>
          {error && <p className="text-xs text-[var(--color-error)]">{error}</p>}
          {!error && helperText && <p className="text-xs text-[var(--color-text-tertiary)]">{helperText}</p>}
        </div>
      )}
    </div>
    );
  }
);

Select.displayName = "Select";
