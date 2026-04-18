/**
 * ManualTriggers — the four manual-trigger action tiles.
 *
 * Extracted from HealingPage.tsx as part of P2-20 (decompose large pages).
 */

import { Activity, Cpu, Loader2, Play, Settings2, Shield } from "lucide-react";
import { Button } from "../../components/ui/Button";

export interface ManualTriggersProps {
  onForceCheck: () => void;
  onMcpTest: () => void;
  onReconfigure: () => void;
  onToggle: () => void;
  mcpTesting: boolean;
  reconfiguring: boolean;
  healingEnabled: boolean;
}

export function ManualTriggers({
  onForceCheck,
  onMcpTest,
  onReconfigure,
  onToggle,
  mcpTesting,
  reconfiguring,
  healingEnabled,
}: ManualTriggersProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <TriggerCard
        title="Force Health Check"
        description="Run an immediate health check against all subsystems"
        icon={<Activity className="h-5 w-5 text-green-500" />}
        onClick={onForceCheck}
      />
      <TriggerCard
        title="Test MCP Bridge"
        description="Verify Claude Code CLI connectivity and readiness"
        icon={<Cpu className="h-5 w-5 text-purple-500" />}
        onClick={onMcpTest}
        loading={mcpTesting}
      />
      <TriggerCard
        title="Reconfigure"
        description="Reload detection thresholds and MCP settings from database"
        icon={<Settings2 className="h-5 w-5 text-blue-500" />}
        onClick={onReconfigure}
        loading={reconfiguring}
      />
      <TriggerCard
        title="Toggle Engine"
        description={healingEnabled ? "Disable the self-healing engine" : "Enable the self-healing engine"}
        icon={<Shield className="h-5 w-5 text-red-500" />}
        onClick={onToggle}
        variant={healingEnabled ? "danger" : "primary"}
      />
    </div>
  );
}

interface TriggerCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  onClick: () => void;
  loading?: boolean;
  variant?: "secondary" | "primary" | "danger";
}

function TriggerCard({
  title,
  description,
  icon,
  onClick,
  loading = false,
  variant = "secondary",
}: TriggerCardProps) {
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
