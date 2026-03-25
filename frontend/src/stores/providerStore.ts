import { create } from "zustand";
import { api } from "../services/api";
import type { Provider } from "../types";

interface ProviderState {
  providers: Provider[];
  loading: boolean;
  error: string | null;
  fetchProviders: () => Promise<void>;
  checkHealth: (name: string) => Promise<void>;
}

export const useProviderStore = create<ProviderState>((set) => ({
  providers: [],
  loading: false,
  error: null,

  fetchProviders: async () => {
    set({ loading: true, error: null });
    try {
      const { providers } = await api.listProviders();
      set({ providers, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  checkHealth: async (name) => {
    try {
      const health = await api.checkProviderHealth(name);
      set((s) => ({
        providers: s.providers.map((p) => (p.name === name ? { ...p, health } : p)),
      }));
    } catch (e: any) {
      set((s) => ({
        providers: s.providers.map((p) =>
          p.name === name ? { ...p, health: { name, healthy: false, latency_ms: null, error: e.message } } : p
        ),
      }));
    }
  },
}));
