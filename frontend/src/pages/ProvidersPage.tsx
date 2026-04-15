import React, { useEffect, useState, useCallback, useRef } from "react";
import { RefreshCw, ExternalLink, Settings, Activity, Loader2, Eye, EyeOff, Check, LogIn, LogOut, Shield, Copy, Clock } from "lucide-react";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { useProviderStore } from "../stores/providerStore";
import { useAdminStore } from "../stores/adminStore";
import ProviderLogo from "../components/providers/ProviderLogo";
import { PROVIDER_METADATA } from "../data/providerMetadata";
import { createLogger } from "../utils/logger";
import { api } from "../services/api";
import type { Provider, ProviderFieldSchema, AzureAuthStatus } from "../types";

const logger = createLogger("ProvidersPage");

/* ---------- constants ---------- */

const PRICING_COLORS: Record<string, string> = {
  "open-source": "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  freemium: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300",
  paid: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  free: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
};

/* ---------- page ---------- */

export default function ProvidersPage() {
  const { providers, loading, error, fetchProviders, checkAllHealth, checkHealth } = useProviderStore();
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
          <p className="text-sm text-red-600 dark:text-red-400">Failed to load providers: {error}</p>
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

/* ---------- grid with inline expand ---------- */

/**
 * Renders a 3-column grid. When a card is being edited the edit panel
 * spans the full grid width immediately after the row containing the card.
 */
function ProviderGrid({
  providers,
  editingProvider,
  onToggleEdit,
  onCheckHealth,
}: {
  providers: Provider[];
  editingProvider: string | null;
  onToggleEdit: (name: string) => void;
  onCheckHealth: (name: string) => Promise<void>;
}) {
  // We render rows manually so the expanded panel can span full width.
  // Chunk providers into rows of 3 (desktop), but CSS handles responsive columns.
  // To support the inline expand correctly at all breakpoints we use a flat list
  // with the edit panel inserted after the appropriate card and spanning all columns.
  const items: React.ReactNode[] = [];

  for (const provider of providers) {
    items.push(
      <ProviderCard
        key={provider.name}
        provider={provider}
        isEditing={editingProvider === provider.name}
        onToggleEdit={() => onToggleEdit(provider.name)}
        onCheckHealth={() => onCheckHealth(provider.name)}
      />
    );

    if (editingProvider === provider.name) {
      items.push(
        <div
          key={`${provider.name}-edit`}
          className="col-span-1 sm:col-span-2 lg:col-span-3"
        >
          <ProviderEditPanel provider={provider} onClose={() => onToggleEdit(provider.name)} />
        </div>
      );
    }
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items}
    </div>
  );
}

/* ---------- single provider card ---------- */

