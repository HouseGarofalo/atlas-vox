import { create } from "zustand";
import { api } from "../services/api";

interface SynthesisResult {
  id: string;
  audio_url: string;
  duration_seconds: number | null;
  latency_ms: number;
  profile_id: string;
  provider_name: string;
}

interface SynthesisState {
  lastResult: SynthesisResult | null;
  history: any[];
  comparing: boolean;
  comparisonResults: any[];
  loading: boolean;
  error: string | null;
  synthesize: (data: { text: string; profile_id: string; preset_id?: string; speed?: number; pitch?: number; volume?: number; output_format?: string; ssml?: boolean }) => Promise<SynthesisResult>;
  compare: (data: { text: string; profile_ids: string[]; speed?: number; pitch?: number }) => Promise<void>;
  fetchHistory: (limit?: number) => Promise<void>;
}

export const useSynthesisStore = create<SynthesisState>((set) => ({
  lastResult: null,
  history: [],
  comparing: false,
  comparisonResults: [],
  loading: false,
  error: null,

  synthesize: async (data) => {
    set({ loading: true, error: null });
    try {
      const result = await api.synthesize(data);
      set({ lastResult: result, loading: false });
      return result;
    } catch (e: any) {
      set({ error: e.message, loading: false });
      throw e;
    }
  },

  compare: async (data) => {
    set({ comparing: true, error: null, comparisonResults: [] });
    try {
      const { results } = await api.compare(data);
      set({ comparisonResults: results, comparing: false });
    } catch (e: any) {
      set({ error: e.message, comparing: false });
    }
  },

  fetchHistory: async (limit = 50) => {
    try {
      const history = await api.getSynthesisHistory(limit);
      set({ history });
    } catch (e: any) {
      set({ error: e.message });
    }
  },
}));
