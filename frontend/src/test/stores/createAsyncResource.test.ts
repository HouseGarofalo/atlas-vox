import { describe, it, expect, beforeEach, vi } from "vitest";
import { createAsyncResource, type AsyncResourceState } from "../../stores/createAsyncResource";

vi.mock("../../utils/logger", () => ({
  createLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }),
}));

/** Tiny manual store shim so the test doesn't need Zustand. */
function makeStore<T>(initial: AsyncResourceState<T>) {
  let state = initial;
  return {
    get: () => state,
    set: (partial: Partial<AsyncResourceState<T>> | ((s: AsyncResourceState<T>) => Partial<AsyncResourceState<T>>)) => {
      const patch = typeof partial === "function" ? partial(state) : partial;
      state = { ...state, ...patch };
    },
    current: () => state,
  };
}

describe("createAsyncResource", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it("fetch populates data and sets lastFetchedAt", async () => {
    const resource = createAsyncResource<number[]>({
      name: "nums",
      fetcher: async () => [1, 2, 3],
    });
    const store = makeStore(resource.initialState());

    const data = await resource.fetch(store.set, store.get);
    expect(data).toEqual([1, 2, 3]);
    expect(store.current().data).toEqual([1, 2, 3]);
    expect(store.current().loading).toBe(false);
    expect(store.current().error).toBeNull();
    expect(store.current().lastFetchedAt).not.toBeNull();
  });

  it("skips refetch within staleness window", async () => {
    const fetcher = vi.fn().mockResolvedValue([1]);
    const resource = createAsyncResource({ name: "x", fetcher, staleMs: 1000 });
    const store = makeStore(resource.initialState());

    await resource.fetch(store.set, store.get);
    await resource.fetch(store.set, store.get);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("force:true bypasses staleness", async () => {
    const fetcher = vi.fn().mockResolvedValue([1]);
    const resource = createAsyncResource({ name: "x", fetcher, staleMs: 10_000 });
    const store = makeStore(resource.initialState());

    await resource.fetch(store.set, store.get);
    await resource.fetch(store.set, store.get, true);
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("aborts previous fetch when a new one fires", async () => {
    vi.useRealTimers();

    let firstAborted = false;
    const fetcher = vi.fn().mockImplementation((signal: AbortSignal) => {
      return new Promise((resolve, reject) => {
        signal.addEventListener("abort", () => {
          firstAborted = true;
          const e = new Error("aborted"); e.name = "AbortError"; reject(e);
        });
        // Never resolves on its own.
      });
    }).mockImplementationOnce((signal: AbortSignal) => {
      return new Promise((resolve, reject) => {
        signal.addEventListener("abort", () => {
          firstAborted = true;
          const e = new Error("aborted"); e.name = "AbortError"; reject(e);
        });
      });
    }).mockImplementationOnce(async () => [99]);

    const resource = createAsyncResource<number[]>({
      name: "race",
      fetcher,
      staleMs: 0, // disable staleness so second fetch proceeds
    });
    const store = makeStore(resource.initialState());

    // Start the first call but don't await.
    const firstP = resource.fetch(store.set, store.get);
    // Second call: abort the first.
    const secondData = await resource.fetch(store.set, store.get);

    await firstP; // allow first to settle (AbortError caught internally)
    expect(firstAborted).toBe(true);
    expect(secondData).toEqual([99]);
  });

  it("error state set on non-abort failures, data preserved", async () => {
    const resource = createAsyncResource<number[]>({
      name: "boom",
      fetcher: async () => { throw new Error("kaboom"); },
    });
    const store = makeStore({ ...resource.initialState(), data: [5] });

    await resource.fetch(store.set, store.get, true);
    expect(store.current().error).toBe("kaboom");
    expect(store.current().loading).toBe(false);
    expect(store.current().data).toEqual([5]); // previous data preserved
  });

  it("invalidate clears staleness so next fetch runs", async () => {
    const fetcher = vi.fn().mockResolvedValue([1]);
    const resource = createAsyncResource({ name: "inv", fetcher, staleMs: 60_000 });
    const store = makeStore(resource.initialState());

    await resource.fetch(store.set, store.get);
    resource.invalidate(store.set);
    await resource.fetch(store.set, store.get);
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("reset restores initial state", async () => {
    const resource = createAsyncResource<number[]>({
      name: "rst",
      fetcher: async () => [7, 8, 9],
      initialData: [],
    });
    const store = makeStore(resource.initialState());
    await resource.fetch(store.set, store.get);
    resource.reset(store.set);
    expect(store.current().data).toEqual([]);
    expect(store.current().lastFetchedAt).toBeNull();
  });
});
