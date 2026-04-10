import { create } from "zustand";
import { api } from "../services/api";
import type { AudioDesignFile, AudioQualityBrief } from "../types";
import { createLogger } from "../utils/logger";

const logger = createLogger("AudioDesignStore");

// Re-export types from centralized types file for backward compatibility
export type AudioClip = AudioDesignFile;
export type QualityBrief = AudioQualityBrief;

export interface AnalysisResult {
  file_id: string;
  duration_seconds: number;
  sample_rate: number;
  quality: QualityBrief;
  pitch_mean: number | null;
  pitch_std: number | null;
  energy_mean: number | null;
  energy_std: number | null;
  spectral_centroid_mean: number | null;
  rms_db: number | null;
}

export interface EffectConfig {
  type: "noise_reduction" | "normalize" | "trim_silence" | "gain";
  enabled: boolean;
  strength?: number;
  target_db?: number;
  threshold_db?: number;
  gain_db?: number;
}

interface AudioDesignState {
  clips: AudioClip[];
  selectedClipId: string | null;
  analysis: AnalysisResult | null;
  processingEngine: "local" | "elevenlabs";
  effects: EffectConfig[];
  exportFormat: string;
  exportSampleRate: number | null;
  loading: boolean;
  processing: boolean;
  error: string | null;

  fetchFiles: () => Promise<void>;
  uploadClip: (file: File) => Promise<AudioClip>;
  removeClip: (fileId: string) => Promise<void>;
  trimClip: (fileId: string, start: number, end: number) => Promise<AudioClip>;
  concatClips: (fileIds: string[], crossfadeMs?: number) => Promise<AudioClip>;
  applyEffects: (fileId: string) => Promise<AudioClip>;
  analyzeClip: (fileId: string) => Promise<AnalysisResult>;
  isolateClip: (fileId: string) => Promise<AudioClip>;
  exportClip: (fileId: string) => Promise<{ audio_url: string; filename: string }>;
  setSelectedClip: (id: string | null) => void;
  setProcessingEngine: (engine: "local" | "elevenlabs") => void;
  updateEffect: (index: number, update: Partial<EffectConfig>) => void;
  setExportFormat: (format: string) => void;
  setExportSampleRate: (rate: number | null) => void;
  clearError: () => void;
  resetEffects: () => void;
}

const DEFAULT_EFFECTS: EffectConfig[] = [
  { type: "noise_reduction", enabled: false, strength: 0.5 },
  { type: "normalize", enabled: false },
  { type: "trim_silence", enabled: false, threshold_db: -40 },
  { type: "gain", enabled: false, gain_db: 0 },
];

