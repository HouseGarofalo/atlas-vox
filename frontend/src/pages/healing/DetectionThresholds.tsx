/**
 * DetectionThresholds — the detection threshold grid.
 *
 * Extracted from HealingPage.tsx as part of P2-20 (decompose large pages).
 */

import {
  Activity,
  AlertTriangle,
  BarChart3,
  Clock,
  Database,
  HardDrive,
  Server,
} from "lucide-react";
import type { HealingStatus } from "../../types";

export interface DetectionThresholdsProps {
  detector: NonNullable<HealingStatus["detector"]>;
}

export function DetectionThresholds({ detector }: DetectionThresholdsProps) {
  return (
    <>
      <p className="mb-4 text-sm text-[var(--color-text-secondary)]">
        Current detection thresholds (change via Admin &rarr; Self-Healing settings, then click Reconfigure)
      </p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <ThresholdCard
          label="Health Failures"
          value={String(detector.health_failure_threshold)}
          unit="consecutive"
          icon={<Activity className="h-4 w-4" />}
        />
        <ThresholdCard
          label="Error Rate Spike"
          value={`${detector.error_rate_spike_multiplier}x`}
          unit="baseline multiplier"
          icon={<BarChart3 className="h-4 w-4" />}
        />
        <ThresholdCard
          label="Latency P99"
          value={`${detector.latency_p99_threshold_ms}`}
          unit="ms"
          icon={<Clock className="h-4 w-4" />}
        />
        <ThresholdCard
          label="Errors/Minute"
          value={String(detector.errors_per_minute_threshold)}
          unit="per minute"
          icon={<AlertTriangle className="h-4 w-4" />}
        />
        <ThresholdCard
          label="Celery Backlog"
          value={String(detector.celery_backlog_threshold)}
          unit="pending tasks"
          icon={<Server className="h-4 w-4" />}
        />
        <ThresholdCard
          label="Memory Limit"
          value={String(detector.memory_threshold_mb)}
          unit="MB RSS"
          icon={<Database className="h-4 w-4" />}
        />
        <ThresholdCard
          label="Disk Usage"
          value={`${detector.disk_usage_threshold_pct}%`}
          unit="capacity"
          icon={<HardDrive className="h-4 w-4" />}
        />
      </div>
    </>
  );
}

interface ThresholdCardProps {
  label: string;
  value: string;
  unit: string;
  icon: React.ReactNode;
}

function ThresholdCard({ label, value, unit, icon }: ThresholdCardProps) {
  return (
    <div className="rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg)] p-3 card-styled">
      <div className="flex items-center gap-2 mb-1 text-[var(--color-text-secondary)]">
        {icon}
        <span className="text-xs font-medium">{label}</span>
      </div>
      <p className="text-lg font-bold">{value}</p>
      <p className="text-[10px] text-[var(--color-text-secondary)]">{unit}</p>
    </div>
  );
}
