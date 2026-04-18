/**
 * TrainingHistoryList — list of past + in-flight training jobs for a profile,
 * each with a Cancel button when applicable.
 *
 * Extracted from TrainingStudioPage.tsx as part of P2-20 (decompose large pages).
 */

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import type { TrainingJob } from "../../types";

export interface TrainingHistoryListProps {
  jobs: TrainingJob[];
  onCancel: (jobId: string) => void;
}

export function TrainingHistoryList({ jobs, onCancel }: TrainingHistoryListProps) {
  return (
    <div className="space-y-2">
      {jobs.map((job) => (
        <div
          key={job.id}
          className="flex items-center justify-between rounded border border-[var(--color-border)] p-3"
        >
          <div>
            <p className="text-sm font-medium">{job.provider_name}</p>
            <p className="text-xs text-[var(--color-text-secondary)]">
              {new Date(job.created_at).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge status={job.status} />
            {["queued", "training"].includes(job.status) && (
              <Button size="sm" variant="danger" onClick={() => onCancel(job.id)}>
                Cancel
              </Button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
