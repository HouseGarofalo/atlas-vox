import { useEffect, useState, useCallback } from "react";
import { getErrorMessage } from "../utils/errors";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Cpu,
  Clock,
  Zap,
  BarChart3,
  Settings2,
  Play,
  Server,
  Loader2,
  ChevronDown,
  ChevronUp,
  Database,
  HardDrive,
  Wifi,
  WifiOff,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import { api } from "../services/api";
import { createLogger } from "../utils/logger";
import type { HealingStatus, HealingIncident, McpTestResult } from "../types";

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
  const [mcpTestResult, setMcpTestResult] = useState<McpTestResult | null>(null);
  const [mcpTesting, setMcpTesting] = useState(false);
  const [reconfiguring, setReconfiguring] = useState(false);
  const [expandedIncident, setExpandedIncident] = useState<string | null>(null);

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

  const handleMcpTest = async () => {
    setMcpTesting(true);
    try {
      const result = await api.testMcpBridge();
      setMcpTestResult(result);
      toast.success(result.ready ? "MCP bridge ready" : "MCP bridge not ready");
    } catch (e: unknown) {
      toast.error(getErrorMessage(e));
    } finally {
      setMcpTesting(false);
    }
  };

  const handleReconfigure = async () => {
    setReconfiguring(true);
    try {
      await api.reconfigureHealing();
      toast.success("Healing engine reconfigured from DB settings");
      await fetchData();
    } catch (e: unknown) {
      toast.error(getErrorMessage(e));
    } finally {
      setReconfiguring(false);
    }
  };

  const formatUptime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (h > 24) {
      const d = Math.floor(h / 24);
      return `${d}d ${h % 24}h`;
    }
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
        <div className="flex gap-2 flex-wrap">
          <Button variant="secondary" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} /> Refresh
          </Button>
          <Button variant="secondary" onClick={handleForceCheck}>
            <Activity className="h-4 w-4" /> Force Check
          </Button>
          <Button variant="secondary" onClick={handleReconfigure} disabled={reconfiguring}>
            {reconfiguring ? <Loader2 className="h-4 w-4 animate-spin" /> : <Settings2 className="h-4 w-4" />}
            Reconfigure
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

      {/* Health Timeline */}
      {status && (
        <CollapsiblePanel
          title="Health Timeline"
          icon={<Activity className="h-4 w-4 text-green-500" />}
          id="healing-timeline"
          defaultOpen
        >
          <HealthTimeline status={status} incidents={incidents} />
        </CollapsiblePanel>
      )}

      {/* Detection Configuration */}
      {status?.detector && (
        <CollapsiblePanel
          title="Detection Thresholds"
          icon={<Settings2 className="h-4 w-4 text-blue-500" />}
          id="healing-config"
          defaultOpen={false}
        >
          <p className="mb-4 text-sm text-[var(--color-text-secondary)]">
            Current detection thresholds (change via Admin &rarr; Self-Healing settings, then click Reconfigure)
          </p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            <ThresholdCard
              label="Health Failures"
              value={String(status.detector.health_failure_threshold)}
              unit="consecutive"
              icon={<Activity className="h-4 w-4" />}
            />
            <ThresholdCard
              label="Error Rate Spike"
              value={`${status.detector.error_rate_spike_multiplier}x`}
              unit="baseline multiplier"
              icon={<BarChart3 className="h-4 w-4" />}
            />
            <ThresholdCard
              label="Latency P99"
              value={`${status.detector.latency_p99_threshold_ms}`}
              unit="ms"
              icon={<Clock className="h-4 w-4" />}
            />
            <ThresholdCard
              label="Errors/Minute"
              value={String(status.detector.errors_per_minute_threshold)}
              unit="per minute"
              icon={<AlertTriangle className="h-4 w-4" />}
            />
            <ThresholdCard
              label="Celery Backlog"
              value={String(status.detector.celery_backlog_threshold)}
              unit="pending tasks"
              icon={<Server className="h-4 w-4" />}
            />
            <ThresholdCard
              label="Memory Limit"
              value={String(status.detector.memory_threshold_mb)}
              unit="MB RSS"
              icon={<Database className="h-4 w-4" />}
            />
            <ThresholdCard
              label="Disk Usage"
              value={`${status.detector.disk_usage_threshold_pct}%`}
              unit="capacity"
              icon={<HardDrive className="h-4 w-4" />}
            />
          </div>
        </CollapsiblePanel>
      )}

      {/* Manual Triggers */}
      <CollapsiblePanel
        title="Manual Triggers"
        icon={<Play className="h-4 w-4 text-orange-500" />}
        id="healing-triggers"
        defaultOpen={false}
      >
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <TriggerCard
            title="Force Health Check"
            description="Run an immediate health check against all subsystems"
            icon={<Activity className="h-5 w-5 text-green-500" />}
            onClick={handleForceCheck}
          />
          <TriggerCard
            title="Test MCP Bridge"
            description="Verify Claude Code CLI connectivity and readiness"
            icon={<Cpu className="h-5 w-5 text-purple-500" />}
            onClick={handleMcpTest}
            loading={mcpTesting}
          />
          <TriggerCard
            title="Reconfigure"
            description="Reload detection thresholds and MCP settings from database"
            icon={<Settings2 className="h-5 w-5 text-blue-500" />}
            onClick={handleReconfigure}
            loading={reconfiguring}
          />
          <TriggerCard
            title="Toggle Engine"
            description={status?.enabled ? "Disable the self-healing engine" : "Enable the self-healing engine"}
            icon={<Shield className="h-5 w-5 text-red-500" />}
            onClick={handleToggle}
            variant={status?.enabled ? "danger" : "primary"}
          />
        </div>
      </CollapsiblePanel>

      {/* MCP Status Detail */}
      {status?.mcp && (
        <CollapsiblePanel
          title="Claude Code MCP Bridge"
          icon={<Cpu className="h-4 w-4 text-purple-500" />}
          id="healing-mcp"
          defaultOpen={false}
        >
          <div className="space-y-4">
            {/* MCP Stats */}
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

            {/* MCP Paths */}
            <div className="rounded-[var(--radius)] border border-[var(--color-border)] p-3 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-[var(--color-text-secondary)]">Server Path:</span>
                <div className="flex items-center gap-1.5">
                  {status.mcp.server_exists ? (
                    <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5 text-red-500" />
                  )}
                  <span className="font-mono text-xs">{status.mcp.server_path}</span>
                </div>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-[var(--color-text-secondary)]">Project Root:</span>
                <div className="flex items-center gap-1.5">
                  {status.mcp.project_root_exists ? (
                    <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5 text-red-500" />
                  )}
                  <span className="font-mono text-xs">{status.mcp.project_root}</span>
                </div>
              </div>
            </div>

            {/* MCP Test Result */}
            {mcpTestResult && (
              <div className="rounded-[var(--radius)] border border-[var(--color-border)] p-3 space-y-2">
                <h4 className="text-sm font-medium">Connection Test Result</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <TestResultRow
                    label="Claude CLI"
                    ok={mcpTestResult.claude_cli_found}
                    detail={mcpTestResult.claude_cli_version || "Not found"}
                  />
                  <TestResultRow
                    label="Server Path"
                    ok={mcpTestResult.server_path_valid}
                    detail={mcpTestResult.server_path_valid ? "Valid" : "Missing"}
                  />
                  <TestResultRow
                    label="Project Root"
                    ok={mcpTestResult.project_root_valid}
                    detail={mcpTestResult.project_root_valid ? "Valid" : "Missing"}
                  />
                  <TestResultRow
                    label="Overall"
                    ok={mcpTestResult.ready}
                    detail={mcpTestResult.ready ? "Ready" : "Not Ready"}
                  />
                </div>
              </div>
            )}

            {/* Recent Fix History */}
            {status.mcp.recent_fixes && status.mcp.recent_fixes.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Recent Fixes</h4>
                {status.mcp.recent_fixes.map((fix, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 rounded-[var(--radius)] border border-[var(--color-border)] p-3"
                  >
                    {fix.success ? (
                      <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{fix.event_title}</p>
                      <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                        Rule: {fix.event_rule} | {new Date(fix.timestamp * 1000).toLocaleString()}
                      </p>
                      <p className="text-xs text-[var(--color-text-secondary)] mt-1 font-mono line-clamp-2">
                        {fix.result}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
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
              const isExpanded = expandedIncident === incident.id;
              return (
                <div
                  key={incident.id}
                  className="rounded-[var(--radius)] border border-[var(--color-border)] overflow-hidden"
                >
                  <button
                    type="button"
                    className="flex w-full items-start gap-3 p-3 text-left hover:bg-[var(--color-bg-secondary)] transition-colors"
                    onClick={() => setExpandedIncident(isExpanded ? null : incident.id)}
                  >
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
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)]">
                          {incident.category}
                        </span>
                        <span className="text-sm font-medium truncate">{incident.title}</span>
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-xs text-[var(--color-text-secondary)]">
                        {incident.action_taken && <span>Action: {incident.action_taken}</span>}
                        {incident.created_at && <span>{new Date(incident.created_at).toLocaleString()}</span>}
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
                        <span>Outcome: <strong>{incident.outcome}</strong></span>
                        {incident.resolved_at && <span>Resolved: {new Date(incident.resolved_at).toLocaleString()}</span>}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CollapsiblePanel>
    </div>
  );
}

/* ---------- Sub-Components ---------- */

function StatusCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string; color: string }) {
  return (
    <div className="rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg)] p-3 text-center card-styled">
      <div className={`mx-auto mb-1 ${color}`}>{icon}</div>
      <p className={`text-lg font-bold ${color}`}>{value}</p>
      <p className="text-xs text-[var(--color-text-secondary)]">{label}</p>
    </div>
  );
}

function ThresholdCard({ label, value, unit, icon }: { label: string; value: string; unit: string; icon: React.ReactNode }) {
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

function TriggerCard({
  title,
  description,
  icon,
  onClick,
  loading = false,
  variant = "secondary",
}: {
  title: string;
  description: string;
  icon: React.ReactNode;
  onClick: () => void;
  loading?: boolean;
  variant?: "secondary" | "primary" | "danger";
}) {
  return (
    <div className="rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg)] p-4 flex flex-col gap-3 card-styled">
      <div className="flex items-center gap-2">
        {icon}
        <h4 className="text-sm font-medium">{title}</h4>
      </div>
      <p className="text-xs text-[var(--color-text-secondary)] flex-1">{description}</p>
      <Button variant={variant} size="sm" onClick={onClick} disabled={loading} className="w-full">
        {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
        {loading ? "Running..." : "Run"}
      </Button>
    </div>
  );
}

function TestResultRow({ label, ok, detail }: { label: string; ok: boolean; detail: string }) {
  return (
    <div className="flex items-center gap-2">
      {ok ? (
        <Wifi className="h-3.5 w-3.5 text-green-500" />
      ) : (
        <WifiOff className="h-3.5 w-3.5 text-red-500" />
      )}
      <span className="text-[var(--color-text-secondary)]">{label}:</span>
      <span className={`font-mono text-xs ${ok ? "text-green-600" : "text-red-500"}`}>
        {detail}
      </span>
    </div>
  );
}

function HealthTimeline({ status, incidents }: { status: HealingStatus; incidents: Incident[] }) {
  // Build a 24-hour timeline with health status and incidents
  const now = Date.now();
  const hours24 = 24 * 60 * 60 * 1000;
  const startTime = now - hours24;

  // Group incidents by hour
  const hourlyIncidents: Record<number, Incident[]> = {};
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
        <MiniStat label="Consecutive Failures" value={String(status.health.consecutive_failures)} color={status.health.consecutive_failures > 0 ? "text-red-500" : undefined} />
        <MiniStat label="Avg Error Rate" value={`${status.telemetry.avg_error_rate}%`} />
        <MiniStat label="Errors (5m)" value={String(status.logs.errors_last_5_minutes)} color={status.logs.errors_last_5_minutes > 10 ? "text-red-500" : undefined} />
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
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-green-500/40" /> OK</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-blue-500/40" /> Info</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-yellow-500/50" /> Warning</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-red-500/60" /> Critical</span>
        </div>
      </div>
    </div>
  );
}

function MiniStat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="text-center">
      <p className={`text-lg font-bold ${color || ""}`}>{value}</p>
      <p className="text-[10px] text-[var(--color-text-secondary)]">{label}</p>
    </div>
  );
}
