import { clsx } from "clsx";
import type { ReactNode } from "react";
import { Button } from "./Button";

interface EmptyStateAction {
  label: string;
  onClick: () => void;
  variant?: "primary" | "secondary" | "electric" | "glass" | "console" | "ghost" | "danger";
}

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: EmptyStateAction;
  secondaryAction?: EmptyStateAction;
  compact?: boolean;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  secondaryAction,
  compact = false,
  className,
}: EmptyStateProps) {
  return (
    <div
      role="status"
      className={clsx(
        "flex flex-col items-center justify-center text-center",
        compact ? "py-8" : "py-16",
        className
      )}
    >
      {icon && (
        <div className={clsx(
          "text-[var(--color-text-tertiary)]",
          compact ? "mb-3" : "mb-4"
        )}>
          {icon}
        </div>
      )}
      <h3 className={clsx(
        "font-display font-semibold text-[var(--color-text)]",
        compact ? "text-base" : "text-lg"
      )}>
        {title}
      </h3>
      {description && (
        <p className={clsx(
          "mt-2 max-w-md text-[var(--color-text-secondary)]",
          compact ? "text-xs" : "text-sm"
        )}>
          {description}
        </p>
      )}
      {(action || secondaryAction) && (
        <div className={clsx("flex items-center gap-3", compact ? "mt-4" : "mt-6")}>
          {action && (
            <Button
              variant={action.variant ?? "primary"}
              size={compact ? "sm" : "md"}
              onClick={action.onClick}
            >
              {action.label}
            </Button>
          )}
          {secondaryAction && (
            <Button
              variant={secondaryAction.variant ?? "ghost"}
              size={compact ? "sm" : "md"}
              onClick={secondaryAction.onClick}
            >
              {secondaryAction.label}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
