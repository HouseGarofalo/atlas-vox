import { create } from "zustand";
import { createLogger } from "../utils/logger";

const logger = createLogger("AuthStore");

const API_BASE = "/api/v1";

interface AuthUser {
  sub: string;
  scopes: string[];
}

interface AuthState {
  isAuthenticated: boolean;
  user: AuthUser | null;
  apiKey: string | null;
  error: string | null;
  isLoading: boolean;
  authDisabled: boolean;

  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  fetchMe: () => Promise<void>;
  setApiKey: (key: string) => Promise<void>;
  setAuthDisabled: () => void;
  clearAuth: () => void;
  hasScope: (scope: string) => boolean;
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  isAuthenticated: false,
  user: null,
  apiKey: null,
  error: null,
  isLoading: false,
  authDisabled: false,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Login failed" }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      // JWT is now in httpOnly cookie — fetch user info from /auth/me
      await get().fetchMe();
      logger.info("login_success");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Login failed";
      logger.error("login_failed", { error: msg });
      set({ isLoading: false, error: msg, isAuthenticated: false, user: null });
      throw e;
    }
  },

  logout: async () => {
    logger.info("logout");
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // Best-effort — clear client state regardless
      logger.warn("logout_request_failed");
    }
    set({
      isAuthenticated: false,
      user: null,
      apiKey: null,
      error: null,
      isLoading: false,
      authDisabled: false,
    });
  },

  refreshToken: async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) {
        throw new Error(`Refresh failed: HTTP ${res.status}`);
      }
      // New JWT cookie set by server — refresh user info
      await get().fetchMe();
      logger.info("token_refreshed");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Refresh failed";
      logger.warn("token_refresh_failed", { error: msg });
      // Token refresh failed — force re-login
      set({ isAuthenticated: false, user: null, error: msg });
    }
  },

  fetchMe: async () => {
    set({ isLoading: true, error: null });
    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      // If using API key auth, attach it
      const { apiKey } = get();
      if (apiKey) {
        headers["Authorization"] = `Bearer ${apiKey}`;
      }

      const res = await fetch(`${API_BASE}/auth/me`, {
        headers,
        credentials: "include",
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      set({
        isAuthenticated: true,
        user: { sub: data.sub, scopes: data.scopes || [] },
        isLoading: false,
        error: null,
      });
      logger.info("user_fetched", { sub: data.sub });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to fetch user";
      logger.warn("fetch_me_failed", { error: msg });
      set({ isLoading: false, error: msg });
      throw e;
    }
  },

  setApiKey: async (key: string) => {
    logger.info("api_key_set");
    set({ apiKey: key, isLoading: true, error: null });
    try {
      // Fetch actual scopes from server instead of assuming admin
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${key}`,
        },
        credentials: "include",
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      set({
        apiKey: key,
        isAuthenticated: true,
        user: { sub: data.sub, scopes: data.scopes || [] },
        isLoading: false,
        error: null,
      });
      logger.info("api_key_validated", { sub: data.sub });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "API key validation failed";
      logger.warn("api_key_validation_failed", { error: msg });
      // Still set the key — server will validate on each request.
      // Mark as authenticated with empty scopes; actual authorization
      // happens server-side.
      set({
        apiKey: key,
        isAuthenticated: true,
        user: { sub: "api-key-user", scopes: [] },
        isLoading: false,
        error: null,
      });
    }
  },

  setAuthDisabled: () => {
    logger.info("auth_disabled_mode");
    set({
      apiKey: null,
      user: { sub: "local-user", scopes: ["admin"] },
      isAuthenticated: true,
      authDisabled: true,
      isLoading: false,
      error: null,
    });
  },

  clearAuth: () => {
    set({
      isAuthenticated: false,
      user: null,
      apiKey: null,
      error: null,
      isLoading: false,
      authDisabled: false,
    });
  },

  hasScope: (scope: string) => {
    const user = get().user;
    if (!user) return false;
    return user.scopes.includes("admin") || user.scopes.includes(scope);
  },
}));
