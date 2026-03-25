import { type InputHTMLAttributes } from "react";
import { clsx } from "clsx";

interface SliderProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: string;
  displayValue?: string;
}

export function Slider({ label, displayValue, className, id, ...props }: SliderProps) {
  return (
    <div className="space-y-1">
      {label && (
        <div className="flex items-center justify-between">
          <label htmlFor={id} className="text-sm font-medium text-[var(--color-text)]">
            {label}
          </label>
          {displayValue && <span className="text-xs text-[var(--color-text-secondary)]">{displayValue}</span>}
        </div>
      )}
      <input
        id={id}
        type="range"
        className={clsx("h-2 w-full cursor-pointer appearance-none rounded-lg bg-gray-200 accent-primary-500 dark:bg-gray-700", className)}
        {...props}
      />
    </div>
  );
}
