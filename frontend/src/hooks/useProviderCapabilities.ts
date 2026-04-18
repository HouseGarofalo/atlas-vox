import { useEffect, useMemo } from "react";
import { useProviderStore } from "../stores/providerStore";
import type { Provider, ProviderCapabilities } from "../types";

/**
 * Read capabilities for a named provider from the provider store, ensuring
 * the list is fetched if nothing has been loaded yet. Returns a stable
 * reference keyed on the provider name so consumers can safely use it in
 * dependency arrays.
 *
 * Callers should use the returned flags to hide/show controls instead of
 * branching on provider-name string comparisons — that way, adding a new
 * provider with the same capability (say, streaming) doesn't require
 * touching every consumer.
 */
export interface ProviderCapabilityView {
  provider: Provider | null;
  capabilities: ProviderCapabilities | null;
  loading: boolean;
  error: string | null;
  // Convenience boolean mirrors so consumers can one-line the common checks.
  supportsSsml: boolean;
  supportsStreaming: boolean;
  supportsCloning: boolean;
  supportsFineTuning: boolean;
  supportsZeroShot: boolean;
  supportsWordBoundaries: boolean;
  supportsPronunciationAssessment: boolean;
  supportsTranscription: boolean;
  supportedLanguages: string[];
  supportedOutputFormats: string[];
  maxTextLength: number;
}

const EMPTY_VIEW: ProviderCapabilityView = {
  provider: null,
  capabilities: null,
  loading: false,
  error: null,
  supportsSsml: false,
  supportsStreaming: false,
  supportsCloning: false,
  supportsFineTuning: false,
  supportsZeroShot: false,
  supportsWordBoundaries: false,
  supportsPronunciationAssessment: false,
  supportsTranscription: false,
  supportedLanguages: [],
  supportedOutputFormats: [],
  maxTextLength: 5000,
};

export function useProviderCapabilities(
  providerName: string | null | undefined,
): ProviderCapabilityView {
  const providers = useProviderStore((s) => s.providers);
  const loading = useProviderStore((s) => s.loading);
  const error = useProviderStore((s) => s.error);
  const lastFetchedAt = useProviderStore((s) => s.lastFetchedAt);
  const fetchProviders = useProviderStore((s) => s.fetchProviders);

  // Ensure the store has loaded something — the store itself will no-op
  // within the stale window so this is safe to call on every mount.
  useEffect(() => {
    if (providerName && !lastFetchedAt && !loading) {
      void fetchProviders();
    }
  }, [providerName, lastFetchedAt, loading, fetchProviders]);

  return useMemo(() => {
    if (!providerName) return EMPTY_VIEW;
    const provider = providers.find((p) => p.name === providerName) ?? null;
    const caps = provider?.capabilities ?? null;
    if (!caps) {
      return { ...EMPTY_VIEW, provider, loading, error };
    }
    return {
      provider,
      capabilities: caps,
      loading,
      error,
      supportsSsml: caps.supports_ssml,
      supportsStreaming: caps.supports_streaming,
      supportsCloning: caps.supports_cloning,
      supportsFineTuning: caps.supports_fine_tuning,
      supportsZeroShot: caps.supports_zero_shot,
      supportsWordBoundaries: caps.supports_word_boundaries,
      supportsPronunciationAssessment: caps.supports_pronunciation_assessment,
      supportsTranscription: caps.supports_transcription,
      supportedLanguages: caps.supported_languages,
      supportedOutputFormats: caps.supported_output_formats,
      maxTextLength: caps.max_text_length,
    };
  }, [providerName, providers, loading, error]);
}
