import { clsx } from "clsx";

const colorMap: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
  training: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  ready: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
  error: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  archived: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300",
  queued: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
  completed: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
  failed: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  cancelled: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300",
  healthy: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
  unhealthy: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  revoked: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
  cloud: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300",
  local: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300",
  gpu: "bg-violet-100 text-violet-700 dark:bg-violet-900 dark:text-violet-300",
};

interface BadgeProps {
  status: string;
  className?: string;
}

export function Badge({ status, className }: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize",
        colorMap[status] || "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
        className
      )}
    >
      {status}
    </span>
  );
}