const ProviderCard = React.memo(function ProviderCard({
  provider,
  isEditing,
  onToggleEdit,
  onCheckHealth,
}: {
  provider: Provider;
  isEditing: boolean;
  onToggleEdit: () => void;
  onCheckHealth: () => void;
}) {
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

/* ---------- inline edit panel ---------- */

function ProviderEditPanel({
  provider,
  onClose,
}: {
  provider: Provider;
  onClose: () => void;
}) {
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [dirtyFields, setDirtyFields] = useState<Set<string>>(new Set());
  const [visibleSecrets, setVisibleSecrets] = useState<Set<string>>(new Set());
  const [testText, setTestText] = useState("Hello, this is a test of the text to speech system.");
  const [savedRecently, setSavedRecently] = useState(false);
  const savedTimerRef = useRef<ReturnType<typeof setTimeout>>();

  const {
    providerConfigs,
    loadingConfig,
    savingConfig,
    testResults,
    testingProvider,
    fetchProviderConfig,
    saveProviderConfig,
    testProvider,
  } = useAdminStore();

  const { checkHealth } = useProviderStore();

  const config = providerConfigs[provider.name];
  const isLoading = loadingConfig[provider.name] ?? false;
  const isSaving = savingConfig[provider.name] ?? false;
  const isTesting = testingProvider[provider.name] ?? false;
  const testResult = testResults[provider.name];

  // Load config when panel mounts
  useEffect(() => {
    if (!config && !isLoading) {
      fetchProviderConfig(provider.name);
    }
  }, [config, isLoading, provider.name, fetchProviderConfig]);

  // Initialize form values from config
  useEffect(() => {
    if (config) {
      const initial: Record<string, string> = {};
      for (const field of config.config_schema) {
        initial[field.name] = config.config[field.name] ?? "";
      }
      setFormValues(initial);
      setDirtyFields(new Set());
    }
  }, [config]);

  const handleFieldChange = useCallback((fieldName: string, value: string) => {
    setFormValues((prev) => ({ ...prev, [fieldName]: value }));
    setDirtyFields((prev) => new Set(prev).add(fieldName));
  }, []);

  const toggleSecretVisibility = useCallback((fieldName: string) => {
    setVisibleSecrets((prev) => {
      const next = new Set(prev);
      if (next.has(fieldName)) next.delete(fieldName);
      else next.add(fieldName);
      return next;
    });
  }, []);

  const handleSave = useCallback(async () => {
    if (dirtyFields.size === 0) return;
    const changedConfig: Record<string, string> = {};
    for (const fieldName of dirtyFields) {
      changedConfig[fieldName] = formValues[fieldName];
    }
    try {
      await saveProviderConfig(provider.name, { config: changedConfig });
      setSavedRecently(true);
      if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
      savedTimerRef.current = setTimeout(() => setSavedRecently(false), 2000);
    } catch {
      // handled in store
    }
  }, [dirtyFields, formValues, provider.name, saveProviderConfig]);

  const handleHealthCheck = useCallback(() => {
    checkHealth(provider.name);
  }, [provider.name, checkHealth]);

  const handleTest = useCallback(() => {
    testProvider(provider.name, testText);
  }, [provider.name, testText, testProvider]);

  const meta = PROVIDER_METADATA[provider.name];

  return (
    <Card className="mt-0 border-primary-500/30 bg-[var(--color-bg)]">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <ProviderLogo name={provider.name} size={20} />
          {provider.display_name} Configuration
        </h3>
        <Button size="sm" variant="ghost" onClick={onClose}>
          Close
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-[var(--color-text-secondary)]" />
        </div>
      ) : config ? (
        <div className="space-y-5">
          {/* Provider description & website */}
          {meta && (
            <div className="space-y-1">
              <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                {meta.description}
              </p>
              <a
                href={meta.website}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-primary-500 hover:text-primary-600 transition-colors"
              >
                Website <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          )}

          {/* Config fields */}
          {config.config_schema.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-[var(--color-text-secondary)]">Configuration</h4>
              <div className="space-y-3 max-w-lg">
                {config.config_schema.map((field) => (
                  <ConfigField
                    key={field.name}
                    field={field}
                    value={formValues[field.name] ?? ""}
                    isDirty={dirtyFields.has(field.name)}
                    isSecretVisible={visibleSecrets.has(field.name)}
                    originalValue={config.config[field.name] ?? ""}
                    onChange={(val) => handleFieldChange(field.name, val)}
                    onToggleVisibility={() => toggleSecretVisibility(field.name)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Azure Login Section (only for azure_speech) */}
          {provider.name === "azure_speech" && <AzureLoginSection />}

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant="primary"
              disabled={dirtyFields.size === 0 || isSaving}
              onClick={handleSave}
            >
              {isSaving ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : savedRecently ? (
                <Check className="h-3.5 w-3.5" />
              ) : null}
              {savedRecently ? "Saved" : "Save"}
            </Button>
            <Button size="sm" variant="secondary" onClick={handleHealthCheck}>
              Health Check
            </Button>
          </div>

          {/* Health check result */}
          {provider.health && (
            <div
              className={`text-xs rounded-lg px-3 py-2 ${
                provider.health.healthy
                  ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                  : "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300"
              }`}
            >
              {provider.health.healthy
                ? `Healthy - latency: ${provider.health.latency_ms}ms`
                : `Error: ${provider.health.error}`}
            </div>
          )}

          {/* Test synthesis */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-[var(--color-text-secondary)]">Test Synthesis</h4>
            <div className="flex gap-2">
              <input
                type="text"
                value={testText}
                onChange={(e) => setTestText(e.target.value)}
                placeholder="Enter test text..."
                className="h-8 flex-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 text-sm text-[var(--color-text)] focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
              <Button
                size="sm"
                variant="secondary"
                onClick={handleTest}
                disabled={isTesting || !testText.trim()}
              >
                {isTesting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Test
              </Button>
            </div>
            {testResult && (
              <div
                className={`text-xs rounded-lg px-3 py-2 ${
                  testResult.success
                    ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                    : "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                }`}
              >
                {testResult.success ? (
                  <div className="space-y-1">
                    <p>
                      Success - latency: {testResult.latency_ms}ms
                      {testResult.duration_seconds != null
                        ? `, duration: ${testResult.duration_seconds.toFixed(2)}s`
                        : ""}
                    </p>
                    {testResult.audio_url && (
                      <audio controls src={testResult.audio_url} className="mt-1 h-8 w-full" />
                    )}
                  </div>
                ) : (
                  <p>Error: {testResult.error}</p>
                )}
              </div>
            )}
          </div>
        </div>
      ) : (
        <p className="text-sm text-[var(--color-text-secondary)]">Failed to load configuration.</p>
      )}
    </Card>
  );
}

/* ---------- Azure Login Section ---------- */

function AzureLoginSection() {
  const [authStatus, setAuthStatus] = useState<AzureAuthStatus | null>(null);
  const [initiating, setInitiating] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  // Fetch status on mount and set up polling when device code is pending
  const fetchStatus = useCallback(async () => {
    try {
      const status = await api.getAzureLoginStatus();
      setAuthStatus(status);
      setError(status.error ?? null);
      return status;
    } catch (err) {
      logger.warn("azure_status_fetch_failed", { error: String(err) });
      return null;
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchStatus]);

  // Start polling when device code is pending
  useEffect(() => {
    if (authStatus?.device_code_pending) {
      pollRef.current = setInterval(async () => {
        const status = await fetchStatus();
        if (status && !status.device_code_pending) {
          if (pollRef.current) clearInterval(pollRef.current);
        }
      }, 3000);
      return () => {
        if (pollRef.current) clearInterval(pollRef.current);
      };
    }
  }, [authStatus?.device_code_pending, fetchStatus]);

  const handleInitiateLogin = useCallback(async () => {
    setInitiating(true);
    setError(null);
    try {
      await api.initiateAzureLogin();
      // Poll for status after initiating
      await fetchStatus();
    } catch (err) {
      setError(String(err));
    } finally {
      setInitiating(false);
    }
  }, [fetchStatus]);

  const handleLogout = useCallback(async () => {
    setLoggingOut(true);
    try {
      await api.azureLogout();
      await fetchStatus();
    } catch (err) {
      setError(String(err));
    } finally {
      setLoggingOut(false);
    }
  }, [fetchStatus]);

  const handleCopyCode = useCallback((code: string) => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, []);

  const formatExpiry = (seconds: number | null) => {
    if (!seconds || seconds <= 0) return "expired";
    const mins = Math.floor(seconds / 60);
    const hrs = Math.floor(mins / 60);
    if (hrs > 0) return `${hrs}h ${mins % 60}m`;
    return `${mins}m`;
  };

  // Auth status badge
  const statusBadge = authStatus?.authenticated
    ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300"
    : authStatus?.device_code_pending
      ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
      : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300";

  const statusLabel = authStatus?.authenticated
    ? "Authenticated"
    : authStatus?.device_code_pending
      ? "Pending..."
      : "Not Authenticated";

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Shield className="h-4 w-4 text-[var(--color-text-secondary)]" />
        <h4 className="text-sm font-medium text-[var(--color-text-secondary)]">Azure Entra ID Login</h4>
        <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${statusBadge}`}>
          {statusLabel}
        </span>
      </div>

      {/* Authenticated state */}
      {authStatus?.authenticated && (
        <div className="rounded-lg border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 px-4 py-3 space-y-2">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              {authStatus.user_display_name && (
                <p className="text-sm font-medium text-green-800 dark:text-green-200">
                  {authStatus.user_display_name}
                </p>
              )}
              {authStatus.user_email && (
                <p className="text-xs text-green-600 dark:text-green-400">
                  {authStatus.user_email}
                </p>
              )}
              <div className="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400">
                <Clock className="h-3 w-3" />
                <span>
                  via {authStatus.auth_method ?? "unknown"} · expires in {formatExpiry(authStatus.expires_in_seconds ?? null)}
                </span>
              </div>
            </div>
            <Button size="sm" variant="ghost" onClick={handleLogout} disabled={loggingOut}>
              {loggingOut ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <LogOut className="h-3.5 w-3.5" />}
              Logout
            </Button>
          </div>
        </div>
      )}

      {/* Device code pending state */}
      {authStatus?.device_code_pending && authStatus.device_code_info && (
        <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 px-4 py-3 space-y-3">
          <p className="text-sm text-amber-800 dark:text-amber-200">
            Open the link below and enter the code to sign in:
          </p>
          <div className="flex items-center gap-3">
            <div className="flex-1 flex items-center gap-2">
              <code className="rounded bg-white dark:bg-gray-800 px-3 py-1.5 text-lg font-mono font-bold tracking-wider text-amber-800 dark:text-amber-200 border border-amber-300 dark:border-amber-700">
                {authStatus.device_code_info.user_code}
              </code>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleCopyCode(authStatus.device_code_info!.user_code)}
                title="Copy code"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
              </Button>
            </div>
            <a
              href={authStatus.device_code_info.verification_uri}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-lg bg-amber-600 hover:bg-amber-700 text-white px-3 py-1.5 text-sm font-medium transition-colors"
            >
              Open Login Page <ExternalLink className="h-3 w-3" />
            </a>
          </div>
          <div className="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>Waiting for sign-in... ({formatExpiry(authStatus.device_code_info.expires_in_seconds)} remaining)</span>
          </div>
        </div>
      )}

      {/* Not authenticated — show login button */}
      {!authStatus?.authenticated && !authStatus?.device_code_pending && (
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={handleInitiateLogin}
            disabled={initiating}
          >
            {initiating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <LogIn className="h-3.5 w-3.5" />}
            Login with Azure
          </Button>
          <span className="text-xs text-[var(--color-text-secondary)]">
            Sign in with your Microsoft account for token-based auth
          </span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-900/20 px-3 py-2 text-xs text-red-700 dark:text-red-300">
          {error}
        </div>
      )}
    </div>
  );
}

/* ---------- config field ---------- */

interface ConfigFieldProps {
  field: ProviderFieldSchema;
  value: string;
  isDirty: boolean;
  isSecretVisible: boolean;
  originalValue: string;
  onChange: (value: string) => void;
  onToggleVisibility: () => void;
}

function ConfigField({
  field,
  value,
  isDirty,
  isSecretVisible,
  originalValue,
  onChange,
  onToggleVisibility,
}: ConfigFieldProps) {
  const inputClass =
    "h-10 w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 text-sm text-[var(--color-text)] focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500";

  return (
    <div className="space-y-1">
      <label className="flex items-center gap-1 text-sm font-medium text-[var(--color-text)]">
        {field.label}
        {field.required && <span className="text-red-500">*</span>}
        {isDirty && <span className="text-xs text-primary-500 ml-1">(modified)</span>}
      </label>
      {field.field_type === "select" ? (
        <select value={value} onChange={(e) => onChange(e.target.value)} className={inputClass}>
          <option value="">{field.default ? `Default: ${field.default}` : "Select..."}</option>
          {(() => {
            const groups: { label: string | null; items: string[] }[] = [];
            let current: { label: string | null; items: string[] } = { label: null, items: [] };
            for (const opt of field.options ?? []) {
              if (opt.startsWith("---")) {
                if (current.items.length > 0 || current.label) groups.push(current);
                current = { label: opt.slice(3), items: [] };
              } else {
                current.items.push(opt);
              }
            }
            if (current.items.length > 0 || current.label) groups.push(current);
            return groups.map((g) =>
              g.label ? (
                <optgroup key={g.label} label={g.label}>
                  {g.items.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </optgroup>
              ) : (
                g.items.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))
              ),
            );
          })()}
        </select>
      ) : field.field_type === "password" ? (
        <div className="relative">
          <input
            type={isSecretVisible ? "text" : "password"}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={originalValue || field.default || ""}
            className={inputClass + " pr-10"}
          />
          <button
            type="button"
            onClick={onToggleVisibility}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
            aria-label={isSecretVisible ? "Hide value" : "Show value"}
          >
            {isSecretVisible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.default || ""}
          className={inputClass}
        />
      )}
    </div>
  );
}

/* ---------- capability badge ---------- */

function CapBadge({ label }: { label: string }) {
  return (
    <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">
      {label}
    </span>
  );
}
