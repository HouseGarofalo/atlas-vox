import { create } from "zustand";
import { api } from "../services/api";
import type { VoiceProfile } from "../types";

interface ProfileState {
  profiles: VoiceProfile[];
  loading: boolean;
  error: string | null;
  fetchProfiles: () => Promise<void>;
  createProfile: (data: { name: string; description?: string; language?: string; provider_name: string; tags?: string[] }) => Promise<VoiceProfile>;
  updateProfile: (id: string, data: Record<string, any>) => Promise<void>;
  deleteProfile: (id: string) => Promise<void>;
  activateVersion: (profileId: string, versionId: string) => Promise<void>;
}

export const useProfileStore = create<ProfileState>((set, get) => ({
  profiles: [],
  loading: false,
  error: null,

  fetchProfiles: async () => {
    set({ loading: true, error: null });
    try {
      const { profiles } = await api.listProfiles();
      set({ profiles, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  createProfile: async (data) => {
    const profile = await api.createProfile(data);
    set((s) => ({ profiles: [profile, ...s.profiles] }));
    return profile;
  },

  updateProfile: async (id, data) => {
    const updated = await api.updateProfile(id, data);
    set((s) => ({ profiles: s.profiles.map((p) => (p.id === id ? updated : p)) }));
  },

  deleteProfile: async (id) => {
    await api.deleteProfile(id);
    set((s) => ({ profiles: s.profiles.filter((p) => p.id !== id) }));
  },

  activateVersion: async (profileId, versionId) => {
    const updated = await api.activateVersion(profileId, versionId);
    set((s) => ({ profiles: s.profiles.map((p) => (p.id === profileId ? updated : p)) }));
  },
}));
