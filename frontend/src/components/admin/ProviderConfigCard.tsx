import { useState, useEffect, useCallback, useRef } from "react";
import { ChevronDown, ChevronRight, Eye, EyeOff, Loader2, Check, ExternalLink } from "lucide-react";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { useAdminStore } from "../../stores/adminStore";
import { useProviderStore } from "../../stores/providerStore";
import ProviderLogo from "../providers/ProviderLogo";
import { PROVIDER_METADATA } from "../../data/providerMetadata";
import { createLogger } from "../../utils/logger";
import type { Provider, ProviderFieldSchema } from "../../types";

const logger = createLogger("ProviderConfigCard");

const PRICING_COLORS: Record<string, string> = {
  "open-source": "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  freemium: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300",
  paid: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  free: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
};

interface ProviderConfigCardProps {
  provider: Provider;
}

export default function ProviderConfigCard({ provider }: ProviderConfigCardProps) {
  const [expanded, setExpanded] = useState(false);
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

  // Load config when expanded
  useEffect(() => {
    if (expanded && !config && !isLoading) {
      fetchProviderConfig(provider.name);
    }
  }, [expanded, config, isLoading, provider.name, fetchProviderConfig]);

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
    logger.debug("field_change", { provider: provider.name, field: fieldName });
    setFormValues((prev) => ({ ...prev, [fieldName]: value }));
    setDirtyFields((prev) => new Set(prev).add(fieldName));
  }, [provider.name]);

  const toggleSecretVisibility = useCallback((fieldName: string) => {
    setVisibleSecrets((prev) => {
      const next = new Set(prev);
      if (next.has(fieldName)) {
        next.delete(fieldName);
      } else {
        next.add(fieldName);
      }
      return next;
    });
  }, []);

  const handleToggleEnabled = useCallback(async () => {
    logger.info("toggle_enabled", { provider: provider.name, enabled: !provider.enabled });
    try {
      await saveProviderConfig(provider.name, { enabled: !provider.enabled });
    } catch (e: unknown) {
      logger.error("toggle_enabled_error", { provider: provider.name, error: String(e) });
    }
  }, [provider.name, provider.enabled, saveProviderConfig]);

  const handleSave = useCallback(async () => {
    if (dirtyFields.size === 0) return;

    const changedConfig: Record<string, string> = {};
    for (const fieldName of dirtyFields) {
      changedConfig[fieldName] = formValues[fieldName];
    }

    logger.info("save_config", { provider: provider.name, fields_changed: dirtyFields.size });
    try {
      await saveProviderConfig(provider.name, { config: changedConfig });
      logger.info("save_config_complete", { provider: provider.name });
      setSavedRecently(true);
      if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
      savedTimerRef.current = setTimeout(() => setSavedRecently(false), 2000);
    } catch (e: unknown) {
      logger.error("save_config_error", { provider: provider.name, error: String(e) });
    }
  }, [dirtyFields, formValues, provider.name, saveProviderConfig]);

  const handleHealthCheck = useCallback(() => {
    logger.info("health_check", { provider: provider.name });
    checkHealth(provider.name);
  }, [provider.name, checkHealth]);

  const handleTest = useCallback(() => {
    logger.info("test_provider", { provider: provider.name, text_length: testText.length });
    testProvider(provider.name, testText);
  }, [provider.name, testText, testProvider]);

  const healthStatus = provider.health?.healthy
    ? "healthy"
    : provider.health
      ? "unhealthy"
      : "pending";

  const meta = PROVIDER_METADATA[provider.name];

  return (
    <Card className="overflow-hidden">
      {/* Header - always visible */}
      <button
        type="button"
        className="flex w-full items-start gap-3 text-left"
        onClick={() => { logger.info("panel_toggle", { provider: provider.name, expanded: !expanded }); setExpanded(!expanded); }}
      >
        <ProviderLogo name={provider.name} size={36} className="flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {meta ? (
              <a
                href={meta.website}
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold hover:text-primary-500 transition-colors inline-flex items-center gap-1"
                onClick={(e) => e.stopPropagation()}
              >
                {provider.display_name}
                <ExternalLink className="h-3 w-3 opacity-40" />
              </a>
            ) : (
              <h3 className="font-semibold">{provider.display_name}</h3>
            )}
            {meta && (() => {
              const tier = meta.pricingTier;
              const colors = PRICING_COLORS[tier] ?? "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300";
              return <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${colors}`}>{tier}</span>;
            })()}
            <Badge status={provider.provider_type} />
            <Badge status={healthStatus} />
          </div>
          {meta && (
            <p className="text-xs text-[var(--color-text-secondary)] mt-1 leading-relaxed line-clamp-2">
              {meta.description}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5">
            {provider.capabilities && (
              <div className="flex flex-wrap gap-1">
                {provider.capabilities.supports_cloning && <CapBadge label="Cloning" />}
                {provider.capabilities.supports_streaming && <CapBadge label="Streaming" />}
                {provider.capabilities.supports_ssml && <CapBadge label="SSML" />}
                {provider.capabilities.supports_fine_tuning && <CapBadge label="Fine-tune" />}
                {provider.capabilities.supports_zero_shot && <CapBadge label="Zero-shot" />}
              </div>
            )}
            <span className="text-[10px] text-[var(--color-text-secondary)]">
              GPU: {provider.capabilities?.gpu_mode || provider.gpu_mode || "none"}
              {meta && <span className="ml-2 opacity-70">{meta.modelInfo}</span>}
            </span>
          </div>
          {provider.health && !expanded && (
            <div className={`text-xs mt-1 ${provider.health.healthy ? "text-green-600 dark:text-green-400" : "text-red-500 dark:text-red-400"}`}>
              {provider.health.healthy ? `Healthy - ${provider.health.latency_ms}ms` : `Error: ${provider.health.error}`}
            </div>
          )}
        </div>
        <div className="flex items-center gap-3 flex-shrink-0 mt-1">
          {/* Enable/Disable toggle */}
          <div
            role="switch"
            aria-checked={provider.enabled}
            tabIndex={0}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors cursor-pointer ${
              provider.enabled ? "bg-primary-500" : "bg-gray-300 dark:bg-gray-600"
            }`}
            onClick={(e) => {
              e.stopPropagation();
              handleToggleEnabled();
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.stopPropagation();
                e.preventDefault();
                handleToggleEnabled();
              }
            }}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                provider.enabled ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </div>
          {expanded ? (
            <ChevronDown className="h-5 w-5 text-[var(--color-text-secondary)]" />
          ) : (
            <ChevronRight className="h-5 w-5 text-[var(--color-text-secondary)]" />
          )}
        </div>
      </button>

      {/* Expanded section */}
      {expanded && (
        <div className="mt-4 space-y-5 border-t border-[var(--color-border)] pt-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-[var(--color-text-secondary)]" />
            </div>
          ) : config ? (
            <>
              {/* Provider description & website */}
              {PROVIDER_METADATA[provider.name] && (
                <div className="space-y-1">
                  <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                    {PROVIDER_METADATA[provider.name].description}
                  </p>
                  <a
                    href={PROVIDER_METADATA[provider.name].website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-primary-500 hover:text-primary-600 transition-colors"
                    onClick={(e) => e.stopPropagation()}
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
                <div className={`text-xs rounded-lg px-3 py-2 ${
                  provider.health.healthy
                    ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                    : "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                }`}>
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
                  <Button size="sm" variant="secondary" onClick={handleTest} disabled={isTesting || !testText.trim()}>
                    {isTesting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                    Test
                  </Button>
                </div>
                {testResult && (
                  <div className={`text-xs rounded-lg px-3 py-2 ${
                    testResult.success
                      ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                      : "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                  }`}>
                    {testResult.success ? (
                      <div className="space-y-1">
                        <p>Success - latency: {testResult.latency_ms}ms{testResult.duration_seconds != null ? `, duration: ${testResult.duration_seconds.toFixed(2)}s` : ""}</p>
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
            </>
          ) : (
            <p className="text-sm text-[var(--color-text-secondary)]">Failed to load configuration.</p>
          )}
        </div>
      )}
    </Card>
  );
}

interface ConfigFieldProps {
  field: ProviderFieldSchema;
  value: string;
  isDirty: boolean;
  isSecretVisible: boolean;
  originalValue: string;
  onChange: (value: string) => void;
  onToggleVisibility: () => void;
}

function ConfigField({ field, value, isDirty, isSecretVisible, originalValue, onChange, onToggleVisibility }: ConfigFieldProps) {
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
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={inputClass}
        >
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
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </optgroup>
              ) : (
                g.items.map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))
              )
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

function CapBadge({ label }: { label: string }) {
  return <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">{label}</span>;
}
