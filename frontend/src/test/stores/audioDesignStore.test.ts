import { describe, it, expect, beforeEach, vi } from "vitest";
import { useAudioDesignStore } from "../../stores/audioDesignStore";

vi.mock("../../utils/logger", () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock("../../services/api", () => ({
  api: {
    audioDesignListFiles: vi.fn(),
    audioDesignUpload: vi.fn(),
    audioDesignDeleteFile: vi.fn(),
    audioDesignTrim: vi.fn(),
    audioDesignConcat: vi.fn(),
    audioDesignEffects: vi.fn(),
    audioDesignAnalyze: vi.fn(),
    audioDesignIsolate: vi.fn(),
    audioDesignExport: vi.fn(),
  },
}));

import { api } from "../../services/api";

const mockApi = vi.mocked(api);

// ---------------------------------------------------------------------------
// Fixtures
//
// The api service uses internal AudioDesignFile / AudioDesignQuality types.
// At the mock boundary we cast with `as any` so our plain test fixtures do not
// need to satisfy those private type constraints.  The store then exposes the
// same shape via its own exported AudioClip / AnalysisResult interfaces, which
// our assertions use directly.
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const makeClip = (overrides: Record<string, any> = {}): any => ({
  file_id: "clip-1",
  filename: "test.wav",
  original_filename: "test.wav",
  duration_seconds: 3.5,
  sample_rate: 44100,
  channels: 1,
  format: "wav",
  file_size_bytes: 154000,
  audio_url: "/audio/test.wav",
  ...overrides,
});

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const makeAnalysis = (overrides: Record<string, any> = {}): any => ({
  file_id: "clip-1",
  duration_seconds: 3.5,
  sample_rate: 44100,
  quality: {
    passed: true,
    score: 0.92,
    snr_db: 38,
    rms_db: -18,
    issues: [],
  },
  pitch_mean: 120,
  pitch_std: 5,
  energy_mean: 0.04,
  energy_std: 0.01,
  spectral_centroid_mean: 2200,
  rms_db: -18,
  ...overrides,
});

const DEFAULT_EFFECTS = [
  { type: "noise_reduction", enabled: false, strength: 0.5 },
  { type: "normalize", enabled: false },
  { type: "trim_silence", enabled: false, threshold_db: -40 },
  { type: "gain", enabled: false, gain_db: 0 },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function resetStore() {
  useAudioDesignStore.setState({
    clips: [],
    selectedClipId: null,
    analysis: null,
    processingEngine: "local",
    effects: DEFAULT_EFFECTS.map((e) => ({ ...e })) as any,
    exportFormat: "wav",
    exportSampleRate: null,
    loading: false,
    processing: false,
    error: null,
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AudioDesignStore", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.clearAllMocks();
    resetStore();
  });

  // -------------------------------------------------------------------------
  describe("fetchFiles", () => {
    it("loads clips from the API and clears loading/error on success", async () => {
      const clips = [makeClip({ file_id: "a" }), makeClip({ file_id: "b" })];
      mockApi.audioDesignListFiles.mockResolvedValue({ files: clips as any, count: 2, total: 2 });

      await useAudioDesignStore.getState().fetchFiles();

      const state = useAudioDesignStore.getState();
      expect(state.clips).toEqual(clips);
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
    });

    it("sets loading true while the request is in flight", async () => {
      let resolve!: (v: any) => void;
      mockApi.audioDesignListFiles.mockReturnValue(new Promise((r) => { resolve = r; }));

      const pending = useAudioDesignStore.getState().fetchFiles();
      expect(useAudioDesignStore.getState().loading).toBe(true);

      resolve({ files: [], count: 0, total: 0 });
      await pending;
      expect(useAudioDesignStore.getState().loading).toBe(false);
    });

    it("sets error and clears loading on failure", async () => {
      mockApi.audioDesignListFiles.mockRejectedValue(new Error("Network error"));

      await useAudioDesignStore.getState().fetchFiles();

      const state = useAudioDesignStore.getState();
      expect(state.error).toBe("Network error");
      expect(state.loading).toBe(false);
      expect(state.clips).toEqual([]);
    });

    it("uses a fallback message when the thrown value is not an Error", async () => {
      mockApi.audioDesignListFiles.mockRejectedValue("oops");

      await useAudioDesignStore.getState().fetchFiles();

      expect(useAudioDesignStore.getState().error).toBe("Failed to load files");
    });
  });

  // -------------------------------------------------------------------------
  describe("uploadClip", () => {
    it("uploads a file, appends the clip, selects it, and returns it", async () => {
      const clip = makeClip({ file_id: "new-1" });
      mockApi.audioDesignUpload.mockResolvedValue({ file: clip as any, quality: null });

      const file = new File(["audio"], "voice.wav", { type: "audio/wav" });
      const result = await useAudioDesignStore.getState().uploadClip(file);

      expect(result).toEqual(clip);
      const state = useAudioDesignStore.getState();
      expect(state.clips).toContainEqual(clip);
      expect(state.selectedClipId).toBe("new-1");
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
    });

    it("appends to existing clips without replacing them", async () => {
      const existing = makeClip({ file_id: "old-1" });
      useAudioDesignStore.setState({ clips: [existing] });

      const newClip = makeClip({ file_id: "new-2" });
      mockApi.audioDesignUpload.mockResolvedValue({ file: newClip, quality: null });

      await useAudioDesignStore.getState().uploadClip(new File(["x"], "x.wav"));

      expect(useAudioDesignStore.getState().clips).toHaveLength(2);
      expect(useAudioDesignStore.getState().clips[0]).toEqual(existing);
    });

    it("sets error and re-throws on failure", async () => {
      mockApi.audioDesignUpload.mockRejectedValue(new Error("Upload failed"));

      await expect(
        useAudioDesignStore.getState().uploadClip(new File(["x"], "x.wav")),
      ).rejects.toThrow("Upload failed");

      const state = useAudioDesignStore.getState();
      expect(state.error).toBe("Upload failed");
      expect(state.loading).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  describe("removeClip", () => {
    it("removes the clip from the list on success", async () => {
      const a = makeClip({ file_id: "a" });
      const b = makeClip({ file_id: "b" });
      useAudioDesignStore.setState({ clips: [a, b] });
      mockApi.audioDesignDeleteFile.mockResolvedValue(undefined);

      await useAudioDesignStore.getState().removeClip("a");

      const state = useAudioDesignStore.getState();
      expect(state.clips).toEqual([b]);
    });

    it("clears selectedClipId when the selected clip is removed", async () => {
      const clip = makeClip({ file_id: "sel" });
      useAudioDesignStore.setState({ clips: [clip], selectedClipId: "sel" });
      mockApi.audioDesignDeleteFile.mockResolvedValue(undefined);

      await useAudioDesignStore.getState().removeClip("sel");

      expect(useAudioDesignStore.getState().selectedClipId).toBeNull();
    });

    it("preserves selectedClipId when a different clip is removed", async () => {
      const a = makeClip({ file_id: "a" });
      const b = makeClip({ file_id: "b" });
      useAudioDesignStore.setState({ clips: [a, b], selectedClipId: "b" });
      mockApi.audioDesignDeleteFile.mockResolvedValue(undefined);

      await useAudioDesignStore.getState().removeClip("a");

      expect(useAudioDesignStore.getState().selectedClipId).toBe("b");
    });

    it("clears the analysis when the analysed clip is removed", async () => {
      const clip = makeClip({ file_id: "c" });
      const analysis = makeAnalysis({ file_id: "c" });
      useAudioDesignStore.setState({ clips: [clip], analysis });
      mockApi.audioDesignDeleteFile.mockResolvedValue(undefined);

      await useAudioDesignStore.getState().removeClip("c");

      expect(useAudioDesignStore.getState().analysis).toBeNull();
    });

    it("preserves the analysis when a different clip is removed", async () => {
      const a = makeClip({ file_id: "a" });
      const b = makeClip({ file_id: "b" });
      const analysis = makeAnalysis({ file_id: "b" });
      useAudioDesignStore.setState({ clips: [a, b], analysis });
      mockApi.audioDesignDeleteFile.mockResolvedValue(undefined);

      await useAudioDesignStore.getState().removeClip("a");

      expect(useAudioDesignStore.getState().analysis).toEqual(analysis);
    });

    it("sets error on failure", async () => {
      useAudioDesignStore.setState({ clips: [makeClip()] });
      mockApi.audioDesignDeleteFile.mockRejectedValue(new Error("Delete failed"));

      await useAudioDesignStore.getState().removeClip("clip-1");

      expect(useAudioDesignStore.getState().error).toBe("Delete failed");
    });
  });

  // -------------------------------------------------------------------------
  describe("trimClip", () => {
    it("appends the trimmed clip, selects it, and returns it", async () => {
      const trimmed = makeClip({ file_id: "trimmed-1" });
      mockApi.audioDesignTrim.mockResolvedValue({ file: trimmed });

      const result = await useAudioDesignStore.getState().trimClip("clip-1", 0.5, 2.0);

      expect(result).toEqual(trimmed);
      const state = useAudioDesignStore.getState();
      expect(state.clips).toContainEqual(trimmed);
      expect(state.selectedClipId).toBe("trimmed-1");
      expect(state.processing).toBe(false);
      expect(state.error).toBeNull();
      expect(mockApi.audioDesignTrim).toHaveBeenCalledWith("clip-1", 0.5, 2.0);
    });

    it("sets processing true while in-flight", async () => {
      let resolve!: (v: any) => void;
      mockApi.audioDesignTrim.mockReturnValue(new Promise((r) => { resolve = r; }));

      const pending = useAudioDesignStore.getState().trimClip("clip-1", 0, 1);
      expect(useAudioDesignStore.getState().processing).toBe(true);

      resolve({ file: makeClip() });
      await pending;
      expect(useAudioDesignStore.getState().processing).toBe(false);
    });

    it("sets error and re-throws on failure", async () => {
      mockApi.audioDesignTrim.mockRejectedValue(new Error("Trim failed"));

      await expect(
        useAudioDesignStore.getState().trimClip("clip-1", 0, 1),
      ).rejects.toThrow("Trim failed");

      const state = useAudioDesignStore.getState();
      expect(state.error).toBe("Trim failed");
      expect(state.processing).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  describe("concatClips", () => {
    it("concatenates clips, appends the result, selects it, and returns it", async () => {
      const concat = makeClip({ file_id: "concat-1" });
      mockApi.audioDesignConcat.mockResolvedValue({ file: concat });

      const result = await useAudioDesignStore.getState().concatClips(["a", "b"], 100);

      expect(result).toEqual(concat);
      const state = useAudioDesignStore.getState();
      expect(state.clips).toContainEqual(concat);
      expect(state.selectedClipId).toBe("concat-1");
      expect(state.processing).toBe(false);
      expect(mockApi.audioDesignConcat).toHaveBeenCalledWith(["a", "b"], 100);
    });

    it("defaults crossfadeMs to 0 when not supplied", async () => {
      mockApi.audioDesignConcat.mockResolvedValue({ file: makeClip() });

      await useAudioDesignStore.getState().concatClips(["a", "b"]);

      expect(mockApi.audioDesignConcat).toHaveBeenCalledWith(["a", "b"], 0);
    });

    it("sets error and re-throws on failure", async () => {
      mockApi.audioDesignConcat.mockRejectedValue(new Error("Concat failed"));

      await expect(
        useAudioDesignStore.getState().concatClips(["a", "b"]),
      ).rejects.toThrow("Concat failed");

      expect(useAudioDesignStore.getState().error).toBe("Concat failed");
      expect(useAudioDesignStore.getState().processing).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  describe("applyEffects", () => {
    it("sends only enabled effects and returns the processed clip", async () => {
      // Enable noise_reduction and gain; leave normalize and trim_silence off
      useAudioDesignStore.setState({
        effects: [
          { type: "noise_reduction", enabled: true, strength: 0.7 },
          { type: "normalize", enabled: false },
          { type: "trim_silence", enabled: false, threshold_db: -40 },
          { type: "gain", enabled: true, gain_db: 3 },
        ],
      });

      const processed = makeClip({ file_id: "processed-1" });
      mockApi.audioDesignEffects.mockResolvedValue({ file: processed });

      const result = await useAudioDesignStore.getState().applyEffects("clip-1");

      expect(result).toEqual(processed);

      // Only enabled effects should have been forwarded
      const [, cleanEffects] = mockApi.audioDesignEffects.mock.calls[0];
      expect(cleanEffects).toHaveLength(2);
      expect(cleanEffects[0]).toMatchObject({ type: "noise_reduction", strength: 0.7 });
      expect(cleanEffects[1]).toMatchObject({ type: "gain", gain_db: 3 });

      // normalize (no extra keys) should NOT carry undefined optional fields
      expect(cleanEffects[0]).not.toHaveProperty("target_db");
      expect(cleanEffects[0]).not.toHaveProperty("threshold_db");
      expect(cleanEffects[0]).not.toHaveProperty("gain_db");
    });

    it("strips undefined optional params from noise_reduction", async () => {
      useAudioDesignStore.setState({
        effects: [
          { type: "noise_reduction", enabled: true },
          { type: "normalize", enabled: false },
          { type: "trim_silence", enabled: false },
          { type: "gain", enabled: false },
        ],
      });
      mockApi.audioDesignEffects.mockResolvedValue({ file: makeClip() });

      await useAudioDesignStore.getState().applyEffects("clip-1");

      const [, cleanEffects] = mockApi.audioDesignEffects.mock.calls[0];
      expect(cleanEffects[0]).not.toHaveProperty("strength");
    });

    it("strips undefined optional params from trim_silence", async () => {
      useAudioDesignStore.setState({
        effects: [
          { type: "noise_reduction", enabled: false },
          { type: "normalize", enabled: false },
          { type: "trim_silence", enabled: true },
          { type: "gain", enabled: false },
        ],
      });
      mockApi.audioDesignEffects.mockResolvedValue({ file: makeClip() });

      await useAudioDesignStore.getState().applyEffects("clip-1");

      const [, cleanEffects] = mockApi.audioDesignEffects.mock.calls[0];
      // threshold_db was undefined on the effect, so it should not appear
      expect(cleanEffects[0]).not.toHaveProperty("threshold_db");
    });

    it("throws synchronously when no effects are enabled", async () => {
      // Default state has all effects disabled
      await expect(
        useAudioDesignStore.getState().applyEffects("clip-1"),
      ).rejects.toThrow("No effects enabled");

      expect(mockApi.audioDesignEffects).not.toHaveBeenCalled();
    });

    it("sets error and re-throws on API failure", async () => {
      useAudioDesignStore.setState({
        effects: [
          { type: "normalize", enabled: true },
          { type: "noise_reduction", enabled: false },
          { type: "trim_silence", enabled: false },
          { type: "gain", enabled: false },
        ],
      });
      mockApi.audioDesignEffects.mockRejectedValue(new Error("Effects failed"));

      await expect(
        useAudioDesignStore.getState().applyEffects("clip-1"),
      ).rejects.toThrow("Effects failed");

      expect(useAudioDesignStore.getState().error).toBe("Effects failed");
      expect(useAudioDesignStore.getState().processing).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  describe("analyzeClip", () => {
    it("stores the analysis result and returns it", async () => {
      const analysis = makeAnalysis();
      mockApi.audioDesignAnalyze.mockResolvedValue(analysis);

      const result = await useAudioDesignStore.getState().analyzeClip("clip-1");

      expect(result).toEqual(analysis);
      const state = useAudioDesignStore.getState();
      expect(state.analysis).toEqual(analysis);
      expect(state.processing).toBe(false);
      expect(state.error).toBeNull();
      expect(mockApi.audioDesignAnalyze).toHaveBeenCalledWith("clip-1");
    });

    it("sets processing true while in-flight", async () => {
      let resolve!: (v: any) => void;
      mockApi.audioDesignAnalyze.mockReturnValue(new Promise((r) => { resolve = r; }));

      const pending = useAudioDesignStore.getState().analyzeClip("clip-1");
      expect(useAudioDesignStore.getState().processing).toBe(true);

      resolve(makeAnalysis());
      await pending;
      expect(useAudioDesignStore.getState().processing).toBe(false);
    });

    it("sets error and re-throws on failure", async () => {
      mockApi.audioDesignAnalyze.mockRejectedValue(new Error("Analysis failed"));

      await expect(
        useAudioDesignStore.getState().analyzeClip("clip-1"),
      ).rejects.toThrow("Analysis failed");

      expect(useAudioDesignStore.getState().error).toBe("Analysis failed");
      expect(useAudioDesignStore.getState().processing).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  describe("isolateClip", () => {
    it("appends the isolated clip, selects it, and returns it", async () => {
      const isolated = makeClip({ file_id: "isolated-1" });
      mockApi.audioDesignIsolate.mockResolvedValue({ file: isolated });

      const result = await useAudioDesignStore.getState().isolateClip("clip-1");

      expect(result).toEqual(isolated);
      const state = useAudioDesignStore.getState();
      expect(state.clips).toContainEqual(isolated);
      expect(state.selectedClipId).toBe("isolated-1");
      expect(state.processing).toBe(false);
      expect(state.error).toBeNull();
      expect(mockApi.audioDesignIsolate).toHaveBeenCalledWith("clip-1");
    });

    it("sets processing true while in-flight", async () => {
      let resolve!: (v: any) => void;
      mockApi.audioDesignIsolate.mockReturnValue(new Promise((r) => { resolve = r; }));

      const pending = useAudioDesignStore.getState().isolateClip("clip-1");
      expect(useAudioDesignStore.getState().processing).toBe(true);

      resolve({ file: makeClip() });
      await pending;
      expect(useAudioDesignStore.getState().processing).toBe(false);
    });

    it("sets error and re-throws on failure", async () => {
      mockApi.audioDesignIsolate.mockRejectedValue(new Error("Isolation failed"));

      await expect(
        useAudioDesignStore.getState().isolateClip("clip-1"),
      ).rejects.toThrow("Isolation failed");

      expect(useAudioDesignStore.getState().error).toBe("Isolation failed");
      expect(useAudioDesignStore.getState().processing).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  describe("exportClip", () => {
    it("exports using current format/sample-rate and returns the result", async () => {
      useAudioDesignStore.setState({ exportFormat: "mp3", exportSampleRate: 22050 });
      const exportResult = {
        file_id: "clip-1",
        filename: "out.mp3",
        audio_url: "/exports/out.mp3",
        format: "mp3",
        sample_rate: 22050,
        duration_seconds: 3.5,
        file_size_bytes: 88200,
      };
      mockApi.audioDesignExport.mockResolvedValue(exportResult);

      const result = await useAudioDesignStore.getState().exportClip("clip-1");

      expect(result).toEqual(exportResult);
      const state = useAudioDesignStore.getState();
      expect(state.processing).toBe(false);
      expect(state.error).toBeNull();
      expect(mockApi.audioDesignExport).toHaveBeenCalledWith("clip-1", "mp3", 22050);
    });

    it("passes null sample rate when exportSampleRate is not set", async () => {
      mockApi.audioDesignExport.mockResolvedValue({
        file_id: "clip-1",
        filename: "e.wav",
        audio_url: "/e.wav",
        format: "wav",
        sample_rate: 44100,
        duration_seconds: 3.5,
        file_size_bytes: 308000,
      });

      await useAudioDesignStore.getState().exportClip("clip-1");

      expect(mockApi.audioDesignExport).toHaveBeenCalledWith("clip-1", "wav", null);
    });

    it("sets processing true while in-flight", async () => {
      let resolve!: (v: any) => void;
      mockApi.audioDesignExport.mockReturnValue(new Promise((r) => { resolve = r; }));

      const pending = useAudioDesignStore.getState().exportClip("clip-1");
      expect(useAudioDesignStore.getState().processing).toBe(true);

      resolve({
        file_id: "clip-1",
        filename: "e.wav",
        audio_url: "/e.wav",
        format: "wav",
        sample_rate: 44100,
        duration_seconds: 3.5,
        file_size_bytes: 308000,
      });
      await pending;
      expect(useAudioDesignStore.getState().processing).toBe(false);
    });

    it("sets error and re-throws on failure", async () => {
      mockApi.audioDesignExport.mockRejectedValue(new Error("Export failed"));

      await expect(
        useAudioDesignStore.getState().exportClip("clip-1"),
      ).rejects.toThrow("Export failed");

      expect(useAudioDesignStore.getState().error).toBe("Export failed");
      expect(useAudioDesignStore.getState().processing).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  describe("setSelectedClip", () => {
    it("sets the selected clip ID", () => {
      useAudioDesignStore.getState().setSelectedClip("clip-1");
      expect(useAudioDesignStore.getState().selectedClipId).toBe("clip-1");
    });

    it("accepts null to deselect", () => {
      useAudioDesignStore.setState({ selectedClipId: "clip-1" });
      useAudioDesignStore.getState().setSelectedClip(null);
      expect(useAudioDesignStore.getState().selectedClipId).toBeNull();
    });

    it("resets effects to defaults", () => {
      useAudioDesignStore.setState({
        effects: [
          { type: "noise_reduction", enabled: true, strength: 0.9 },
          { type: "normalize", enabled: true },
          { type: "trim_silence", enabled: true, threshold_db: -20 },
          { type: "gain", enabled: true, gain_db: 6 },
        ],
      });

      useAudioDesignStore.getState().setSelectedClip("clip-2");

      const { effects } = useAudioDesignStore.getState();
      expect(effects.every((e) => e.enabled === false)).toBe(true);
      expect(effects[0]).toMatchObject({ type: "noise_reduction", strength: 0.5 });
      expect(effects[2]).toMatchObject({ type: "trim_silence", threshold_db: -40 });
      expect(effects[3]).toMatchObject({ type: "gain", gain_db: 0 });
    });

    it("clears any existing analysis", () => {
      useAudioDesignStore.setState({ analysis: makeAnalysis() });
      useAudioDesignStore.getState().setSelectedClip("clip-2");
      expect(useAudioDesignStore.getState().analysis).toBeNull();
    });
  });

  // -------------------------------------------------------------------------
  describe("updateEffect", () => {
    it("updates a specific effect by index", () => {
      useAudioDesignStore.getState().updateEffect(0, { enabled: true, strength: 0.8 });

      const { effects } = useAudioDesignStore.getState();
      expect(effects[0]).toMatchObject({ type: "noise_reduction", enabled: true, strength: 0.8 });
    });

    it("does not mutate other effects", () => {
      useAudioDesignStore.getState().updateEffect(2, { enabled: true });

      const { effects } = useAudioDesignStore.getState();
      expect(effects[0].enabled).toBe(false);
      expect(effects[1].enabled).toBe(false);
      expect(effects[3].enabled).toBe(false);
      expect(effects[2].enabled).toBe(true);
    });

    it("merges partial updates without dropping existing fields", () => {
      // Pre-set a known state so we can verify merge behaviour
      useAudioDesignStore.setState({
        effects: [
          { type: "noise_reduction", enabled: false, strength: 0.5 },
          { type: "normalize", enabled: false },
          { type: "trim_silence", enabled: false, threshold_db: -40 },
          { type: "gain", enabled: false, gain_db: 0 },
        ],
      });

      useAudioDesignStore.getState().updateEffect(0, { enabled: true });

      const { effects } = useAudioDesignStore.getState();
      // strength should still be present after partial update
      expect(effects[0]).toMatchObject({ type: "noise_reduction", enabled: true, strength: 0.5 });
    });
  });

  // -------------------------------------------------------------------------
  describe("clearError", () => {
    it("sets error to null", () => {
      useAudioDesignStore.setState({ error: "Something went wrong" });
      useAudioDesignStore.getState().clearError();
      expect(useAudioDesignStore.getState().error).toBeNull();
    });

    it("is a no-op when error is already null", () => {
      useAudioDesignStore.getState().clearError();
      expect(useAudioDesignStore.getState().error).toBeNull();
    });
  });
});
