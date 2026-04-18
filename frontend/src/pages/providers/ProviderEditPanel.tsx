/**
 * ProviderEditPanel — inline edit form for a single provider.
 *
 * Extracted from ProvidersPage.tsx as part of P2-20 (decompose large pages).
 * Reuses the shared `components/providers/ConfigField` component rather than
 * duplicating the form-field rendering logic.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, ExternalLink, Loader2 } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import ProviderLogo from "../../components/providers/ProviderLogo";
import { ConfigField } from "../../components/providers/ConfigField";
import { PROVIDER_METADATA } from "../../data/providerMetadata";
import { useAdminStore } from "../../stores/adminStore";
import { useProviderStore } from "../../stores/providerStore";
import { AzureLoginSection } from "./AzureLoginSection";
import type { Provider } from "../../types";

export interface ProviderEditPanelProps {
  provider: Provider;
  onClose: () => void;
}

export function ProviderEditPanel({ provider, onClose }: ProviderEditPanelProps) {
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
