import { useEffect } from "react";
import { RefreshCw } from "lucide-react";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { useProviderStore } from "../stores/providerStore";

export default function ProvidersPage() {
  const { providers, loading, fetchProviders, checkHealth } = useProviderStore();
  useEffect(() => { fetchProviders(); }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Providers</h1>
        <Button variant="secondary" onClick={fetchProviders} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
        </Button>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {providers.map((provider) => (
          <Card key={provider.name} className="flex flex-col gap-3">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold">{provider.display_name}</h3>
                <p className="text-xs text-[var(--color-text-secondary)]">{provider.name}</p>
              </div>
              <div className="flex gap-1">
                <Badge status={provider.provider_type} />
                <Badge status={provider.health?.healthy ? "healthy" : provider.enabled ? "unhealthy" : "pending"} />
              </div>
            </div>
            {provider.capabilities && (
              <div className="flex flex-wrap gap-1">
                {provider.capabilities.supports_cloning && <CapBadge label="Cloning" />}
                {provider.capabilities.supports_streaming && <CapBadge label="Streaming" />}
                {provider.capabilities.supports_ssml && <CapBadge label="SSML" />}
                {provider.capabilities.supports_fine_tuning && <CapBadge label="Fine-tune" />}
                {provider.capabilities.supports_zero_shot && <CapBadge label="Zero-shot" />}
              </div>
            )}
            <div className="text-xs text-[var(--color-text-secondary)]">GPU: {provider.capabilities?.gpu_mode || provider.gpu_mode || "none"}</div>
            {provider.health && (
              <div className="text-xs text-[var(--color-text-secondary)]">{provider.health.healthy ? `Latency: ${provider.health.latency_ms}ms` : `Error: ${provider.health.error}`}</div>
            )}
            <div className="mt-auto pt-2 border-t border-[var(--color-border)]">
              <Button size="sm" variant="secondary" onClick={() => checkHealth(provider.name)}>Health Check</Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function CapBadge({ label }: { label: string }) {
  return <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">{label}</span>;
}
