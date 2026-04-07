import { create } from "zustand";
import { persist } from "zustand/middleware";
import { createLogger } from "../utils/logger";

const logger = createLogger("AuthStore");

interface AuthState {
  token: string | null;
  apiKey: string | null;
  user: { sub: string; scopes: string[] } | null;
  isAuthenticated: boolean;
  authDisabled: boolean;
  setToken: (token: string) => void;
  setApiKey: (key: string) => void;
  setAuthDisabled: () => void;
  logout: () => void;
  hasScope: (scope: string) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      apiKey: null,
      user: null,
      isAuthenticated: false,
      authDisabled: false,

      setToken: (token: string) => {
        logger.info("token_set");
        try {
          const payload = JSON.parse(atob(token.split(".")[1]));
          set({
            token,
            user: { sub: payload.sub, scopes: payload.scopes || ["admin"] },
            isAuthenticated: true,
            authDisabled: false,
          });
        } catch {
          // Not a valid JWT — treat as opaque token
          logger.warn("token_not_jwt", { hint: "Token is not a decodable JWT" });
          set({ token, user: { sub: "unknown", scopes: [] }, isAuthenticated: true });
        }
      },

      setAuthDisabled: () => {
        logger.info("auth_disabled_mode");
        set({
          token: null,
          apiKey: null,
          user: { sub: "local-user", scopes: ["admin"] },
          isAuthenticated: true,
          authDisabled: true,
        });
      },

      setApiKey: (key: string) => {
        logger.info("api_key_set");
        set({
          apiKey: key,
          token: null,
          isAuthenticated: true,
          // API key scopes are validated server-side; assume admin for UI
          user: { sub: "api-key-user", scopes: ["admin"] },
        });
      },

      logout: () => {
        logger.info("logout");
        set({ token: null, apiKey: null, user: null, isAuthenticated: false, authDisabled: false });
      },

      hasScope: (scope: string) => {
        const user = get().user;
        if (!user) return false;
        return user.scopes.includes("admin") || user.scopes.includes(scope);
      },
    }),
    { name: "atlas-vox-auth" }
  )
);
