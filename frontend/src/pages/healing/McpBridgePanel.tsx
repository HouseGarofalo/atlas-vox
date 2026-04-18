/**
 * McpBridgePanel — the Claude Code MCP bridge status/fix-history block.
 *
 * Extracted from HealingPage.tsx as part of P2-20 (decompose large pages).
 */

import { CheckCircle, Wifi, WifiOff, XCircle } from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import type { HealingStatus, McpTestResult } from "../../types";

export interface McpBridgePanelProps {
  mcp: NonNullable<HealingStatus["mcp"]>;
  mcpTestResult: McpTestResult | null;
}

export function McpBridgePanel({ mcp, mcpTestResult }: McpBridgePanelProps) {
  return (
    <div className="space-y-4">
      {/* MCP Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="text-center">
          <p className="text-2xl font-bold">{mcp.fixes_this_hour}</p>
          <p className="text-xs text-[var(--color-text-secondary)]">Fixes This Hour</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold">{mcp.max_fixes_per_hour}</p>
          <p className="text-xs text-[var(--color-text-secondary)]">Max Per Hour</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold">{mcp.total_fixes}</p>
          <p className="text-xs text-[var(--color-text-secondary)]">Total Fixes</p>
        </div>
        <div className="text-center">
          <Badge status={mcp.enabled ? "healthy" : "pending"} />
          <p className="text-xs text-[var(--color-text-secondary)] mt-1">MCP Status</p>
        </div>
      </div>

      {/* MCP Paths */}
      <div className="rounded-[var(--radius)] border border-[var(--color-border)] p-3 space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--color-text-secondary)]">Server Path:</span>
          <div className="flex items-center gap-1.5">
            {mcp.server_exists ? (
              <CheckCircle className="h-3.5 w-3.5 text-green-500" />
            ) : (
              <XCircle className="h-3.5 w-3.5 text-red-500" />
            )}
            <span className="font-mono text-xs">{mcp.server_path}</span>
          </div>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--color-text-secondary)]">Project Root:</span>
          <div className="flex items-center gap-1.5">
            {mcp.project_root_exists ? (
              <CheckCircle className="h-3.5 w-3.5 text-green-500" />
            ) : (
              <XCircle className="h-3.5 w-3.5 text-red-500" />
            )}
            <span className="font-mono text-xs">{mcp.project_root}</span>
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
      {mcp.recent_fixes && mcp.recent_fixes.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Recent Fixes</h4>
          {mcp.recent_fixes.map((fix, idx) => (
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
