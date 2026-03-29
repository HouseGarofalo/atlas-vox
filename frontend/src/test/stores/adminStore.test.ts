import { describe, it, expect, beforeEach, vi } from "vitest";
import { useAdminStore } from "../../stores/adminStore";

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
    getProviderConfig: vi.fn(),
    updateProviderConfig: vi.fn(),
    testProvider: vi.fn(),
  },
}));

import { api } from "../../services/api";

const mockApi = vi.mocked(api);

describe("AdminStore", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useAdminStore.setState({
      providerConfigs: {},
      loadingConfig: {},
      savingConfig: {},
      testResults: {},
      testingProvider: {},
    });
  });

  describe("fetchProviderConfig", () => {
    it("fetches config successfully", async () => {
      const config = {
        enabled: true,
        gpu_mode: "cpu",
        config: { model_path: "/models/kokoro" },
        config_schema: [],
      };
      mockApi.getProviderConfig.mockResolvedValue(config as any);

      await useAdminStore.getState().fetchProviderConfig("kokoro");

      const state = useAdminStore.getState();
      expect(state.providerConfigs["kokoro"]).toEqual(config);
      expect(state.loadingConfig["kokoro"]).toBe(false);
    });

    it("sets loading state", async () => {
      let resolvePromise: (value: any) => void;
      mockApi.getProviderConfig.mockReturnValue(
        new Promise((resolve) => {
          resolvePromise = resolve;
        })
      );

      const fetchPromise = useAdminStore.getState().fetchProviderConfig("kokoro");
      expect(useAdminStore.getState().loadingConfig["kokoro"]).toBe(true);

      resolvePromise!({ enabled: true, gpu_mode: "cpu", config: {}, config_schema: [] });
      await fetchPromise;
      expect(useAdminStore.getState().loadingConfig["kokoro"]).toBe(false);
    });

    it("handles fetch errors", async () => {
      mockApi.getProviderConfig.mockRejectedValue(new Error("Not found"));

      await useAdminStore.getState().fetchProviderConfig("nonexistent");

      expect(useAdminStore.getState().loadingConfig["nonexistent"]).toBe(false);
      expect(useAdminStore.getState().providerConfigs["nonexistent"]).toBeUndefined();
    });
  });

  describe("saveProviderConfig", () => {
    it("saves config successfully", async () => {
      const updatedConfig = {
        enabled: true,
        gpu_mode: "docker",
        config: { api_key: "xxx" },
        config_schema: [],
      };
      mockApi.updateProviderConfig.mockResolvedValue(updatedConfig as any);

      await useAdminStore.getState().saveProviderConfig("elevenlabs", {
        enabled: true,
        gpu_mode: "docker",
        config: { api_key: "xxx" },
      });

      const state = useAdminStore.getState();
      expect(state.providerConfigs["elevenlabs"]).toEqual(updatedConfig);
      expect(state.savingConfig["elevenlabs"]).toBe(false);
    });

    it("handles save errors", async () => {
      mockApi.updateProviderConfig.mockRejectedValue(new Error("Validation error"));

      await expect(
        useAdminStore.getState().saveProviderConfig("kokoro", { enabled: false })
      ).rejects.toThrow("Failed to save provider config");

      expect(useAdminStore.getState().savingConfig["kokoro"]).toBe(false);
    });
  });

  describe("testProvider", () => {
    it("tests provider successfully", async () => {
      const testResult = {
        success: true,
        audio_url: "/audio/test.wav",
        duration_seconds: 1.5,
        latency_ms: 200,
        error: null,
      };
      mockApi.testProvider.mockResolvedValue(testResult as any);

      await useAdminStore.getState().testProvider("kokoro", "Hello");

      const state = useAdminStore.getState();
      expect(state.testResults["kokoro"]).toEqual(testResult);
      expect(state.testingProvider["kokoro"]).toBe(false);
    });

    it("handles test failure", async () => {
      mockApi.testProvider.mockRejectedValue(new Error("Connection refused"));

      await useAdminStore.getState().testProvider("kokoro");

      const state = useAdminStore.getState();
      expect(state.testResults["kokoro"]).toEqual({
        success: false,
        audio_url: null,
        duration_seconds: null,
        latency_ms: 0,
        error: "Test request failed",
      });
      expect(state.testingProvider["kokoro"]).toBe(false);
    });

    it("passes text parameter when provided", async () => {
      mockApi.testProvider.mockResolvedValue({
        success: true,
        audio_url: "/audio/test.wav",
        duration_seconds: 1.0,
        latency_ms: 100,
        error: null,
      } as any);

      await useAdminStore.getState().testProvider("kokoro", "Custom text");

      expect(mockApi.testProvider).toHaveBeenCalledWith("kokoro", { text: "Custom text" });
    });

    it("omits text parameter when not provided", async () => {
      mockApi.testProvider.mockResolvedValue({
        success: true,
        audio_url: "/audio/test.wav",
        duration_seconds: 1.0,
        latency_ms: 100,
        error: null,
      } as any);

      await useAdminStore.getState().testProvider("kokoro");

      expect(mockApi.testProvider).toHaveBeenCalledWith("kokoro", undefined);
    });
  });
});
