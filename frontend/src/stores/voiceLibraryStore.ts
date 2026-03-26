import { create } from "zustand";
import { api } from "../services/api";
import type { Voice } from "../types";

interface VoiceLibraryFilters {
  provider: string | null;
  language: string | null;
  gender: string | null;
  search: string;
}

interface VoiceLibraryState {
  voices: Voice[];
  loading: boolean;
  error: string | null;
  filters: VoiceLibraryFilters;

  fetchAllVoices: () => Promise<void>;
  setFilter: (key: keyof VoiceLibraryFilters, value: string | null) => void;
  filteredVoices: () => Voice[];
}

export const useVoiceLibraryStore = create<VoiceLibraryState>((set, get) => ({
  voices: [],
  loading: false,
  error: null,
  filters: {
    provider: null,
    language: null,
    gender: null,
    search: "",
  },

  fetchAllVoices: async () => {
    set({ loading: true, error: null });
    try {
      const { voices } = await api.listAllVoices();
      set({ voices, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  setFilter: (key, value) => {
    set((s) => ({
      filters: { ...s.filters, [key]: value },
    }));
  },

  filteredVoices: () => {
    const { voices, filters } = get();
    let result = voices;

    if (filters.provider) {
      result = result.filter((v) => v.provider === filters.provider);
    }

    if (filters.language) {
      result = result.filter((v) => v.language === filters.language);
    }

    if (filters.gender) {
      result = result.filter((v) => {
        if (v.gender) return v.gender === filters.gender;
        // Fallback: infer from voice_id for Kokoro pattern
        const id = v.voice_id.toLowerCase();
        if (filters.gender === "Female") return /^[ab]f[_-]/.test(id);
        if (filters.gender === "Male") return /^[ab]m[_-]/.test(id);
        return false;
      });
    }

    if (filters.search) {
      const q = filters.search.toLowerCase();
      result = result.filter(
        (v) =>
          v.name.toLowerCase().includes(q) ||
          v.voice_id.toLowerCase().includes(q) ||
          v.provider_display.toLowerCase().includes(q)
      );
    }

    return result;
  },
}));
