import { create } from "zustand";
import { persist } from "zustand/middleware";
import { createLogger } from "../utils/logger";
import { THEME_BY_ID, DEFAULT_THEME_ID, applyThemeToDOM, type Theme } from "../themes";

const logger = createLogger("DesignStore");

export interface DesignTokens {
  // Theme selection (replaces accentHue/accentSaturation for full theme support)
  themeId: string;
  // Legacy color tokens (still used by DesignSystemPage for hue tweaking)
  accentHue: number;        // 0-360 hue for primary color
  accentSaturation: number;  // 0-100
  borderRadius: "none" | "sm" | "md" | "lg" | "xl" | "full";
  // Typography
  fontFamily: "system" | "inter" | "mono" | "serif";
  fontSize: "compact" | "default" | "large";
  // Spacing
  density: "compact" | "default" | "spacious";
  // Sidebar
  sidebarWidth: number;     // pixels, 200-320
  sidebarCollapsed: boolean;
  // Layout
  contentMaxWidth: "full" | "xl" | "2xl" | "4xl" | "6xl";
  // Panels
  panelDefaultOpen: boolean;
  // Animations
  animationsEnabled: boolean;
  // Card style
  cardStyle: "flat" | "raised" | "bordered" | "glass" | "console";
}

const DEFAULT_TOKENS: DesignTokens = {
  themeId: DEFAULT_THEME_ID,
  accentHue: 338,
  accentSaturation: 85,
  borderRadius: "lg",
  fontFamily: "system",
  fontSize: "default",
  density: "default",
  sidebarWidth: 280,
  sidebarCollapsed: false,
  contentMaxWidth: "full",
  panelDefaultOpen: true,
  animationsEnabled: true,
  cardStyle: "bordered",
};

interface DesignState {
  tokens: DesignTokens;
  setToken: <K extends keyof DesignTokens>(key: K, value: DesignTokens[K]) => void;
  setTokens: (partial: Partial<DesignTokens>) => void;
  setTheme: (themeId: string) => void;
  getCurrentTheme: () => Theme;
  resetTokens: () => void;
  applyToDOM: () => void;
}

export const useDesignStore = create<DesignState>()(
  persist(
    (set, get) => ({
      tokens: { ...DEFAULT_TOKENS },

      setToken: (key, value) => {
        logger.info("token_change", { key, value });
        set((state) => ({
          tokens: { ...state.tokens, [key]: value },
        }));
        // Apply immediately
        setTimeout(() => get().applyToDOM(), 0);
      },

      setTokens: (partial) => {
        logger.info("tokens_batch_change", { keys: Object.keys(partial) });
        set((state) => ({
          tokens: { ...state.tokens, ...partial },
        }));
        setTimeout(() => get().applyToDOM(), 0);
      },

      setTheme: (themeId) => {
        const theme = THEME_BY_ID[themeId];
        if (!theme) {
          logger.error("theme_not_found", { themeId });
          return;
        }
        logger.info("theme_change", { themeId, name: theme.name });
        set((state) => ({
          tokens: {
            ...state.tokens,
            themeId,
            // Sync legacy accentHue/Saturation with theme primary
            accentHue: theme.primary.h,
            accentSaturation: theme.primary.s,
          },
        }));
        setTimeout(() => get().applyToDOM(), 0);
      },

      getCurrentTheme: () => {
        const { tokens } = get();
        return THEME_BY_ID[tokens.themeId] || THEME_BY_ID[DEFAULT_THEME_ID];
      },

      resetTokens: () => {
        logger.info("tokens_reset");
        set({ tokens: { ...DEFAULT_TOKENS } });
        setTimeout(() => get().applyToDOM(), 0);
      },

      applyToDOM: () => {
        const { tokens } = get();
        const root = document.documentElement;

        // === STEP 1: Apply user-overridable design tokens ===
        // (theme will overwrite shape/density/font tokens after this)

        // Font size scale (always user-controlled)
        const sizeMap = { compact: "14px", default: "16px", large: "18px" };
        root.style.setProperty("--font-size-base", sizeMap[tokens.fontSize]);

        // Sidebar width (always user-controlled)
        root.style.setProperty("--sidebar-width", `${tokens.sidebarWidth}px`);

        // Content max width (always user-controlled)
        const maxWidthMap = { full: "100%", xl: "1280px", "2xl": "1536px", "4xl": "1792px", "6xl": "2048px" };
        root.style.setProperty("--content-max-width", maxWidthMap[tokens.contentMaxWidth]);

        // Animations on/off master toggle
        if (!tokens.animationsEnabled) {
          root.style.setProperty("--theme-anim-duration", "0ms");
        }

        // === STEP 2: Apply theme LAST so personality wins ===
        // Theme writes: colors, radius, density, fonts, card style, animations,
        // background pattern, hover effects, shadows, letter spacing, weights
        const theme = THEME_BY_ID[tokens.themeId] || THEME_BY_ID[DEFAULT_THEME_ID];
        applyThemeToDOM(theme);

        // === STEP 3: Legacy accent fallback for user hue tweaking ===
        // Only apply if user has tweaked away from theme defaults
        if (
          tokens.accentHue !== theme.primary.h ||
          tokens.accentSaturation !== theme.primary.s
        ) {
          root.style.setProperty("--studio-primary-h", String(tokens.accentHue));
          root.style.setProperty("--studio-primary-s", `${tokens.accentSaturation}%`);
          root.style.setProperty("--accent-h", String(tokens.accentHue));
          root.style.setProperty("--accent-s", `${tokens.accentSaturation}%`);
        }
      },
    }),
    {
      name: "atlas-vox-design",
    }
  )
);