export const useAudioDesignStore = create<AudioDesignState>((set, get) => ({
  clips: [],
  selectedClipId: null,
  analysis: null,
  processingEngine: "local",
  effects: [...DEFAULT_EFFECTS],
  exportFormat: "wav",
  exportSampleRate: null,
  loading: false,
  processing: false,
  error: null,

  fetchFiles: async () => {
    set({ loading: true });
    try {
      const { files, total } = await api.audioDesignListFiles();
      set({ clips: files, loading: false, error: null });
      if (total > files.length) {
        logger.info("fetch_files_paginated", { loaded: files.length, total });
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to load files";
      logger.error("fetch_files_failed", { error: msg });
      set({ error: msg, loading: false });
    }
  },

  uploadClip: async (file: File) => {
    logger.info("upload_clip", { name: file.name, size: file.size });
    set({ loading: true });
    try {
      const { file: clip } = await api.audioDesignUpload(file);
      set((s) => ({ clips: [...s.clips, clip], loading: false, error: null, selectedClipId: clip.file_id }));
      return clip;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Upload failed";
      logger.error("upload_failed", { error: msg });
      set({ error: msg, loading: false });
      throw e;
    }
  },

  removeClip: async (fileId: string) => {
    logger.info("remove_clip", { fileId });
    try {
      await api.audioDesignDeleteFile(fileId);
      set((s) => ({
        clips: s.clips.filter((c) => c.file_id !== fileId),
        selectedClipId: s.selectedClipId === fileId ? null : s.selectedClipId,
        analysis: s.analysis?.file_id === fileId ? null : s.analysis,
      }));
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Delete failed";
      logger.error("remove_failed", { error: msg });
      set({ error: msg });
    }
  },

  trimClip: async (fileId, start, end) => {
    logger.info("trim_clip", { fileId, start, end });
    set({ processing: true });
    try {
      const { file: clip } = await api.audioDesignTrim(fileId, start, end);
      set((s) => ({ clips: [...s.clips, clip], processing: false, selectedClipId: clip.file_id, error: null }));
      return clip;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Trim failed";
      logger.error("trim_failed", { error: msg });
      set({ error: msg, processing: false });
      throw e;
    }
  },

  concatClips: async (fileIds, crossfadeMs = 0) => {
    logger.info("concat_clips", { fileIds, crossfadeMs });
    set({ processing: true });
    try {
      const { file: clip } = await api.audioDesignConcat(fileIds, crossfadeMs);
      set((s) => ({ clips: [...s.clips, clip], processing: false, selectedClipId: clip.file_id, error: null }));
      return clip;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Concat failed";
      logger.error("concat_failed", { error: msg });
      set({ error: msg, processing: false });
      throw e;
    }
  },

  applyEffects: async (fileId) => {
    const { effects } = get();
    const enabled = effects.filter((e) => e.enabled);
    if (enabled.length === 0) throw new Error("No effects enabled");

    // Normalize: strip undefined optional fields before sending to API
    const cleanEffects = enabled.map((e) => {
      const out: Record<string, unknown> = { type: e.type };
      if (e.type === "noise_reduction" && e.strength !== undefined) out.strength = e.strength;
      if (e.type === "trim_silence" && e.threshold_db !== undefined) out.threshold_db = e.threshold_db;
      if (e.type === "gain" && e.gain_db !== undefined) out.gain_db = e.gain_db;
      return out as { type: string; strength?: number; target_db?: number; threshold_db?: number; gain_db?: number };
    });

    logger.info("apply_effects", { fileId, effectCount: cleanEffects.length });
    set({ processing: true });
    try {
      const { file: clip } = await api.audioDesignEffects(fileId, cleanEffects);
      set((s) => ({ clips: [...s.clips, clip], processing: false, selectedClipId: clip.file_id, error: null }));
      return clip;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Effects failed";
      logger.error("effects_failed", { error: msg });
      set({ error: msg, processing: false });
      throw e;
    }
  },

  analyzeClip: async (fileId) => {
    logger.info("analyze_clip", { fileId });
    set({ processing: true });
    try {
      const result = await api.audioDesignAnalyze(fileId);
      set({ analysis: result, processing: false, error: null });
      return result;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Analysis failed";
      logger.error("analyze_failed", { error: msg });
      set({ error: msg, processing: false });
      throw e;
    }
  },

  isolateClip: async (fileId) => {
    logger.info("isolate_clip", { fileId });
    set({ processing: true });
    try {
      const { file: clip } = await api.audioDesignIsolate(fileId);
      set((s) => ({ clips: [...s.clips, clip], processing: false, selectedClipId: clip.file_id, error: null }));
      return clip;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Isolation failed";
      logger.error("isolate_failed", { error: msg });
      set({ error: msg, processing: false });
      throw e;
    }
  },

  exportClip: async (fileId) => {
    const { exportFormat, exportSampleRate } = get();
    logger.info("export_clip", { fileId, format: exportFormat, sampleRate: exportSampleRate });
    set({ processing: true });
    try {
      const result = await api.audioDesignExport(fileId, exportFormat, exportSampleRate);
      set({ processing: false, error: null });
      return result;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Export failed";
      logger.error("export_failed", { error: msg });
      set({ error: msg, processing: false });
      throw e;
    }
  },

  setSelectedClip: (id) => set({ selectedClipId: id, analysis: null, effects: DEFAULT_EFFECTS.map((e) => ({ ...e })) }),
  setProcessingEngine: (engine) => set({ processingEngine: engine }),
  updateEffect: (index, update) =>
    set((s) => {
      const effects = [...s.effects];
      effects[index] = { ...effects[index], ...update };
      return { effects };
    }),
  setExportFormat: (format) => set({ exportFormat: format }),
  setExportSampleRate: (rate) => set({ exportSampleRate: rate }),
  clearError: () => set({ error: null }),
  resetEffects: () => set({ effects: DEFAULT_EFFECTS.map((e) => ({ ...e })) }),
}));
