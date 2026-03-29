import { create } from "zustand";
import { persist } from "zustand/middleware";
import { createLogger } from "../utils/logger";

const logger = createLogger("AuthStore");

interface AuthState {
  token: string | null;
  apiKey: string | null;
  user: { sub: string; scopes: string[] } | null;
  isAuthenticated: boolean;
  setToken: (token: string) => void;
  setApiKey: (key: string) => void;
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

      setToken: (token: string) => {
        logger.info("token_set");
        try {
          const payload = JSON.parse(atob(token.split(".")[1]));
          set({
            token,
            user: { sub: payload.sub, scopes: payload.scopes || ["admin"] },
            isAuthenticated: true,
          });
        } catch {
          set({ token, user: { sub: "unknown", scopes: [] }, isAuthenticated: true });
        }
      },

      setApiKey: (key: string) => {
        logger.info("api_key_set");
        set({ apiKey: key, isAuthenticated: true, user: { sub: "api-key-user", scopes: ["admin"] } });
      },

      logout: () => {
        logger.info("logout");
        set({ token: null, apiKey: null, user: null, isAuthenticated: false });
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
