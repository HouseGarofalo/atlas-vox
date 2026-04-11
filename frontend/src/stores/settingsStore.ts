import { create } from "zustand";
import { persist } from "zustand/middleware";
import { createLogger } from "../utils/logger";
import { useDesignStore } from "./designStore";

const logger = createLogger("SettingsStore");

interface SettingsState {
  theme: "light" | "dark";
  defaultProvider: string;
  audioFormat: string;
  toggleTheme: () => void;
  setDefaultProvider: (provider: string) => void;
  setAudioFormat: (format: string) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: "light",
      defaultProvider: "kokoro",
      audioFormat: "wav",
      toggleTheme: () =>
        set((state) => {
          const next = state.theme === "light" ? "dark" : "light";
          logger.info("toggleTheme", { from: state.theme, to: next });
          document.documentElement.classList.toggle("dark", next === "dark");
          // Re-apply active theme so its neutral palette picks up the new mode
          useDesignStore.getState().applyToDOM();
          return { theme: next };
        }),
      setDefaultProvider: (provider) => {
        logger.info("setDefaultProvider", { provider });
        set({ defaultProvider: provider });
      },
      setAudioFormat: (format) => {
        logger.info("setAudioFormat", { format });
        set({ audioFormat: format });
      },
    }),
    { name: "atlas-vox-settings" }
  )
);
