import { describe, it, expect, beforeEach, vi } from "vitest";
import { useProfileStore } from "../../stores/profileStore";

// Mock the logger
vi.mock("../../utils/logger", () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

// Mock the API client
vi.mock("../../services/api", () => ({
  api: {
    listProfiles: vi.fn(),
    createProfile: vi.fn(),
    updateProfile: vi.fn(),
    deleteProfile: vi.fn(),
    activateVersion: vi.fn(),
  },
}));

import { api } from "../../services/api";

const mockApi = vi.mocked(api);

describe("ProfileStore", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    // Reset store state
    useProfileStore.setState({
      profiles: [],
      loading: false,
      error: null,
    });
  });

  describe("fetchProfiles", () => {
    it("fetches profiles successfully", async () => {
      const profiles = [
        { id: "1", name: "Voice A", provider_name: "kokoro" },
        { id: "2", name: "Voice B", provider_name: "piper" },
      ];
      mockApi.listProfiles.mockResolvedValue({ profiles, count: 2 } as any);

      await useProfileStore.getState().fetchProfiles();

      const state = useProfileStore.getState();
      expect(state.profiles).toEqual(profiles);
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
    });

    it("sets loading state during fetch", async () => {
      let resolvePromise: (value: any) => void;
      mockApi.listProfiles.mockReturnValue(
        new Promise((resolve) => {
          resolvePromise = resolve;
        })
      );

      const fetchPromise = useProfileStore.getState().fetchProfiles();
      expect(useProfileStore.getState().loading).toBe(true);

      resolvePromise!({ profiles: [], count: 0 });
      await fetchPromise;
      expect(useProfileStore.getState().loading).toBe(false);
    });

    it("handles errors", async () => {
      mockApi.listProfiles.mockRejectedValue(new Error("Network error"));

      await useProfileStore.getState().fetchProfiles();

      const state = useProfileStore.getState();
      expect(state.error).toBe("Network error");
      expect(state.loading).toBe(false);
      expect(state.profiles).toEqual([]);
    });
  });

  describe("createProfile", () => {
    it("creates a profile and adds to list", async () => {
      const newProfile = { id: "3", name: "Voice C", provider_name: "kokoro" };
      mockApi.createProfile.mockResolvedValue(newProfile as any);

      const result = await useProfileStore.getState().createProfile({
        name: "Voice C",
        provider_name: "kokoro",
      });

      expect(result).toEqual(newProfile);
      expect(useProfileStore.getState().profiles).toContainEqual(newProfile);
    });

    it("prepends new profile to the list", async () => {
      useProfileStore.setState({
        profiles: [{ id: "1", name: "Existing" } as any],
      });
      const newProfile = { id: "2", name: "New" };
      mockApi.createProfile.mockResolvedValue(newProfile as any);

      await useProfileStore.getState().createProfile({
        name: "New",
        provider_name: "kokoro",
      });

      const profiles = useProfileStore.getState().profiles;
      expect(profiles[0]).toEqual(newProfile);
      expect(profiles).toHaveLength(2);
    });

    it("propagates errors", async () => {
      mockApi.createProfile.mockRejectedValue(new Error("Validation error"));

      await expect(
        useProfileStore.getState().createProfile({
          name: "",
          provider_name: "kokoro",
        })
      ).rejects.toThrow("Validation error");
    });
  });

  describe("deleteProfile", () => {
    it("removes profile from list", async () => {
      useProfileStore.setState({
        profiles: [
          { id: "1", name: "A" } as any,
          { id: "2", name: "B" } as any,
        ],
      });
      mockApi.deleteProfile.mockResolvedValue(undefined);

      await useProfileStore.getState().deleteProfile("1");

      const profiles = useProfileStore.getState().profiles;
      expect(profiles).toHaveLength(1);
      expect(profiles[0].id).toBe("2");
    });

    it("propagates delete errors", async () => {
      mockApi.deleteProfile.mockRejectedValue(new Error("Not found"));

      await expect(
        useProfileStore.getState().deleteProfile("nonexistent")
      ).rejects.toThrow("Not found");
    });
  });
});
