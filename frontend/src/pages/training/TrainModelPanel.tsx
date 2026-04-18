/**
 * TrainModelPanel — "Start Training" button plus progress bar + helper text.
 *
 * Extracted from TrainingStudioPage.tsx as part of P2-20 (decompose large pages).
 */

import { Button } from "../../components/ui/Button";
import { ProgressBar } from "../../components/ui/ProgressBar";
import type { ReadinessResult } from "../../types";

export interface TrainingProgress {
  percent: number;
  status: string;
  state: string;
  error?: string | null;
}

export interface TrainModelPanelProps {
  onStart: () => void;
  disabled: boolean;
  readiness: ReadinessResult | null;
  progress: TrainingProgress | null | undefined;
}

export function TrainModelPanel({
  onStart,
  disabled,
  readiness,
  progress,
}: TrainModelPanelProps) {
  return (
    <div className="space-y-4">
      <Button onClick={onStart} disabled={disabled}>
        Start Training
      </Button>
      {readiness !== null && !readiness.ready && (
        <p className="text-xs text-[var(--color-text-secondary)]">
          Training is disabled until readiness requirements are met. See the Readiness
          panel above.
        </p>
      )}
      {progress && (
        <div className="space-y-2">
          <ProgressBar percent={progress.percent} label={progress.status} />
          {progress.error && <p className="text-sm text-red-500">{progress.error}</p>}
        </div>
      )}
    </div>
  );
}
