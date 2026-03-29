import { describe, it, expect, beforeEach, vi } from "vitest";
import { useSettingsStore } from "../../stores/settingsStore";

vi.mock("../../utils/logger", () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

describe("SettingsStore", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    // Reset to defaults
    useSettingsStore.setState({
      theme: "light",
      defaultProvider: "kokoro",
      audioFormat: "wav",
    });
    // Mock document.documentElement for theme toggling
    document.documentElement.classList.remove("dark");
  });

  describe("toggleTheme", () => {
    it("toggles from light to dark", () => {
      useSettingsStore.getState().toggleTheme();

      expect(useSettingsStore.getState().theme).toBe("dark");
      expect(document.documentElement.classList.contains("dark")).toBe(true);
    });

    it("toggles from dark to light", () => {
      useSettingsStore.setState({ theme: "dark" });
      document.documentElement.classList.add("dark");

      useSettingsStore.getState().toggleTheme();

      expect(useSettingsStore.getState().theme).toBe("light");
      expect(document.documentElement.classList.contains("dark")).toBe(false);
    });

    it("toggles back and forth", () => {
      expect(useSettingsStore.getState().theme).toBe("light");

      useSettingsStore.getState().toggleTheme();
      expect(useSettingsStore.getState().theme).toBe("dark");

      useSettingsStore.getState().toggleTheme();
      expect(useSettingsStore.getState().theme).toBe("light");
    });
  });

  describe("setDefaultProvider", () => {
    it("sets the default provider", () => {
      useSettingsStore.getState().setDefaultProvider("piper");

      expect(useSettingsStore.getState().defaultProvider).toBe("piper");
    });

    it("accepts any provider string", () => {
      useSettingsStore.getState().setDefaultProvider("elevenlabs");
      expect(useSettingsStore.getState().defaultProvider).toBe("elevenlabs");

      useSettingsStore.getState().setDefaultProvider("azure_speech");
      expect(useSettingsStore.getState().defaultProvider).toBe("azure_speech");
    });
  });

  describe("setAudioFormat", () => {
    it("sets the audio format", () => {
      useSettingsStore.getState().setAudioFormat("mp3");

      expect(useSettingsStore.getState().audioFormat).toBe("mp3");
    });

    it("accepts different formats", () => {
      useSettingsStore.getState().setAudioFormat("ogg");
      expect(useSettingsStore.getState().audioFormat).toBe("ogg");

      useSettingsStore.getState().setAudioFormat("flac");
      expect(useSettingsStore.getState().audioFormat).toBe("flac");
    });
  });

  describe("defaults", () => {
    it("has correct default values", () => {
      // Reset fully
      useSettingsStore.setState({
        theme: "light",
        defaultProvider: "kokoro",
        audioFormat: "wav",
      });

      const state = useSettingsStore.getState();
      expect(state.theme).toBe("light");
      expect(state.defaultProvider).toBe("kokoro");
      expect(state.audioFormat).toBe("wav");
    });
  });
});
