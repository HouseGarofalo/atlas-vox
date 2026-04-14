import { clsx } from "clsx";

type StatusCategory = "success" | "error" | "warning" | "info" | "neutral" | "accent";

const statusCategoryMap: Record<string, StatusCategory> = {
  // Success states
  ready: "success",
  completed: "success",
  healthy: "success",
  // Error states
  error: "error",
  failed: "error",
  unhealthy: "error",
  // Warning states
  pending: "warning",
  archived: "warning",
  cancelled: "warning",
  queued: "warning",
  // Info states
  training: "info",
  preprocessing: "info",
  // Neutral states
  revoked: "neutral",
  // Accent states
  cloud: "accent",
  local: "accent",
  gpu: "accent",
};

const categoryClasses: Record<StatusCategory, string> = {
  success: "bg-[var(--color-success-bg)] text-[var(--color-success)] border border-[var(--color-success-border)]",
  error: "bg-[var(--color-error-bg)] text-[var(--color-error)] border border-[var(--color-error-border)]",
  warning: "bg-[var(--color-warning-bg)] text-[var(--color-warning)] border border-[var(--color-warning-border)]",
  info: "bg-[var(--color-info-bg)] text-[var(--color-info)] border border-[var(--color-info-border)]",
  neutral: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 border border-transparent",
  accent: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300 border border-transparent",
};

interface BadgeProps {
  status: string;
  className?: string;
}

export function Badge({ status, className }: BadgeProps) {
  const category = statusCategoryMap[status] ?? "neutral";

  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize",
        categoryClasses[category],
        className
      )}
    >
      {status}
    </span>
  );
}
