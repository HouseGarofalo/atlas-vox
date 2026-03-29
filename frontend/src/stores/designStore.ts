import { create } from "zustand";
import { persist } from "zustand/middleware";
import { createLogger } from "../utils/logger";

const logger = createLogger("DesignStore");

export interface DesignTokens {
  // Colors
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
  cardStyle: "flat" | "raised" | "bordered" | "glass";
}

const DEFAULT_TOKENS: DesignTokens = {
  accentHue: 217,
  accentSaturation: 91,
  borderRadius: "lg",
  fontFamily: "system",
  fontSize: "default",
  density: "default",
  sidebarWidth: 256,
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

      resetTokens: () => {
        logger.info("tokens_reset");
        set({ tokens: { ...DEFAULT_TOKENS } });
        setTimeout(() => get().applyToDOM(), 0);
      },

      applyToDOM: () => {
        const { tokens } = get();
        const root = document.documentElement;

        // Accent color as HSL
        root.style.setProperty("--accent-h", String(tokens.accentHue));
        root.style.setProperty("--accent-s", `${tokens.accentSaturation}%`);

        // Border radius
        const radiusMap = { none: "0px", sm: "4px", md: "8px", lg: "12px", xl: "16px", full: "9999px" };
        root.style.setProperty("--radius", radiusMap[tokens.borderRadius]);

        // Font family
        const fontMap = {
          system: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          inter: '"Inter", -apple-system, sans-serif',
          mono: '"JetBrains Mono", "Fira Code", monospace',
          serif: '"Georgia", "Times New Roman", serif',
        };
        root.style.setProperty("--font-family", fontMap[tokens.fontFamily]);

        // Font size scale
        const sizeMap = { compact: "14px", default: "16px", large: "18px" };
        root.style.setProperty("--font-size-base", sizeMap[tokens.fontSize]);

        // Density (padding/gap scale)
        const densityMap = { compact: "0.75", default: "1", spacious: "1.25" };
        root.style.setProperty("--density", densityMap[tokens.density]);

        // Sidebar width
        root.style.setProperty("--sidebar-width", `${tokens.sidebarWidth}px`);

        // Content max width
        const maxWidthMap = { full: "100%", xl: "1280px", "2xl": "1536px", "4xl": "1792px", "6xl": "2048px" };
        root.style.setProperty("--content-max-width", maxWidthMap[tokens.contentMaxWidth]);

        // Animations
        if (!tokens.animationsEnabled) {
          root.style.setProperty("--transition-duration", "0ms");
        } else {
          root.style.removeProperty("--transition-duration");
        }

        // Card style
        root.dataset.cardStyle = tokens.cardStyle;
      },
    }),
    {
      name: "atlas-vox-design",
    }
  )
);
