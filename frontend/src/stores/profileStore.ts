import { create } from "zustand";
import { api } from "../services/api";
import type { VoiceProfile } from "../types";
import { createLogger } from "../utils/logger";
import { getErrorMessage } from "../utils/errors";

const logger = createLogger("ProfileStore");

const STALE_MS = 30_000; // 30 seconds

interface ProfileState {
  profiles: VoiceProfile[];
  loading: boolean;
  error: string | null;
  lastFetchedAt: number | null;
  _abortController: AbortController | null;
  fetchProfiles: (force?: boolean) => Promise<void>;
  createProfile: (data: { name: string; description?: string; language?: string; provider_name: string; voice_id?: string; tags?: string[] }) => Promise<VoiceProfile>;
  updateProfile: (id: string, data: Partial<Pick<VoiceProfile, "name" | "description" | "language" | "provider_name" | "voice_id" | "tags">>) => Promise<void>;
  deleteProfile: (id: string) => Promise<void>;
  activateVersion: (profileId: string, versionId: string) => Promise<void>;
  reset: () => void;
}

export const useProfileStore = create<ProfileState>((set, get) => ({
  profiles: [],
  loading: false,
  error: null,
  lastFetchedAt: null,
  _abortController: null,

  fetchProfiles: async (force = false) => {
    const { lastFetchedAt, loading } = get();
    if (!force && lastFetchedAt && Date.now() - lastFetchedAt < STALE_MS) return;
    if (loading) return;

    const prevController = get()._abortController;
    if (prevController) {
      logger.debug("aborting_previous_request");
      prevController.abort();
    }

    const controller = new AbortController();
    set({ _abortController: controller });

    logger.info("fetchProfiles");
    set({ loading: true, error: null });
    try {
      const { profiles } = await api.listProfiles();
      logger.info("fetchProfiles_success", { count: profiles.length });
      set({ profiles, loading: false, lastFetchedAt: Date.now() });
    } catch (e: unknown) {
      if ((e as Error).name === 'AbortError') {
        logger.debug("fetchProfiles_aborted");
        return;
      }
      const message = getErrorMessage(e);
      logger.error("fetchProfiles_failed", { error: message });
      set({ error: message, loading: false });
    }
  },

  reset: () => set({ profiles: [], loading: false, error: null, lastFetchedAt: null, _abortController: null }),

  createProfile: async (data) => {
    logger.info("createProfile", { name: data.name, provider: data.provider_name });
    const profile = await api.createProfile(data);
    logger.info("createProfile_success", { id: profile.id });
    set((s) => ({ profiles: [profile, ...s.profiles] }));
    return profile;
  },

  updateProfile: async (id, data) => {
    logger.info("updateProfile", { id });
    const updated = await api.updateProfile(id, data);
    set((s) => ({ profiles: s.profiles.map((p) => (p.id === id ? updated : p)) }));
  },

  deleteProfile: async (id) => {
    logger.info("deleteProfile", { id });
    await api.deleteProfile(id);
    set((s) => ({ profiles: s.profiles.filter((p) => p.id !== id) }));
  },

  activateVersion: async (profileId, versionId) => {
    logger.info("activateVersion", { profileId, versionId });
    const updated = await api.activateVersion(profileId, versionId);
    set((s) => ({ profiles: s.profiles.map((p) => (p.id === profileId ? updated : p)) }));
  },
}));
