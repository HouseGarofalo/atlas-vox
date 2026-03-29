import { forwardRef, type ButtonHTMLAttributes } from "react";
import { clsx } from "clsx";

const variants = {
  primary: "bg-primary-500 text-white hover:bg-primary-600 focus:ring-primary-300",
  secondary: "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600",
  danger: "bg-red-500 text-white hover:bg-red-600 focus:ring-red-300",
  ghost: "text-[var(--color-text-secondary)] hover:bg-gray-100 dark:hover:bg-gray-800",
} as const;

const sizes = {
  sm: "h-9 px-3 text-xs",
  md: "h-11 px-4 text-sm",
  lg: "h-12 px-6 text-base",
} as const;

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", disabled, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1",
        variants[variant],
        sizes[size],
        disabled && "cursor-not-allowed opacity-50",
        className
      )}
      {...props}
    />
  )
);

Button.displayName = "Button";
