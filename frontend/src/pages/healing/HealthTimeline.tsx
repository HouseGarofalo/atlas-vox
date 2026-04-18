/**
 * HealthTimeline — 24-hour incident frequency visualisation.
 *
 * Extracted from HealingPage.tsx as part of P2-20 (decompose large pages).
 */

import type { HealingIncident, HealingStatus } from "../../types";

export interface HealthTimelineProps {
  status: HealingStatus;
  incidents: HealingIncident[];
}

export function HealthTimeline({ status, incidents }: HealthTimelineProps) {
  // Build a 24-hour timeline with health status and incidents
  const now = Date.now();
  const hours24 = 24 * 60 * 60 * 1000;
  const startTime = now - hours24;

  // Group incidents by hour
  const hourlyIncidents: Record<number, HealingIncident[]> = {};
  incidents.forEach((incident) => {
    if (!incident.created_at) return;
    const ts = new Date(incident.created_at).getTime();
    if (ts < startTime) return;
    const hourBucket = Math.floor((ts - startTime) / (60 * 60 * 1000));
    if (!hourlyIncidents[hourBucket]) hourlyIncidents[hourBucket] = [];
    hourlyIncidents[hourBucket].push(incident);
  });

  return (
    <div className="space-y-3">
      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4 sm:grid-cols-5">
        <MiniStat label="Health Checks" value={String(status.health.checks_count)} />
        <MiniStat
          label="Consecutive Failures"
          value={String(status.health.consecutive_failures)}
          color={status.health.consecutive_failures > 0 ? "text-red-500" : undefined}
        />
        <MiniStat label="Avg Error Rate" value={`${status.telemetry.avg_error_rate}%`} />
        <MiniStat
          label="Errors (5m)"
          value={String(status.logs.errors_last_5_minutes)}
          color={status.logs.errors_last_5_minutes > 10 ? "text-red-500" : undefined}
        />
        <MiniStat label="Total Tracked" value={String(status.logs.total_tracked)} />
      </div>

      {/* Visual Timeline */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-[10px] text-[var(--color-text-secondary)]">
          <span>24h ago</span>
          <span>Now</span>
        </div>
        <div className="flex gap-0.5 h-8">
          {Array.from({ length: 24 }, (_, i) => {
            const hourIncidents = hourlyIncidents[i] || [];
            const hasCritical = hourIncidents.some((inc) => inc.severity === "critical");
            const hasWarning = hourIncidents.some((inc) => inc.severity === "warning");
            const count = hourIncidents.length;

            let bgColor = "bg-green-500/30 hover:bg-green-500/50";
            if (hasCritical) bgColor = "bg-red-500/60 hover:bg-red-500/80";
            else if (hasWarning) bgColor = "bg-yellow-500/40 hover:bg-yellow-500/60";
            else if (count > 0) bgColor = "bg-blue-500/30 hover:bg-blue-500/50";

            return (
              <div
                key={i}
                className={`flex-1 rounded-sm transition-colors cursor-default ${bgColor}`}
                title={`${count} incident${count !== 1 ? "s" : ""} (${24 - i}h ago)`}
              />
            );
          })}
        </div>
        <div className="flex items-center gap-4 text-[10px] text-[var(--color-text-secondary)]">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-green-500/40" /> OK
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-blue-500/40" /> Info
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-yellow-500/50" /> Warning
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-red-500/60" /> Critical
          </span>
        </div>
      </div>
    </div>
  );
}

function MiniStat({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="text-center">
      <p className={`text-lg font-bold ${color || ""}`}>{value}</p>
      <p className="text-[10px] text-[var(--color-text-secondary)]">{label}</p>
    </div>
  );
}
