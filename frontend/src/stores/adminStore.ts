import { create } from "zustand";
import { api } from "../services/api";
import type { ProviderConfigResponse, ProviderTestResponse } from "../types";

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
    set((s) => ({ loadingConfig: { ...s.loadingConfig, [name]: true } }));
    try {
      const config = await api.getProviderConfig(name);
      set((s) => ({
        providerConfigs: { ...s.providerConfigs, [name]: config },
        loadingConfig: { ...s.loadingConfig, [name]: false },
      }));
    } catch {
      set((s) => ({ loadingConfig: { ...s.loadingConfig, [name]: false } }));
    }
  },

  saveProviderConfig: async (name, data) => {
    set((s) => ({ savingConfig: { ...s.savingConfig, [name]: true } }));
    try {
      const config = await api.updateProviderConfig(name, data);
      set((s) => ({
        providerConfigs: { ...s.providerConfigs, [name]: config },
        savingConfig: { ...s.savingConfig, [name]: false },
      }));
    } catch {
      set((s) => ({ savingConfig: { ...s.savingConfig, [name]: false } }));
      throw new Error("Failed to save provider config");
    }
  },

  testProvider: async (name, text) => {
    set((s) => ({ testingProvider: { ...s.testingProvider, [name]: true } }));
    try {
      const result = await api.testProvider(name, text ? { text } : undefined);
      set((s) => ({
        testResults: { ...s.testResults, [name]: result },
        testingProvider: { ...s.testingProvider, [name]: false },
      }));
    } catch {
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
