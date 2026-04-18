/**
 * HealingStatusCards — the top-row status grid and the shared sub-cards.
 *
 * Extracted from HealingPage.tsx as part of P2-20 (decompose large pages).
 */

import {
  Activity,
  AlertTriangle,
  BarChart3,
  Clock,
  Shield,
  Zap,
} from "lucide-react";
import type { HealingStatus } from "../../types";

export interface HealingStatusCardsProps {
  status: HealingStatus;
  formatUptime: (seconds: number) => string;
}

export function HealingStatusCards({ status, formatUptime }: HealingStatusCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
      <StatusCard
        icon={<Shield className="h-5 w-5" />}
        label="Status"
        value={status.running ? "Active" : "Stopped"}
        color={status.running ? "text-green-500" : "text-yellow-500"}
      />
      <StatusCard
        icon={<Activity className="h-5 w-5" />}
        label="Health"
        value={status.health.healthy ? "Healthy" : "Degraded"}
        color={status.health.healthy ? "text-green-500" : "text-red-500"}
      />
      <StatusCard
        icon={<BarChart3 className="h-5 w-5" />}
        label="Error Rate"
        value={`${status.telemetry.current_error_rate}%`}
        color={status.telemetry.current_error_rate > 5 ? "text-red-500" : "text-green-500"}
      />
      <StatusCard
        icon={<AlertTriangle className="h-5 w-5" />}
        label="Errors (1m)"
        value={String(status.logs.errors_last_minute)}
        color={status.logs.errors_last_minute > 5 ? "text-red-500" : "text-green-500"}
      />
      <StatusCard
        icon={<Zap className="h-5 w-5" />}
        label="Incidents"
        value={String(status.incidents_handled)}
        color="text-blue-500"
      />
      <StatusCard
        icon={<Clock className="h-5 w-5" />}
        label="Uptime"
        value={formatUptime(status.uptime_seconds)}
        color="text-[var(--color-text-secondary)]"
      />
    </div>
  );
}

export interface StatusCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}

export function StatusCard({ icon, label, value, color }: StatusCardProps) {
  return (
    <div className="rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg)] p-3 text-center card-styled">
      <div className={`mx-auto mb-1 ${color}`}>{icon}</div>
      <p className={`text-lg font-bold ${color}`}>{value}</p>
      <p className="text-xs text-[var(--color-text-secondary)]">{label}</p>
    </div>
  );
}
