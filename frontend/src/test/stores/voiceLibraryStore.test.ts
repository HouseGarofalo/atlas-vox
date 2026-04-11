import { describe, it, expect, beforeEach, vi } from "vitest";
import { useVoiceLibraryStore } from "../../stores/voiceLibraryStore";

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
    listAllVoices: vi.fn(),
  },
}));

import { api } from "../../services/api";

const mockApi = vi.mocked(api);

const mockVoices = [
  { voice_id: "v1", name: "Alice", language: "en", provider: "kokoro", provider_display: "Kokoro", gender: "Female" },
  { voice_id: "v2", name: "Bob", language: "en", provider: "kokoro", provider_display: "Kokoro", gender: "Male" },
  { voice_id: "v3", name: "Marie", language: "fr", provider: "piper", provider_display: "Piper", gender: "Female" },
  { voice_id: "v4", name: "Hans", language: "de", provider: "coqui_xtts", provider_display: "Coqui XTTS", gender: "Male" },
];

describe("VoiceLibraryStore", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useVoiceLibraryStore.setState({
      voices: [],
      loading: false,
      error: null,
      filters: {
        provider: null,
        language: null,
        gender: null,
        search: "",
      },
    });
  });

  describe("fetchAllVoices", () => {
    it("fetches voices successfully", async () => {
      mockApi.listAllVoices.mockResolvedValue({ voices: mockVoices, count: 4 } as any);

      await useVoiceLibraryStore.getState().fetchAllVoices();

      const state = useVoiceLibraryStore.getState();
      expect(state.voices).toEqual(mockVoices);
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
    });

    it("handles fetch errors", async () => {
      mockApi.listAllVoices.mockRejectedValue(new Error("Network error"));

      await useVoiceLibraryStore.getState().fetchAllVoices();

      const state = useVoiceLibraryStore.getState();
      expect(state.error).toBe("Network error");
      expect(state.loading).toBe(false);
    });

    it("sets loading state during fetch", async () => {
      let resolvePromise: (value: any) => void;
      mockApi.listAllVoices.mockReturnValue(
        new Promise((resolve) => {
          resolvePromise = resolve;
        })
      );

      const fetchPromise = useVoiceLibraryStore.getState().fetchAllVoices();
      expect(useVoiceLibraryStore.getState().loading).toBe(true);

      resolvePromise!({ voices: [], count: 0 });
      await fetchPromise;
      expect(useVoiceLibraryStore.getState().loading).toBe(false);
    });
  });

  describe("setFilter", () => {
    it("sets provider filter", () => {
      useVoiceLibraryStore.getState().setFilter("provider", "kokoro");
      expect(useVoiceLibraryStore.getState().filters.provider).toBe("kokoro");
    });

    it("sets language filter", () => {
      useVoiceLibraryStore.getState().setFilter("language", "fr");
      expect(useVoiceLibraryStore.getState().filters.language).toBe("fr");
    });

    it("sets gender filter", () => {
      useVoiceLibraryStore.getState().setFilter("gender", "Female");
      expect(useVoiceLibraryStore.getState().filters.gender).toBe("Female");
    });

    it("sets search filter", () => {
      useVoiceLibraryStore.getState().setFilter("search", "alice");
      expect(useVoiceLibraryStore.getState().filters.search).toBe("alice");
    });

    it("clears filter with null", () => {
      useVoiceLibraryStore.getState().setFilter("provider", "kokoro");
      useVoiceLibraryStore.getState().setFilter("provider", null);
      expect(useVoiceLibraryStore.getState().filters.provider).toBeNull();
    });
  });

  describe("filteredVoices", () => {
    beforeEach(() => {
      // Must set both voices and _filteredVoices since filteredVoices() reads cached result
      useVoiceLibraryStore.setState({ voices: mockVoices, _filteredVoices: mockVoices });
    });

    it("returns all voices with no filters", () => {
      const result = useVoiceLibraryStore.getState().filteredVoices();
      expect(result).toHaveLength(4);
    });

    it("filters by provider", () => {
      useVoiceLibraryStore.getState().setFilter("provider", "kokoro");
      const result = useVoiceLibraryStore.getState().filteredVoices();
      expect(result).toHaveLength(2);
      expect(result.every((v) => v.provider === "kokoro")).toBe(true);
    });

    it("filters by language", () => {
      useVoiceLibraryStore.getState().setFilter("language", "fr");
      const result = useVoiceLibraryStore.getState().filteredVoices();
      expect(result).toHaveLength(1);
      expect(result[0].name).toBe("Marie");
    });

    it("filters by gender", () => {
      useVoiceLibraryStore.getState().setFilter("gender", "Female");
      const result = useVoiceLibraryStore.getState().filteredVoices();
      expect(result).toHaveLength(2);
      expect(result.every((v) => v.gender === "Female")).toBe(true);
    });

    it("filters by search text", () => {
      useVoiceLibraryStore.getState().setFilter("search", "alice");
      const result = useVoiceLibraryStore.getState().filteredVoices();
      expect(result).toHaveLength(1);
      expect(result[0].name).toBe("Alice");
    });

    it("combines multiple filters", () => {
      useVoiceLibraryStore.getState().setFilter("provider", "kokoro");
      useVoiceLibraryStore.getState().setFilter("gender", "Male");
      const result = useVoiceLibraryStore.getState().filteredVoices();
      expect(result).toHaveLength(1);
      expect(result[0].name).toBe("Bob");
    });

    it("search is case-insensitive", () => {
      useVoiceLibraryStore.getState().setFilter("search", "HANS");
      const result = useVoiceLibraryStore.getState().filteredVoices();
      expect(result).toHaveLength(1);
      expect(result[0].name).toBe("Hans");
    });

    it("search matches provider_display", () => {
      useVoiceLibraryStore.getState().setFilter("search", "Coqui");
      const result = useVoiceLibraryStore.getState().filteredVoices();
      expect(result).toHaveLength(1);
      expect(result[0].provider_display).toBe("Coqui XTTS");
    });
  });
});
