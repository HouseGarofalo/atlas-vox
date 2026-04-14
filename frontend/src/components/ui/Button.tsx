import { forwardRef, type ButtonHTMLAttributes } from "react";
import { clsx } from "clsx";

const variants = {
  primary: "bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-lg hover:shadow-xl hover:from-primary-600 hover:to-primary-700 transform hover:scale-105 transition-all duration-200",
  secondary: "bg-gradient-to-r from-secondary-400 to-secondary-500 text-studio-obsidian shadow-lg hover:shadow-xl hover:from-secondary-500 hover:to-secondary-600 transform hover:scale-105 transition-all duration-200",
  electric: "bg-gradient-to-r from-electric-500 to-electric-600 text-white shadow-lg hover:shadow-xl hover:from-electric-600 hover:to-electric-700 transform hover:scale-105 transition-all duration-200",
  glass: "bg-white/10 backdrop-blur-md text-[var(--color-text)] border border-white/20 hover:bg-white/20 hover:border-white/30 transition-all duration-200",
  console: "bg-gradient-console text-studio-silver border border-studio-slate hover:border-primary-500 hover:text-white transition-all duration-200",
  ghost: "text-[var(--color-text-secondary)] hover:bg-primary-500/10 hover:text-primary-600 transition-all duration-200",
  danger: "bg-gradient-to-r from-red-500 to-red-600 text-white shadow-lg hover:shadow-xl hover:from-red-600 hover:to-red-700 transform hover:scale-105 transition-all duration-200",
} as const;

const sizes = {
  sm: "h-9 px-4 text-xs font-medium",
  md: "h-11 px-6 text-sm font-medium",
  lg: "h-12 px-8 text-base font-semibold",
} as const;

const iconOnlySizes = {
  sm: "h-9 w-9",
  md: "h-11 w-11",
  lg: "h-12 w-12",
} as const;

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
  audioReactive?: boolean;
  loading?: boolean;
  iconOnly?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", disabled, audioReactive = false, loading = false, iconOnly = false, children, ...props }, ref) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        aria-busy={loading ? "true" : undefined}
        aria-disabled={isDisabled ? "true" : undefined}
        className={clsx(
          "inline-flex items-center justify-center rounded-lg font-display font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2",
          variants[variant],
          iconOnly ? iconOnlySizes[size] : clsx(sizes[size], "gap-2"),
          isDisabled && "opacity-50 cursor-not-allowed transform-none hover:scale-100",
          audioReactive && "relative overflow-hidden",
          className
        )}
        {...props}
      >
        {audioReactive && (
          <span aria-hidden="true" className="absolute inset-0 bg-gradient-to-r from-primary-400/20 via-secondary-400/20 to-electric-400/20 animate-spectrum opacity-0 hover:opacity-100 transition-opacity duration-300" />
        )}
        {loading && (
          <svg
            aria-hidden="true"
            className="h-4 w-4 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
