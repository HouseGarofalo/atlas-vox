import { create } from "zustand";
import { api } from "../services/api";
import { createLogger } from "../utils/logger";
import type { SystemSetting, SystemInfo, BackupResponse } from "../types";

const logger = createLogger("systemSettingsStore");
const STALE_MS = 30_000;

interface SystemSettingsState {
  settings: SystemSetting[];
  systemInfo: SystemInfo | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  lastFetchedAt: number | null;

  fetchSettings: (category?: string, force?: boolean) => Promise<void>;
  fetchSystemInfo: () => Promise<void>;
  updateSetting: (category: string, key: string, value: string) => Promise<void>;
  bulkUpdateSettings: (
    category: string,
    updates: Array<{ key: string; value: string }>
  ) => Promise<void>;
  deleteSetting: (category: string, key: string) => Promise<void>;
  seedDefaults: () => Promise<number>;
  backupSettings: () => Promise<BackupResponse>;
  restoreSettings: (data: string) => Promise<number>;
}

export const useSystemSettingsStore = create<SystemSettingsState>((set, get) => ({
  settings: [],
  systemInfo: null,
  loading: false,
  saving: false,
  error: null,
  lastFetchedAt: null,

  fetchSettings: async (category?: string, force = false) => {
    const { lastFetchedAt, loading } = get();
    if (!force && lastFetchedAt && Date.now() - lastFetchedAt < STALE_MS) return;
    if (loading) return;

    set({ loading: true, error: null });
    try {
      const data = await api.listSettings(category);
      set({ settings: data, loading: false, lastFetchedAt: Date.now() });
      logger.info("settings_fetched", { count: data.length, category });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to load settings";
      set({ error: msg, loading: false });
      logger.error("settings_fetch_error", { error: msg });
    }
  },

  fetchSystemInfo: async () => {
    try {
      const info = await api.getSystemInfo();
      set({ systemInfo: info });
      logger.info("system_info_fetched");
    } catch (e: unknown) {
      logger.error("system_info_error", { error: e instanceof Error ? e.message : String(e) });
    }
  },

  updateSetting: async (category: string, key: string, value: string) => {
    set({ saving: true, error: null });
    try {
      const updated = await api.updateSetting(category, key, { value });
      set((state) => ({
        settings: state.settings.map((s) =>
          s.category === category && s.key === key ? updated : s
        ),
        saving: false,
      }));
      logger.info("setting_updated", { category, key });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to update setting";
      set({ error: msg, saving: false });
      throw e;
    }
  },

  bulkUpdateSettings: async (category, updates) => {
    set({ saving: true, error: null });
    try {
      const result = await api.bulkUpdateSettings(category, updates);
      // Merge updated settings into state
      set((state) => {
        const updated = new Map(result.map((s) => [`${s.category}.${s.key}`, s]));
        return {
          settings: state.settings.map((s) => {
            const key = `${s.category}.${s.key}`;
            return updated.has(key) ? updated.get(key)! : s;
          }),
          saving: false,
        };
      });
      logger.info("settings_bulk_updated", { category, count: updates.length });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to save settings";
      set({ error: msg, saving: false });
      throw e;
    }
  },

  deleteSetting: async (category, key) => {
    try {
      await api.deleteSetting(category, key);
      set((state) => ({
        settings: state.settings.filter(
          (s) => !(s.category === category && s.key === key)
        ),
      }));
      logger.info("setting_deleted", { category, key });
    } catch (e: unknown) {
      logger.error("setting_delete_error", { error: e instanceof Error ? e.message : String(e) });
      throw e;
    }
  },

  seedDefaults: async () => {
    const result = await api.seedSettings();
    if (result.seeded > 0) {
      await get().fetchSettings(undefined, true);
    }
    return result.seeded;
  },

  backupSettings: async () => {
    return await api.backupSettings();
  },

  restoreSettings: async (data: string) => {
    const result = await api.restoreSettings(data);
    await get().fetchSettings(undefined, true);
    return result.restored;
  },
}));
