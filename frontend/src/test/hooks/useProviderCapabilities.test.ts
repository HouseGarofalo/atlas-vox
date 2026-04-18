import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useProviderCapabilities } from "../../hooks/useProviderCapabilities";
import { useProviderStore } from "../../stores/providerStore";
import type { Provider, ProviderCapabilities } from "../../types";

vi.mock("../../utils/logger", () => ({
  createLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }),
}));

function makeCaps(overrides: Partial<ProviderCapabilities> = {}): ProviderCapabilities {
  return {
    supports_cloning: false,
    supports_fine_tuning: false,
    supports_streaming: false,
    supports_ssml: false,
    supports_zero_shot: false,
    supports_batch: true,
    supports_word_boundaries: false,
    supports_pronunciation_assessment: false,
    supports_transcription: false,
    requires_gpu: false,
    gpu_mode: "none",
    min_samples_for_cloning: 0,
    max_text_length: 5000,
    supported_languages: ["en"],
    supported_output_formats: ["wav"],
    ...overrides,
  };
}

function makeProvider(name: string, caps: ProviderCapabilities | null): Provider {
  return {
    id: name,
    name,
    display_name: name,
    provider_type: "cloud",
    enabled: true,
    gpu_mode: "none",
    capabilities: caps,
    health: null,
  };
}

describe("useProviderCapabilities", () => {
  beforeEach(() => {
    useProviderStore.setState({
      providers: [],
      loading: false,
      error: null,
      lastFetchedAt: null,
    });
  });

  it("returns the empty view when providerName is null", () => {
    const { result } = renderHook(() => useProviderCapabilities(null));
    expect(result.current.provider).toBeNull();
    expect(result.current.capabilities).toBeNull();
    expect(result.current.supportsSsml).toBe(false);
  });

  it("surfaces flags when provider is in the store", () => {
    useProviderStore.setState({
      providers: [makeProvider("azure_speech", makeCaps({ supports_ssml: true, supports_cloning: true }))],
      lastFetchedAt: Date.now(),
    });
    const { result } = renderHook(() => useProviderCapabilities("azure_speech"));
    expect(result.current.supportsSsml).toBe(true);
    expect(result.current.supportsCloning).toBe(true);
    expect(result.current.supportsFineTuning).toBe(false);
  });

  it("recomputes when providerName changes", () => {
    useProviderStore.setState({
      providers: [
        makeProvider("azure_speech", makeCaps({ supports_ssml: true })),
        makeProvider("kokoro", makeCaps({ supports_ssml: false, supports_streaming: true })),
      ],
      lastFetchedAt: Date.now(),
    });
    const { result, rerender } = renderHook(
      ({ name }: { name: string }) => useProviderCapabilities(name),
      { initialProps: { name: "azure_speech" } },
    );
    expect(result.current.supportsSsml).toBe(true);
    rerender({ name: "kokoro" });
    expect(result.current.supportsSsml).toBe(false);
    expect(result.current.supportsStreaming).toBe(true);
  });

  it("triggers a fetch when the store has never loaded", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(undefined);
    useProviderStore.setState({
      providers: [],
      lastFetchedAt: null,
      fetchProviders: fetchSpy,
    } as unknown as Partial<ReturnType<typeof useProviderStore.getState>>);
    renderHook(() => useProviderCapabilities("elevenlabs"));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
  });

  it("handles providers with no capabilities payload yet", () => {
    useProviderStore.setState({
      providers: [makeProvider("mystery", null)],
      lastFetchedAt: Date.now(),
    });
    const { result } = renderHook(() => useProviderCapabilities("mystery"));
    expect(result.current.provider).not.toBeNull();
    expect(result.current.capabilities).toBeNull();
    expect(result.current.supportsSsml).toBe(false);
  });
});
