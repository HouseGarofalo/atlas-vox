import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock the logger to avoid noise in tests
vi.mock("../../utils/logger", () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

// Mock the auth store before importing the api module
vi.mock("../../stores/authStore", () => {
  const mockAuthStore = {
    token: 'mock-token',
    apiKey: null,
    user: { sub: 'test-user', scopes: ['admin'] },
    isAuthenticated: true,
    setToken: vi.fn(),
    setApiKey: vi.fn(),
    logout: vi.fn(),
    hasScope: vi.fn().mockReturnValue(true),
  };

  const mockUseAuthStore = vi.fn().mockReturnValue(mockAuthStore);
  mockUseAuthStore.getState = vi.fn().mockReturnValue(mockAuthStore);

  return {
    useAuthStore: mockUseAuthStore,
  };
});

const createMockResponse = (body: unknown, status = 200, ok = true): Response => {
  return {
    ok,
    status,
    statusText: status === 404 ? "Not Found" : "OK",
    json: vi.fn().mockResolvedValue(body),
    headers: new Headers(),
    redirected: false,
    type: "basic" as ResponseType,
    url: "",
    clone: vi.fn(),
    body: null,
    bodyUsed: false,
    arrayBuffer: vi.fn(),
    blob: vi.fn(),
    formData: vi.fn(),
    text: vi.fn(),
    bytes: vi.fn(),
  } as unknown as Response;
};

// Use a typed reference to the mocked fetch
const mockFetch = vi.fn();

describe("ApiClient", () => {
  let api: any;
  let originalSetTimeout: typeof setTimeout;

  beforeEach(async () => {
    vi.restoreAllMocks();
    vi.resetModules();
    mockFetch.mockReset();
    globalThis.fetch = mockFetch as unknown as typeof fetch;

    // Mock setTimeout to be instant to avoid delays in retry logic
    originalSetTimeout = globalThis.setTimeout;
    globalThis.setTimeout = vi.fn().mockImplementation((fn: Function) => {
      fn();
      return 0 as unknown as NodeJS.Timeout;
    });

    const module = await import("../../services/api");
    api = module.api;
  });

  afterEach(() => {
    globalThis.setTimeout = originalSetTimeout;
  });

  describe("health", () => {
    it("returns health data", async () => {
      const mockData = { status: "ok", service: "atlas-vox", version: "0.1.0" };
      mockFetch.mockResolvedValue(createMockResponse(mockData));

      const result = await api.health();
      expect(result).toEqual(mockData);
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/health",
        expect.objectContaining({
          headers: expect.objectContaining({ "Content-Type": "application/json" }),
        })
      );
    });
  });

  describe("error handling", () => {
    it("handles 404 errors", async () => {
      const errorResponse = createMockResponse({ detail: "Not found" }, 404, false);
      mockFetch.mockResolvedValue(errorResponse);

      await expect(api.health()).rejects.toThrow("Not found");
    });

    it("handles network errors", async () => {
      mockFetch.mockRejectedValue(new Error("Network error"));

      await expect(api.health()).rejects.toThrow("Network error");
    });

    it("handles error response without detail", async () => {
      const errorResponse = {
        ...createMockResponse({}, 500, false),
        statusText: "Internal Server Error",
        json: vi.fn().mockRejectedValue(new Error("invalid json")),
      } as unknown as Response;
      mockFetch.mockResolvedValue(errorResponse);

      await expect(api.health()).rejects.toThrow("Internal Server Error");
    });
  });

  describe("204 No Content", () => {
    it("returns undefined for 204 responses", async () => {
      const response = createMockResponse(undefined, 204, true);
      mockFetch.mockResolvedValue(response);

      const result = await api.deleteProfile("test-id");
      expect(result).toBeUndefined();
    });
  });

  describe("headers", () => {
    it("sends correct headers", async () => {
      mockFetch.mockResolvedValue(
        createMockResponse({ profiles: [], count: 0 })
      );

      await api.listProfiles();

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/profiles",
        expect.objectContaining({
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
        })
      );
    });

    it("removes Content-Type for FormData", async () => {
      mockFetch.mockResolvedValue(createMockResponse([]));

      const mockFile = new File(["audio"], "test.wav", { type: "audio/wav" });
      await api.uploadSamples("profile-1", [mockFile]);

      const callArgs = mockFetch.mock.calls[0];
      const headers = callArgs[1]?.headers as Record<string, string>;
      expect(headers["Content-Type"]).toBeUndefined();
    });
  });

  describe("profiles", () => {
    it("listProfiles returns profiles", async () => {
      const data = { profiles: [{ id: "1", name: "Test" }], count: 1 };
      mockFetch.mockResolvedValue(createMockResponse(data));

      const result = await api.listProfiles();
      expect(result).toEqual(data);
    });

    it("createProfile sends POST with data", async () => {
      const profileData = { name: "New", provider_name: "kokoro" };
      const created = { id: "1", ...profileData };
      mockFetch.mockResolvedValue(createMockResponse(created));

      const result = await api.createProfile(profileData);
      expect(result).toEqual(created);
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/profiles",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify(profileData),
        })
      );
    });

    it("deleteProfile sends DELETE", async () => {
      mockFetch.mockResolvedValue(createMockResponse(undefined, 204, true));

      await api.deleteProfile("test-id");
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/profiles/test-id",
        expect.objectContaining({ method: "DELETE" })
      );
    });
  });

  describe("synthesis", () => {
    it("synthesize sends POST with synthesis data", async () => {
      const synthData = { text: "Hello", profile_id: "p1" };
      const result = {
        id: "s1",
        audio_url: "/audio/test.wav",
        duration_seconds: 1.5,
        latency_ms: 200,
        profile_id: "p1",
        provider_name: "kokoro",
      };
      mockFetch.mockResolvedValue(createMockResponse(result));

      const res = await api.synthesize(synthData);
      expect(res).toEqual(result);
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/synthesize",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify(synthData),
        })
      );
    });
  });

  describe("providers", () => {
    it("listProviders returns providers", async () => {
      const data = { providers: [{ id: "1", name: "kokoro" }], count: 1 };
      mockFetch.mockResolvedValue(createMockResponse(data));

      const result = await api.listProviders();
      expect(result).toEqual(data);
    });

    it("checkProviderHealth sends POST", async () => {
      const health = { name: "kokoro", healthy: true, latency_ms: 50, error: null };
      mockFetch.mockResolvedValue(createMockResponse(health));

      const result = await api.checkProviderHealth("kokoro");
      expect(result).toEqual(health);
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/providers/kokoro/health",
        expect.objectContaining({ method: "POST" })
      );
    });
  });
});
