import { create } from "zustand";
import { api } from "../services/api";
import type { Provider } from "../types";
import { createLogger } from "../utils/logger";
import { getErrorMessage } from "../utils/errors";

const logger = createLogger("ProviderStore");

const STALE_MS = 30_000; // 30 seconds

interface ProviderState {
  providers: Provider[];
  loading: boolean;
  error: string | null;
  lastFetchedAt: number | null;
  fetchProviders: (force?: boolean) => Promise<void>;
  checkHealth: (name: string) => Promise<void>;
  checkAllHealth: () => Promise<void>;
  reset: () => void;
}

export const useProviderStore = create<ProviderState>((set, get) => ({
  providers: [],
  loading: false,
  error: null,
  lastFetchedAt: null,

  fetchProviders: async (force = false) => {
    const { lastFetchedAt, loading } = get();
    if (!force && lastFetchedAt && Date.now() - lastFetchedAt < STALE_MS) return;
    if (loading) return;

    logger.info("fetchProviders");
    set({ loading: true, error: null });
    try {
      const { providers } = await api.listProviders();
      logger.info("fetchProviders_success", { count: providers.length });
      set({ providers, loading: false, lastFetchedAt: Date.now() });
    } catch (e: unknown) {
      const message = getErrorMessage(e);
      logger.error("fetchProviders_failed", { error: message });
      set({ error: message, loading: false });
    }
  },

  reset: () => set({ providers: [], loading: false, error: null, lastFetchedAt: null }),

  checkHealth: async (name) => {
    logger.info("checkHealth", { provider: name });
    try {
      const health = await api.checkProviderHealth(name);
      logger.info("checkHealth_success", { provider: name, healthy: health.healthy });
      set((s) => ({
        providers: s.providers.map((p) => (p.name === name ? { ...p, health } : p)),
      }));
    } catch (e: unknown) {
      const message = getErrorMessage(e);
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
