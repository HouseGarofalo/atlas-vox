import { describe, it, expect, beforeEach, vi } from "vitest";
import { useProviderStore } from "../../stores/providerStore";

vi.mock("../../utils/logger", () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock("../../services/api", () => ({
  api: {
    listProviders: vi.fn(),
    checkProviderHealth: vi.fn(),
  },
}));

import { api } from "../../services/api";

const mockApi = vi.mocked(api);

describe("ProviderStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useProviderStore.setState({
      providers: [],
      loading: false,
      error: null,
    });
  });

  describe("fetchProviders", () => {
    it("fetches providers successfully", async () => {
      const providers = [
        { id: "1", name: "kokoro", display_name: "Kokoro", enabled: true },
        { id: "2", name: "piper", display_name: "Piper", enabled: true },
      ];
      mockApi.listProviders.mockResolvedValue({ providers, count: 2 } as any);

      await useProviderStore.getState().fetchProviders();

      const state = useProviderStore.getState();
      expect(state.providers).toEqual(providers);
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
    });

    it("handles fetch errors", async () => {
      mockApi.listProviders.mockRejectedValue(new Error("Server error"));

      await useProviderStore.getState().fetchProviders();

      const state = useProviderStore.getState();
      expect(state.error).toBe("Server error");
      expect(state.loading).toBe(false);
    });
  });

  describe("checkHealth", () => {
    it("updates provider health on success", async () => {
      useProviderStore.setState({
        providers: [
          { id: "1", name: "kokoro", health: null } as any,
        ],
      });
      const healthResult = { name: "kokoro", healthy: true, latency_ms: 50, error: null };
      mockApi.checkProviderHealth.mockResolvedValue(healthResult as any);

      await useProviderStore.getState().checkHealth("kokoro");

      const provider = useProviderStore.getState().providers[0];
      expect(provider.health).toEqual(healthResult);
    });

    it("sets unhealthy state on error", async () => {
      useProviderStore.setState({
        providers: [
          { id: "1", name: "kokoro", health: null } as any,
        ],
      });
      mockApi.checkProviderHealth.mockRejectedValue(new Error("Connection refused"));

      await useProviderStore.getState().checkHealth("kokoro");

      const provider = useProviderStore.getState().providers[0];
      expect(provider.health).toEqual({
        name: "kokoro",
        healthy: false,
        latency_ms: null,
        error: "Connection refused",
      });
    });
  });

  describe("checkAllHealth", () => {
    it("checks health for all providers", async () => {
      useProviderStore.setState({
        providers: [
          { id: "1", name: "kokoro", health: null } as any,
          { id: "2", name: "piper", health: null } as any,
        ],
      });
      mockApi.checkProviderHealth.mockResolvedValue({
        name: "test",
        healthy: true,
        latency_ms: 50,
        error: null,
      } as any);

      await useProviderStore.getState().checkAllHealth();

      expect(mockApi.checkProviderHealth).toHaveBeenCalledTimes(2);
      expect(mockApi.checkProviderHealth).toHaveBeenCalledWith("kokoro");
      expect(mockApi.checkProviderHealth).toHaveBeenCalledWith("piper");
    });
  });
});
