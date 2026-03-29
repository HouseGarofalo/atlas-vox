import { create } from "zustand";
import { api } from "../services/api";
import type { Provider } from "../types";
import { createLogger } from "../utils/logger";

const logger = createLogger("ProviderStore");

interface ProviderState {
  providers: Provider[];
  loading: boolean;
  error: string | null;
  fetchProviders: () => Promise<void>;
  checkHealth: (name: string) => Promise<void>;
  checkAllHealth: () => Promise<void>;
}

export const useProviderStore = create<ProviderState>((set) => ({
  providers: [],
  loading: false,
  error: null,

  fetchProviders: async () => {
    logger.info("fetchProviders");
    set({ loading: true, error: null });
    try {
      const { providers } = await api.listProviders();
      logger.info("fetchProviders_success", { count: providers.length });
      set({ providers, loading: false });
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to fetch providers";
      logger.error("fetchProviders_failed", { error: message });
      set({ error: message, loading: false });
    }
  },

  checkHealth: async (name) => {
    logger.info("checkHealth", { provider: name });
    try {
      const health = await api.checkProviderHealth(name);
      logger.info("checkHealth_success", { provider: name, healthy: health.healthy });
      set((s) => ({
        providers: s.providers.map((p) => (p.name === name ? { ...p, health } : p)),
      }));
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Health check failed";
      logger.error("checkHealth_failed", { provider: name, error: message });
      set((s) => ({
        providers: s.providers.map((p) =>
          p.name === name ? { ...p, health: { name, healthy: false, latency_ms: null, error: message } } : p
        ),
      }));
    }
  },

  checkAllHealth: async () => {
    logger.info("checkAllHealth");
    const { providers, checkHealth } = useProviderStore.getState();
    await Promise.allSettled(providers.map((p) => checkHealth(p.name)));
  },
}));
