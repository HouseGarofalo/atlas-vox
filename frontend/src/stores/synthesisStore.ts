import { create } from "zustand";
import { api } from "../services/api";
import type { SynthesisResult, SynthesisHistoryItem, ComparisonResult } from "../types";
import { createLogger } from "../utils/logger";

const logger = createLogger("SynthesisStore");

interface SynthesisState {
  lastResult: SynthesisResult | null;
  history: SynthesisHistoryItem[];
  comparing: boolean;
  comparisonResults: ComparisonResult[];
  loading: boolean;
  error: string | null;
  synthesize: (data: { text: string; profile_id: string; preset_id?: string; speed?: number; pitch?: number; volume?: number; output_format?: string; ssml?: boolean; voice_settings?: Record<string, unknown> }) => Promise<SynthesisResult>;
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
    logger.info("synthesize", { profileId: data.profile_id, textLength: data.text.length });
    set({ loading: true, error: null });
    try {
      const result = await api.synthesize(data);
      logger.info("synthesize_success", { id: result.id, latencyMs: result.latency_ms });
      set({ lastResult: result, loading: false, error: null });
      return result;
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Synthesis failed";
      logger.error("synthesize_failed", { error: message });
      set({ error: message, loading: false });
      throw e;
    }
  },

  compare: async (data) => {
    logger.info("compare", { profileIds: data.profile_ids });
    set({ comparing: true, error: null, comparisonResults: [] });
    try {
      const { results } = await api.compare(data);
      logger.info("compare_success", { resultCount: results.length });
      set({ comparisonResults: results, comparing: false, error: null });
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Comparison failed";
      logger.error("compare_failed", { error: message });
      set({ error: message, comparing: false });
    }
  },

  fetchHistory: async (limit = 50) => {
    logger.info("fetchHistory", { limit });
    try {
      const history = await api.getSynthesisHistory(limit);
      logger.info("fetchHistory_success", { count: history.length });
      set({ history, error: null });
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to fetch history";
      logger.error("fetchHistory_failed", { error: message });
      set({ error: message });
    }
  },
}));
