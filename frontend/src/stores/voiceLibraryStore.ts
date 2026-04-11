import { create } from "zustand";
import { api } from "../services/api";
import type { Voice } from "../types";
import { createLogger } from "../utils/logger";
import { getErrorMessage } from "../utils/errors";

const logger = createLogger("VoiceLibraryStore");

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
  /** Cached filtered result — recomputed when voices or filters change. */
  _filteredVoices: Voice[];

  fetchAllVoices: () => Promise<void>;
  setFilter: (key: keyof VoiceLibraryFilters, value: string | null) => void;
  filteredVoices: () => Voice[];
}

/** Pure function: compute filtered voices from current state. */
function computeFiltered(voices: Voice[], filters: VoiceLibraryFilters): Voice[] {
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
  _filteredVoices: [],

  fetchAllVoices: async () => {
    logger.info("fetchAllVoices");
    set({ loading: true, error: null });
    try {
      const { voices } = await api.listAllVoices();
      logger.info("fetchAllVoices_success", { count: voices.length });
      const { filters } = get();
      set({ voices, loading: false, _filteredVoices: computeFiltered(voices, filters) });
    } catch (e: unknown) {
      const message = getErrorMessage(e);
      logger.error("fetchAllVoices_failed", { error: message });
      set({ error: message, loading: false });
    }
  },

  setFilter: (key, value) => {
    logger.info("setFilter", { key, value });
    set((s) => {
      const filters = { ...s.filters, [key]: value };
      return { filters, _filteredVoices: computeFiltered(s.voices, filters) };
    });
  },

  /** Returns cached filtered result for zero-cost repeated access. */
  filteredVoices: () => get()._filteredVoices,
}));
