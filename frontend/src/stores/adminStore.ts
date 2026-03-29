import { create } from "zustand";
import { api } from "../services/api";
import type { ProviderConfigResponse, ProviderTestResponse } from "../types";
import { createLogger } from "../utils/logger";

const logger = createLogger("AdminStore");

interface AdminState {
  providerConfigs: Record<string, ProviderConfigResponse>;
  loadingConfig: Record<string, boolean>;
  savingConfig: Record<string, boolean>;
  testResults: Record<string, ProviderTestResponse>;
  testingProvider: Record<string, boolean>;

  fetchProviderConfig: (name: string) => Promise<void>;
  saveProviderConfig: (name: string, data: { enabled?: boolean; gpu_mode?: string; config?: Record<string, string> }) => Promise<void>;
  testProvider: (name: string, text?: string) => Promise<void>;
}

export const useAdminStore = create<AdminState>((set) => ({
  providerConfigs: {},
  loadingConfig: {},
  savingConfig: {},
  testResults: {},
  testingProvider: {},

  fetchProviderConfig: async (name) => {
    logger.info("fetchProviderConfig", { provider: name });
    set((s) => ({ loadingConfig: { ...s.loadingConfig, [name]: true } }));
    try {
      const config = await api.getProviderConfig(name);
      logger.info("fetchProviderConfig_success", { provider: name });
      set((s) => ({
        providerConfigs: { ...s.providerConfigs, [name]: config },
        loadingConfig: { ...s.loadingConfig, [name]: false },
      }));
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to fetch config";
      logger.error("fetchProviderConfig_failed", { provider: name, error: message });
      set((s) => ({ loadingConfig: { ...s.loadingConfig, [name]: false } }));
    }
  },

  saveProviderConfig: async (name, data) => {
    logger.info("saveProviderConfig", { provider: name });
    set((s) => ({ savingConfig: { ...s.savingConfig, [name]: true } }));
    try {
      const config = await api.updateProviderConfig(name, data);
      logger.info("saveProviderConfig_success", { provider: name });
      set((s) => ({
        providerConfigs: { ...s.providerConfigs, [name]: config },
        savingConfig: { ...s.savingConfig, [name]: false },
      }));
    } catch (e: unknown) {
      logger.error("saveProviderConfig_failed", { provider: name, error: e instanceof Error ? e.message : "unknown" });
      set((s) => ({ savingConfig: { ...s.savingConfig, [name]: false } }));
      throw new Error("Failed to save provider config");
    }
  },

  testProvider: async (name, text) => {
    logger.info("testProvider", { provider: name, hasText: !!text });
    set((s) => ({ testingProvider: { ...s.testingProvider, [name]: true } }));
    try {
      const result = await api.testProvider(name, text ? { text } : undefined);
      logger.info("testProvider_success", { provider: name, success: result.success });
      set((s) => ({
        testResults: { ...s.testResults, [name]: result },
        testingProvider: { ...s.testingProvider, [name]: false },
      }));
    } catch (e: unknown) {
      logger.error("testProvider_failed", { provider: name, error: e instanceof Error ? e.message : "unknown" });
      set((s) => ({
        testResults: {
          ...s.testResults,
          [name]: { success: false, audio_url: null, duration_seconds: null, latency_ms: 0, error: "Test request failed" },
        },
        testingProvider: { ...s.testingProvider, [name]: false },
      }));
    }
  },
}));
