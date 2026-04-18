/**
 * TrainingReadinessPanel — the big readiness UI block (donut + recommendations).
 *
 * Extracted from TrainingStudioPage.tsx as part of P2-20 (decompose large pages).
 */

import type { ReadinessResult } from "../../types";

export interface TrainingReadinessPanelProps {
  readiness: ReadinessResult | null;
  loading: boolean;
}

export function TrainingReadinessPanel({
  readiness,
  loading,
}: TrainingReadinessPanelProps) {
  if (loading) {
    return (
      <p className="text-sm text-[var(--color-text-secondary)]">Checking readiness...</p>
    );
  }

  if (!readiness) {
    return (
      <p className="text-sm text-[var(--color-text-secondary)]">
        Add samples to check training readiness.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        {/* Circular progress indicator */}
        <div className="relative h-16 w-16 shrink-0">
          <svg className="h-16 w-16 -rotate-90" viewBox="0 0 36 36">
            <path
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="var(--color-border, #e5e7eb)"
              strokeWidth="3"
            />
            <path
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke={
                readiness.score >= 80
                  ? "#22c55e"
                  : readiness.score >= 50
                    ? "#f59e0b"
                    : "#ef4444"
              }
              strokeWidth="3"
              strokeDasharray={`${readiness.score}, 100`}
              strokeLinecap="round"
            />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-sm font-bold">
            {Math.round(readiness.score)}%
          </span>
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium">
            {readiness.ready ? "Ready to train" : "Not yet ready"}
          </p>
          <p className="text-xs text-[var(--color-text-secondary)]">
            {readiness.sample_count} samples, {readiness.total_duration.toFixed(1)}s total
            audio
          </p>
        </div>
      </div>
      {readiness.recommendations.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-[var(--color-text-secondary)]">
            Recommendations:
          </p>
          <ul className="space-y-1">
            {readiness.recommendations.map((rec, i) => (
              <li
                key={i}
                className="text-xs text-[var(--color-text-secondary)] flex items-start gap-1.5"
              >
                <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--color-text-secondary)]" />
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
