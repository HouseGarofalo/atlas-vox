/**
 * HealingPage — self-healing engine dashboard.
 *
 * P2-20: decomposed from a 684-line mega-file. All presentation lives in
 * ./healing/*; this file keeps only data fetching, action handlers, and the
 * page-level layout.
 */

import { useCallback, useEffect, useState } from "react";
import { getErrorMessage } from "../utils/errors";
import {
  Activity,
  AlertTriangle,
  Cpu,
  Loader2,
  Play,
  RefreshCw,
  Settings2,
  Shield,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "../components/ui/Button";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import { api } from "../services/api";
import { createLogger } from "../utils/logger";
import type { HealingIncident, HealingStatus, McpTestResult } from "../types";
import { HealingStatusCards } from "./healing/HealingStatusCards";
import { DetectionThresholds } from "./healing/DetectionThresholds";
import { ManualTriggers } from "./healing/ManualTriggers";
import { McpBridgePanel } from "./healing/McpBridgePanel";
import { IncidentsList } from "./healing/IncidentsList";
import { HealthTimeline } from "./healing/HealthTimeline";

const logger = createLogger("HealingPage");

export default function HealingPage() {
  const [status, setStatus] = useState<HealingStatus | null>(null);
  const [incidents, setIncidents] = useState<HealingIncident[]>([]);
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
            {reconfiguring ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Settings2 className="h-4 w-4" />
            )}
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
      {status && <HealingStatusCards status={status} formatUptime={formatUptime} />}

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
          <DetectionThresholds detector={status.detector} />
        </CollapsiblePanel>
      )}

      {/* Manual Triggers */}
      <CollapsiblePanel
        title="Manual Triggers"
        icon={<Play className="h-4 w-4 text-orange-500" />}
        id="healing-triggers"
        defaultOpen={false}
      >
        <ManualTriggers
          onForceCheck={handleForceCheck}
          onMcpTest={handleMcpTest}
          onReconfigure={handleReconfigure}
          onToggle={handleToggle}
          mcpTesting={mcpTesting}
          reconfiguring={reconfiguring}
          healingEnabled={status?.enabled ?? false}
        />
      </CollapsiblePanel>

      {/* MCP Status Detail */}
      {status?.mcp && (
        <CollapsiblePanel
          title="Claude Code MCP Bridge"
          icon={<Cpu className="h-4 w-4 text-purple-500" />}
          id="healing-mcp"
          defaultOpen={false}
        >
          <McpBridgePanel mcp={status.mcp} mcpTestResult={mcpTestResult} />
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
        <IncidentsList
          incidents={incidents}
          expandedIncident={expandedIncident}
          onToggleExpanded={setExpandedIncident}
        />
      </CollapsiblePanel>
    </div>
  );
}
