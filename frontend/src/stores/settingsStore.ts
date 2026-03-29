import { create } from "zustand";
import { persist } from "zustand/middleware";
import { createLogger } from "../utils/logger";

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
