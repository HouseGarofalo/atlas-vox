import { describe, it, expect, beforeEach, vi } from "vitest";
import { useSynthesisStore } from "../../stores/synthesisStore";

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
    synthesize: vi.fn(),
    compare: vi.fn(),
    getSynthesisHistory: vi.fn(),
  },
}));

import { api } from "../../services/api";

const mockApi = vi.mocked(api);

describe("SynthesisStore", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useSynthesisStore.setState({
      lastResult: null,
      history: [],
      comparing: false,
      comparisonResults: [],
      loading: false,
      error: null,
    });
  });

  describe("synthesize", () => {
    it("synthesizes successfully", async () => {
      const result = {
        id: "s1",
        audio_url: "/audio/test.wav",
        duration_seconds: 1.5,
        latency_ms: 200,
        profile_id: "p1",
        provider_name: "kokoro",
      };
      mockApi.synthesize.mockResolvedValue(result);

      const res = await useSynthesisStore.getState().synthesize({
        text: "Hello world",
        profile_id: "p1",
      });

      expect(res).toEqual(result);
      const state = useSynthesisStore.getState();
      expect(state.lastResult).toEqual(result);
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
    });

    it("sets loading state during synthesis", async () => {
      let resolvePromise: (value: any) => void;
      mockApi.synthesize.mockReturnValue(
        new Promise((resolve) => {
          resolvePromise = resolve;
        })
      );

      const synthPromise = useSynthesisStore.getState().synthesize({
        text: "Hello",
        profile_id: "p1",
      });
      expect(useSynthesisStore.getState().loading).toBe(true);

      resolvePromise!({
        id: "s1",
        audio_url: "/audio/test.wav",
        duration_seconds: 1.0,
        latency_ms: 100,
        profile_id: "p1",
        provider_name: "kokoro",
      });
      await synthPromise;
      expect(useSynthesisStore.getState().loading).toBe(false);
    });

    it("handles synthesis errors", async () => {
      mockApi.synthesize.mockRejectedValue(new Error("Provider offline"));

      await expect(
        useSynthesisStore.getState().synthesize({
          text: "Hello",
          profile_id: "p1",
        })
      ).rejects.toThrow("Provider offline");

      const state = useSynthesisStore.getState();
      expect(state.error).toBe("Provider offline");
      expect(state.loading).toBe(false);
    });
  });

  describe("fetchHistory", () => {
    it("fetches history successfully", async () => {
      const history = [
        { id: "h1", text: "Hello", audio_url: "/audio/h1.wav", profile_id: "p1", provider_name: "kokoro", created_at: "2026-01-01T00:00:00Z" },
        { id: "h2", text: "World", audio_url: "/audio/h2.wav", profile_id: "p1", provider_name: "kokoro", created_at: "2026-01-01T00:00:01Z" },
      ];
      mockApi.getSynthesisHistory.mockResolvedValue(history);

      await useSynthesisStore.getState().fetchHistory();

      expect(useSynthesisStore.getState().history).toEqual(history);
      expect(mockApi.getSynthesisHistory).toHaveBeenCalledWith(50);
    });

    it("accepts custom limit", async () => {
      mockApi.getSynthesisHistory.mockResolvedValue([]);

      await useSynthesisStore.getState().fetchHistory(10);

      expect(mockApi.getSynthesisHistory).toHaveBeenCalledWith(10);
    });

    it("handles history fetch errors", async () => {
      mockApi.getSynthesisHistory.mockRejectedValue(new Error("Timeout"));

      await useSynthesisStore.getState().fetchHistory();

      expect(useSynthesisStore.getState().error).toBe("Timeout");
    });
  });
});
