import { create } from "zustand";
import { api } from "../services/api";
import type { VoiceProfile } from "../types";
import { createLogger } from "../utils/logger";

const logger = createLogger("ProfileStore");

interface ProfileState {
  profiles: VoiceProfile[];
  loading: boolean;
  error: string | null;
  fetchProfiles: () => Promise<void>;
  createProfile: (data: { name: string; description?: string; language?: string; provider_name: string; voice_id?: string; tags?: string[] }) => Promise<VoiceProfile>;
  updateProfile: (id: string, data: Partial<Pick<VoiceProfile, "name" | "description" | "language" | "provider_name" | "voice_id" | "tags">>) => Promise<void>;
  deleteProfile: (id: string) => Promise<void>;
  activateVersion: (profileId: string, versionId: string) => Promise<void>;
}

export const useProfileStore = create<ProfileState>((set) => ({
  profiles: [],
  loading: false,
  error: null,

  fetchProfiles: async () => {
    logger.info("fetchProfiles");
    set({ loading: true, error: null });
    try {
      const { profiles } = await api.listProfiles();
      logger.info("fetchProfiles_success", { count: profiles.length });
      set({ profiles, loading: false });
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to fetch profiles";
      logger.error("fetchProfiles_failed", { error: message });
      set({ error: message, loading: false });
    }
  },

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
