import { useEffect, useState, useCallback } from "react";
import { getErrorMessage } from "../utils/errors";
import { Activity, AlertTriangle, CheckCircle, XCircle, RefreshCw, Shield, ShieldAlert, ShieldCheck, Cpu, Clock, Zap, BarChart3 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import { api } from "../services/api";
import { createLogger } from "../utils/logger";
import type { HealingStatus, HealingIncident } from "../types";

const logger = createLogger("HealingPage");

type Incident = HealingIncident;

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

export default function HealingPage() {
  const [status, setStatus] = useState<HealingStatus | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [s, i] = await Promise.all([
        api.getHealingStatus(),
        api.getHealingIncidents(50),
      ]);
      setStatus(s);
      setIncidents(i.incidents);
    } catch (e: unknown) {
      logger.error("fetch_error", { error: getErrorMessage(e) });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  };

  const handleForceCheck = async () => {
    try {
      const result = await api.forceHealthCheck();
      toast.success(result.healthy ? "System healthy" : "Issues detected");
      await fetchData();
    } catch (e: unknown) {
      toast.error(getErrorMessage(e));
    }
  };

  const handleToggle = async () => {
    if (!status) return;
    try {
      const result = await api.toggleHealing(!status.enabled);
      toast.success(result.enabled ? "Self-healing enabled" : "Self-healing disabled");
      await fetchData();
    } catch (e: unknown) {
      toast.error(getErrorMessage(e));
    }
  };

  const formatUptime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          {status?.running ? (
            <ShieldCheck className="h-7 w-7 text-green-500" />
          ) : (
            <ShieldAlert className="h-7 w-7 text-yellow-500" />
          )}
          <div>
            <h1 className="text-2xl font-bold">Self-Healing</h1>
            <p className="text-sm text-[var(--color-text-secondary)]">
              AI-powered monitoring, detection, and auto-remediation
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} /> Refresh
          </Button>
          <Button variant="secondary" onClick={handleForceCheck}>
            <Activity className="h-4 w-4" /> Force Check
          </Button>
          <Button
            variant={status?.enabled ? "danger" : "primary"}
            onClick={handleToggle}
          >
            <Shield className="h-4 w-4" /> {status?.enabled ? "Disable" : "Enable"}
          </Button>
        </div>
      </div>

      {/* Status Cards */}
      {status && (
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
      )}

      {/* MCP Status */}
      {status?.mcp && (
        <CollapsiblePanel title="Claude Code MCP" icon={<Cpu className="h-4 w-4 text-purple-500" />} id="healing-mcp" defaultOpen={false}>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="text-center">
              <p className="text-2xl font-bold">{status.mcp.fixes_this_hour}</p>
              <p className="text-xs text-[var(--color-text-secondary)]">Fixes This Hour</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{status.mcp.max_fixes_per_hour}</p>
              <p className="text-xs text-[var(--color-text-secondary)]">Max Per Hour</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{status.mcp.total_fixes}</p>
              <p className="text-xs text-[var(--color-text-secondary)]">Total Fixes</p>
            </div>
            <div className="text-center">
              <Badge status={status.mcp.enabled ? "healthy" : "pending"} />
              <p className="text-xs text-[var(--color-text-secondary)] mt-1">MCP Status</p>
            </div>
          </div>
        </CollapsiblePanel>
      )}

      {/* Incident Log */}
      <CollapsiblePanel
        title={`Incident Log (${incidents.length})`}
        icon={<AlertTriangle className="h-4 w-4 text-orange-500" />}
        id="healing-incidents"
        resizable
        defaultHeight={400}
      >
        {incidents.length === 0 ? (
          <div className="py-8 text-center text-[var(--color-text-secondary)]">
            <ShieldCheck className="mx-auto h-12 w-12 text-green-300 mb-2" />
            <p>No incidents recorded. System is running smoothly.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {incidents.map((incident) => {
              const OutcomeIcon = OUTCOME_ICONS[incident.outcome] || Clock;
              return (
                <div key={incident.id} className="flex items-start gap-3 rounded-[var(--radius)] border border-[var(--color-border)] p-3">
                  <OutcomeIcon className={`h-5 w-5 mt-0.5 flex-shrink-0 ${
                    incident.outcome === "resolved" ? "text-green-500" :
                    incident.outcome === "failed" ? "text-red-500" :
                    incident.outcome === "escalated" ? "text-yellow-500" : "text-gray-400"
                  }`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${SEVERITY_COLORS[incident.severity] || "bg-gray-100 text-gray-600"}`}>
                        {incident.severity}
                      </span>
                      <span className="text-sm font-medium truncate">{incident.title}</span>
                    </div>
                    {incident.description && (
                      <p className="text-xs text-[var(--color-text-secondary)] mt-1">{incident.description}</p>
                    )}
                    <div className="flex items-center gap-3 mt-1.5 text-xs text-[var(--color-text-secondary)]">
                      {incident.action_taken && <span>Action: {incident.action_taken}</span>}
                      {incident.created_at && <span>{new Date(incident.created_at).toLocaleString()}</span>}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CollapsiblePanel>
    </div>
  );
}

function StatusCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string; color: string }) {
  return (
    <div className="rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg)] p-3 text-center card-styled">
      <div className={`mx-auto mb-1 ${color}`}>{icon}</div>
      <p className={`text-lg font-bold ${color}`}>{value}</p>
      <p className="text-xs text-[var(--color-text-secondary)]">{label}</p>
    </div>
  );
}
