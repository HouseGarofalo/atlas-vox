/**
 * ProviderCard — single provider tile shown in the ProvidersPage grid.
 *
 * Extracted from ProvidersPage.tsx as part of P2-20 (decompose large pages).
 * Purely presentational + small toggle action; no behaviour changes.
 */

import React, { useCallback } from "react";
import { Activity, ExternalLink, Settings } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import ProviderLogo from "../../components/providers/ProviderLogo";
import { PROVIDER_METADATA } from "../../data/providerMetadata";
import { useAdminStore } from "../../stores/adminStore";
import type { Provider } from "../../types";

const PRICING_COLORS: Record<string, string> = {
  "open-source": "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  freemium: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300",
  paid: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  free: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
};

export interface ProviderCardProps {
  provider: Provider;
  isEditing: boolean;
  onToggleEdit: () => void;
  onCheckHealth: () => void;
}

export const ProviderCard = React.memo(function ProviderCard({
  provider,
  isEditing,
  onToggleEdit,
  onCheckHealth,
}: ProviderCardProps) {
  const { saveProviderConfig } = useAdminStore();
  const meta = PROVIDER_METADATA[provider.name];

  const healthStatus = provider.health?.healthy
    ? "healthy"
    : provider.health
      ? "unhealthy"
      : "pending";

  const handleToggleEnabled = useCallback(
    async (e: React.MouseEvent) => {
      e.stopPropagation();
      try {
        await saveProviderConfig(provider.name, { enabled: !provider.enabled });
      } catch {
        // handled in store
      }
    },
    [provider.name, provider.enabled, saveProviderConfig],
  );

  return (
    <Card className="flex flex-col gap-3">
      {/* Top row: logo + name + health badge */}
      <div className="flex items-center gap-2.5">
        <ProviderLogo name={provider.name} size={32} className="flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {meta ? (
              <a
                href={meta.website}
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold hover:text-primary-500 transition-colors inline-flex items-center gap-1 truncate"
              >
                {provider.display_name}
                <ExternalLink className="h-3 w-3 opacity-40 flex-shrink-0" />
              </a>
            ) : (
              <h3 className="font-semibold truncate">{provider.display_name}</h3>
            )}
          </div>
        </div>
        <Badge status={healthStatus} className="flex-shrink-0" />
      </div>

      {/* Second row: pricing + type badges */}
      <div className="flex flex-wrap items-center gap-1.5">
        {meta && (() => {
          const tier = meta.pricingTier;
          const colors = PRICING_COLORS[tier] ?? "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300";
          return (
            <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${colors}`}>
              {tier}
            </span>
          );
        })()}
        <Badge status={provider.provider_type} />
      </div>

      {/* Description */}
      {meta && (
        <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed line-clamp-2">
          {meta.description}
        </p>
      )}

      {/* Capability badges */}
      {provider.capabilities && (
        <div className="flex flex-wrap gap-1">
          {provider.capabilities.supports_cloning && <CapBadge label="Cloning" />}
          {provider.capabilities.supports_streaming && <CapBadge label="Streaming" />}
          {provider.capabilities.supports_ssml && <CapBadge label="SSML" />}
          {provider.capabilities.supports_fine_tuning && <CapBadge label="Fine-tune" />}
          {provider.capabilities.supports_zero_shot && <CapBadge label="Zero-shot" />}
        </div>
      )}

      {/* Info line: GPU + model */}
      <span className="text-[10px] text-[var(--color-text-secondary)]">
        GPU: {provider.capabilities?.gpu_mode || provider.gpu_mode || "none"}
        {meta && <span className="ml-2 opacity-70">{meta.modelInfo}</span>}
      </span>

      {/* Health status detail (when not editing) */}
      {provider.health && !isEditing && (
        <div
          className={`text-xs ${
            provider.health.healthy
              ? "text-green-600 dark:text-green-400"
              : "text-red-500 dark:text-red-400"
          }`}
        >
          {provider.health.healthy ? (
            <span>Healthy - {provider.health.latency_ms}ms</span>
          ) : (
            <span className="line-clamp-1" title={provider.health.error ?? undefined}>
              Error: {provider.health.error}
            </span>
          )}
        </div>
      )}

      {/* Footer: toggle + actions */}
      <div className="flex items-center justify-between gap-2 mt-auto pt-2 border-t border-[var(--color-border)]">
        {/* Enable/disable toggle */}
        <div
          role="switch"
          aria-checked={provider.enabled}
          aria-label={`${provider.enabled ? "Disable" : "Enable"} ${provider.display_name}`}
          tabIndex={0}
          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors cursor-pointer flex-shrink-0 ${
            provider.enabled ? "bg-primary-500" : "bg-gray-300 dark:bg-gray-600"
          }`}
          onClick={handleToggleEnabled}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              handleToggleEnabled(e as unknown as React.MouseEvent);
            }
          }}
        >
          <span
            className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
              provider.enabled ? "translate-x-[18px]" : "translate-x-[3px]"
            }`}
          />
        </div>

        <div className="flex gap-1.5">
          <Button
            size="sm"
            variant={isEditing ? "primary" : "secondary"}
            onClick={onToggleEdit}
          >
            <Settings className="h-3 w-3" />
            {isEditing ? "Close" : "Edit"}
          </Button>
          <Button size="sm" variant="ghost" onClick={onCheckHealth} title="Health Check">
            <Activity className="h-3 w-3" />
          </Button>
        </div>
      </div>
    </Card>
  );
});

function CapBadge({ label }: { label: string }) {
  return (
    <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">
      {label}
    </span>
  );
}
