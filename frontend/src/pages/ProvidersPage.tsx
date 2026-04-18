/**
 * ProvidersPage — configure, test, and manage TTS providers.
 *
 * P2-20: decomposed from a 922-line mega-file. The heavy presentation and
 * subflow logic now lives in ./providers/* sub-components. This file retains
 * only page-level routing, layout, and the small amount of state that
 * coordinates the inline edit panel.
 */

import { useEffect, useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { useProviderStore } from "../stores/providerStore";
import { createLogger } from "../utils/logger";
import { ProviderGrid } from "./providers/ProviderGrid";

const logger = createLogger("ProvidersPage");

export default function ProvidersPage() {
  const { providers, loading, error, fetchProviders, checkAllHealth, checkHealth } =
    useProviderStore();
  const [editingProvider, setEditingProvider] = useState<string | null>(null);

  useEffect(() => {
    logger.info("page_mounted");
    fetchProviders();
  }, []);

  const toggleEdit = (name: string) => {
    const next = editingProvider === name ? null : name;
    logger.info("edit_panel_toggle", { provider: name, opened: next !== null });
    setEditingProvider(next);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Providers</h1>
          <p className="text-sm text-[var(--color-text-secondary)] mt-1">
            Configure, test, and manage TTS providers
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={() => fetchProviders().then(() => checkAllHealth())}
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh All
        </Button>
      </div>

      {/* Card grid */}
      {loading && !providers.length ? (
        <p className="text-[var(--color-text-secondary)]">Loading...</p>
      ) : error && !providers.length ? (
        <Card className="py-8 text-center space-y-3">
          <p className="text-sm text-red-600 dark:text-red-400">
            Failed to load providers: {error}
          </p>
          <Button variant="secondary" onClick={() => fetchProviders()}>
            <Loader2 className="h-4 w-4 mr-2" /> Retry
          </Button>
        </Card>
      ) : providers.length === 0 ? (
        <Card className="py-12 text-center">
          <p className="text-[var(--color-text-secondary)]">No providers found.</p>
        </Card>
      ) : (
        <ProviderGrid
          providers={providers}
          editingProvider={editingProvider}
          onToggleEdit={toggleEdit}
          onCheckHealth={checkHealth}
        />
      )}
    </div>
  );
}
