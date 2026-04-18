/**
 * IncidentsList and IncidentRow — collapsible incident log entries.
 *
 * Extracted from HealingPage.tsx as part of P2-20 (decompose large pages).
 */

import {
  AlertTriangle,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import type { HealingIncident } from "../../types";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  warning: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300",
  info: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
};

const OUTCOME_ICONS: Record<string, typeof CheckCircle> = {
  resolved: CheckCircle,
  failed: XCircle,
  escalated: AlertTriangle,
  pending: Clock,
};

export interface IncidentsListProps {
  incidents: HealingIncident[];
  expandedIncident: string | null;
  onToggleExpanded: (id: string | null) => void;
}

export function IncidentsList({
  incidents,
  expandedIncident,
  onToggleExpanded,
}: IncidentsListProps) {
  if (incidents.length === 0) {
    return (
      <div className="py-8 text-center text-[var(--color-text-secondary)]">
        <ShieldCheck className="mx-auto h-12 w-12 text-green-300 mb-2" />
        <p>No incidents recorded. System is running smoothly.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {incidents.map((incident) => (
        <IncidentRow
          key={incident.id}
          incident={incident}
          isExpanded={expandedIncident === incident.id}
          onToggle={() =>
            onToggleExpanded(expandedIncident === incident.id ? null : incident.id)
          }
        />
      ))}
    </div>
  );
}

export interface IncidentRowProps {
  incident: HealingIncident;
  isExpanded: boolean;
  onToggle: () => void;
}

export function IncidentRow({ incident, isExpanded, onToggle }: IncidentRowProps) {
  const OutcomeIcon = OUTCOME_ICONS[incident.outcome] || Clock;
  return (
    <div className="rounded-[var(--radius)] border border-[var(--color-border)] overflow-hidden">
      <button
        type="button"
        className="flex w-full items-start gap-3 p-3 text-left hover:bg-[var(--color-bg-secondary)] transition-colors"
        onClick={onToggle}
      >
        <OutcomeIcon
          className={`h-5 w-5 mt-0.5 flex-shrink-0 ${
            incident.outcome === "resolved"
              ? "text-green-500"
              : incident.outcome === "failed"
                ? "text-red-500"
                : incident.outcome === "escalated"
                  ? "text-yellow-500"
                  : "text-gray-400"
          }`}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${SEVERITY_COLORS[incident.severity] || "bg-gray-100 text-gray-600"}`}
            >
              {incident.severity}
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)]">
              {incident.category}
            </span>
            <span className="text-sm font-medium truncate">{incident.title}</span>
          </div>
          <div className="flex items-center gap-3 mt-1 text-xs text-[var(--color-text-secondary)]">
            {incident.action_taken && <span>Action: {incident.action_taken}</span>}
            {incident.created_at && (
              <span>{new Date(incident.created_at).toLocaleString()}</span>
            )}
          </div>
        </div>
        {isExpanded ? (
          <ChevronUp className="h-4 w-4 text-[var(--color-text-secondary)] flex-shrink-0 mt-1" />
        ) : (
          <ChevronDown className="h-4 w-4 text-[var(--color-text-secondary)] flex-shrink-0 mt-1" />
        )}
      </button>
      {isExpanded && (
        <div className="border-t border-[var(--color-border)] p-3 bg-[var(--color-bg-secondary)] space-y-2 text-sm">
          {incident.description && (
            <div>
              <span className="text-[var(--color-text-secondary)]">Description: </span>
              <span>{incident.description}</span>
            </div>
          )}
          {incident.action_detail && (
            <div>
              <span className="text-[var(--color-text-secondary)]">Action Detail: </span>
              <span className="font-mono text-xs">{incident.action_detail}</span>
            </div>
          )}
          <div className="flex gap-4 text-xs text-[var(--color-text-secondary)]">
            <span>
              Outcome: <strong>{incident.outcome}</strong>
            </span>
            {incident.resolved_at && (
              <span>Resolved: {new Date(incident.resolved_at).toLocaleString()}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
