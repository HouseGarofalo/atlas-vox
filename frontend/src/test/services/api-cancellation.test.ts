import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import apiClient from "../../services/api";

vi.mock("../../utils/logger", () => ({
  createLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }),
}));

vi.mock("../../stores/authStore", () => ({
  useAuthStore: {
    getState: () => ({ apiKey: null, authDisabled: true, logout: vi.fn() }),
  },
}));

/** Deferred-promise helper so tests can hold fetch pending, then resolve/abort. */
function deferred<T>() {
  let resolve: (v: T) => void = () => {};
  let reject: (e: unknown) => void = () => {};
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function okResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("ApiClient AbortController registry (P2-21)", () => {
  const fetchSpy = vi.fn();

  beforeEach(() => {
    // @ts-expect-error test stub
    globalThis.fetch = fetchSpy;
    fetchSpy.mockReset();
    apiClient.abortAll(); // clean any bleed-over from earlier tests
  });

  afterEach(() => {
    apiClient.abortAll();
  });

  it("aborts the previous call when a new one with the same method+path fires", async () => {
    // First call: hangs forever until aborted.
    const first = deferred<Response>();
    // Second call: resolves immediately with profiles.
    const second = deferred<Response>();
    fetchSpy
      .mockImplementationOnce((_url, init) => {
        // Reject when aborted.
        init.signal.addEventListener("abort", () => {
          const err = new Error("aborted");
          err.name = "AbortError";
          first.reject(err);
        });
        return first.promise;
      })
      .mockImplementationOnce(() => {
        second.resolve(okResponse({ profiles: [], count: 0 }));
        return second.promise;
      });

    const p1 = apiClient.listProfiles().catch((e) => e);
    const p2 = apiClient.listProfiles();

    const [firstOutcome, secondOutcome] = await Promise.all([p1, p2]);
    expect((firstOutcome as Error).name).toBe("AbortError");
    expect(secondOutcome).toEqual({ profiles: [], count: 0 });
  });

  it("does NOT cancel unrelated endpoints", async () => {
    const hang = deferred<Response>();
    fetchSpy
      // listProfiles pending until aborted.
      .mockImplementationOnce((_u, init) => {
        init.signal.addEventListener("abort", () => {
          const e = new Error("aborted"); e.name = "AbortError"; hang.reject(e);
        });
        return hang.promise;
      })
      // listVersions is a different path — should proceed independently.
      .mockImplementationOnce(() => Promise.resolve(okResponse({ versions: [], count: 0 })));

    const profilesP = apiClient.listProfiles().catch((e) => e);
    const versionsResult = await apiClient.listVersions("profile-abc");
    expect(versionsResult).toEqual({ versions: [], count: 0 });

    // Cancel the still-pending one so the test cleans up.
    apiClient.abortAll();
    const pErr = await profilesP;
    expect((pErr as Error).name).toBe("AbortError");
  });

  it("abortAll cancels every in-flight request at once", async () => {
    const h1 = deferred<Response>();
    const h2 = deferred<Response>();
    let abortedCount = 0;
    fetchSpy
      .mockImplementationOnce((_u, init) => {
        init.signal.addEventListener("abort", () => {
          abortedCount++;
          const e = new Error("a"); e.name = "AbortError"; h1.reject(e);
        });
        return h1.promise;
      })
      .mockImplementationOnce((_u, init) => {
        init.signal.addEventListener("abort", () => {
          abortedCount++;
          const e = new Error("a"); e.name = "AbortError"; h2.reject(e);
        });
        return h2.promise;
      });

    const p1 = apiClient.listProfiles().catch(() => {});
    const p2 = apiClient.listVersions("pp").catch(() => {});
    apiClient.abortAll();
    await Promise.all([p1, p2]);
    expect(abortedCount).toBe(2);
  });
});
