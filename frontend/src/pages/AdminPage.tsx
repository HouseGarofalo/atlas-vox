import { useEffect } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "../components/ui/Button";
import { useProviderStore } from "../stores/providerStore";
import ProviderConfigCard from "../components/admin/ProviderConfigCard";
import { createLogger } from "../utils/logger";

const logger = createLogger("AdminPage");

export default function AdminPage() {
  const { providers, loading, fetchProviders } = useProviderStore();

  useEffect(() => {
    logger.info("page_mounted");
    fetchProviders();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Admin</h1>
          <p className="text-sm text-[var(--color-text-secondary)]">Configure and test TTS providers</p>
        </div>
        <Button variant="secondary" onClick={() => { logger.info("refresh_click"); fetchProviders(); }} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
        </Button>
      </div>
      <div className="space-y-4">
        {providers.map((provider) => (
          <ProviderConfigCard key={provider.name} provider={provider} />
        ))}
        {!loading && providers.length === 0 && (
          <p className="text-sm text-[var(--color-text-secondary)]">No providers found.</p>
        )}
      </div>
    </div>
  );
}
