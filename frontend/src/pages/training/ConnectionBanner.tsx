/**
 * ConnectionBanner — the WebSocket status ribbon shown at the top of the
 * Training Studio page while a training job is active.
 *
 * Extracted from TrainingStudioPage.tsx as part of P2-20 (decompose large pages).
 */

export interface ConnectionBannerProps {
  message: string;
  status: string;
}

export function ConnectionBanner({ message, status }: ConnectionBannerProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="training-connection-banner"
      data-connection-status={status}
      className={`flex items-center gap-3 rounded-lg border p-3 text-sm ${
        status === "failed"
          ? "border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] text-[var(--color-danger)]"
          : "border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]"
      }`}
    >
      <span
        className={`h-2 w-2 rounded-full ${
          status === "polling"
            ? "bg-amber-400 animate-pulse"
            : status === "reconnecting"
              ? "bg-amber-400 animate-pulse"
              : "bg-red-400"
        }`}
      />
      <span>{message}</span>
    </div>
  );
}
