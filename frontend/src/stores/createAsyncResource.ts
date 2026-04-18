/**
 * `createAsyncResource` — shared helper that standardizes the fetch/loading/
 * error/staleness/abort boilerplate every resource-backed Zustand store was
 * copy-pasting.
 *
 * Usage (example — profileStore):
 *
 *   const profilesResource = createAsyncResource<VoiceProfile[]>({
 *     name: "profiles",
 *     fetcher: async (signal) => (await api.listProfiles({ signal })).profiles,
 *     staleMs: 30_000,
 *   });
 *
 *   // Compose into your store with additional mutation actions:
 *   export const useProfileStore = create<ProfileState>((set, get) => ({
 *     ...profilesResource.initialState(),
 *     fetchProfiles: (force) => profilesResource.fetch(set, get, force),
 *     // …domain-specific mutations
 *   }));
 *
 * Design notes:
 *  - Runs with an AbortController; a new fetch aborts any prior in-flight
 *    fetch for the same resource, mirroring api.ts cancellation semantics.
 *  - Enforces a staleness window so repeated `fetch()` calls within `staleMs`
 *    are no-ops unless the caller passes `force: true`.
 *  - Does NOT lock out concurrent fetches — the second call aborts the first
 *    rather than waiting. This matches what users actually want when they
 *    switch filters rapidly.
 */

import { createLogger } from "../utils/logger";
import { getErrorMessage } from "../utils/errors";

export interface AsyncResourceState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  lastFetchedAt: number | null;
}

export interface AsyncResourceOptions<T> {
  /** Logger tag / debugging identifier. Also used for abort-key namespacing. */
  name: string;
  /** Fetcher. Receives an AbortSignal that fires if the fetch is superseded. */
  fetcher: (signal: AbortSignal) => Promise<T>;
  /** Window during which a repeat fetch is a no-op. Default 30s. */
  staleMs?: number;
  /** Optional initial value (default null). */
  initialData?: T | null;
}

export interface AsyncResource<T, S extends AsyncResourceState<T>> {
  /** Initial slice to spread into a store. */
  initialState: () => AsyncResourceState<T>;
  /** Fetch unless fresh; `force=true` bypasses staleness. */
  fetch: (
    set: (partial: Partial<S> | ((s: S) => Partial<S>)) => void,
    get: () => S,
    force?: boolean,
  ) => Promise<T | null>;
  /** Cancel any in-flight fetch. */
  abort: () => void;
  /** Force-refresh on next access (clears `lastFetchedAt`). */
  invalidate: (
    set: (partial: Partial<S>) => void,
  ) => void;
  /** Reset to initial state (useful on logout). */
  reset: (
    set: (partial: Partial<S>) => void,
  ) => void;
}

export function createAsyncResource<
  T,
  S extends AsyncResourceState<T> = AsyncResourceState<T>,
>(options: AsyncResourceOptions<T>): AsyncResource<T, S> {
  const logger = createLogger(`AsyncResource:${options.name}`);
  const staleMs = options.staleMs ?? 30_000;
  const initialData = options.initialData ?? null;
  let activeController: AbortController | null = null;

  const abort = () => {
    if (activeController) {
      try { activeController.abort(); } catch { /* ignore */ }
      activeController = null;
    }
  };

  return {
    initialState: () => ({
      data: initialData,
      loading: false,
      error: null,
      lastFetchedAt: null,
    }),

    fetch: async (set, get, force = false) => {
      const current = get();
      if (!force && current.lastFetchedAt && Date.now() - current.lastFetchedAt < staleMs) {
        return current.data as T | null;
      }

      abort();
      const controller = new AbortController();
      activeController = controller;

      // Narrow patch type to the shared async-resource fields so callers
      // don't have to cast on every set() call.
      set({ loading: true, error: null } as Partial<S>);
      logger.info("fetch_start", { force });

      try {
        const data = await options.fetcher(controller.signal);
        if (controller.signal.aborted) return current.data as T | null;
        set({
          data,
          loading: false,
          error: null,
          lastFetchedAt: Date.now(),
        } as Partial<S>);
        logger.info("fetch_ok");
        return data;
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          logger.info("fetch_aborted");
          return current.data as T | null;
        }
        const message = getErrorMessage(err);
        logger.error("fetch_failed", { error: message });
        set({ loading: false, error: message } as Partial<S>);
        return current.data as T | null;
      } finally {
        if (activeController === controller) activeController = null;
      }
    },

    abort,

    invalidate: (set) => {
      set({ lastFetchedAt: null } as Partial<S>);
    },

    reset: (set) => {
      abort();
      set({
        data: initialData,
        loading: false,
        error: null,
        lastFetchedAt: null,
      } as Partial<S>);
    },
  };
}
