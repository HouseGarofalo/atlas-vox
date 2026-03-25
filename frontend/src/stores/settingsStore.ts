import { create } from "zustand";
import { persist } from "zustand/middleware";

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
          document.documentElement.classList.toggle("dark", next === "dark");
          return { theme: next };
        }),
      setDefaultProvider: (provider) => set({ defaultProvider: provider }),
      setAudioFormat: (format) => set({ audioFormat: format }),
    }),
    { name: "atlas-vox-settings" }
  )
);
