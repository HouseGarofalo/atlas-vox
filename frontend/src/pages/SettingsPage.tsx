import { useEffect } from "react";
import { Palette, Sliders, Info } from "lucide-react";
import { Select } from "../components/ui/Select";
import { Button } from "../components/ui/Button";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import { useSettingsStore } from "../stores/settingsStore";
import { useProviderStore } from "../stores/providerStore";
import { createLogger } from "../utils/logger";

const logger = createLogger("SettingsPage");

export default function SettingsPage() {
  const { theme, defaultProvider, audioFormat, toggleTheme, setDefaultProvider, setAudioFormat } = useSettingsStore();
  const { providers, fetchProviders } = useProviderStore();
  useEffect(() => { logger.info("page_mounted"); fetchProviders().then(() => logger.info("providers_fetched")); }, []);

  const providerOptions = providers.map((p) => ({ value: p.name, label: p.display_name }));
  if (!providerOptions.length) providerOptions.push({ value: "kokoro", label: "Kokoro" });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      <CollapsiblePanel title="Appearance" icon={<Palette className="h-4 w-4 text-purple-500" />}>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">Theme</p>
            <p className="text-sm text-[var(--color-text-secondary)]">Currently: {theme === "dark" ? "Dark" : "Light"}</p>
          </div>
          <Button variant="secondary" onClick={toggleTheme}>Switch to {theme === "dark" ? "Light" : "Dark"}</Button>
        </div>
      </CollapsiblePanel>

      <CollapsiblePanel title="Defaults" icon={<Sliders className="h-4 w-4 text-blue-500" />}>
        <div className="space-y-4 max-w-md">
          <Select label="Default Provider" value={defaultProvider} onChange={(e) => setDefaultProvider(e.target.value)} options={providerOptions} />
          <Select label="Default Audio Format" value={audioFormat} onChange={(e) => setAudioFormat(e.target.value)} options={[{ value: "wav", label: "WAV (lossless)" }, { value: "mp3", label: "MP3 (compressed)" }, { value: "ogg", label: "OGG (compressed)" }]} />
        </div>
      </CollapsiblePanel>

      <CollapsiblePanel title="About" icon={<Info className="h-4 w-4 text-gray-500" />}>
        <div className="space-y-1 text-sm text-[var(--color-text-secondary)]">
          <p>Atlas Vox v0.1.0</p>
          <p>Intelligent Voice Training & Customization Platform</p>
          <p>9 TTS providers &middot; 4 interfaces &middot; Full training pipeline</p>
        </div>
      </CollapsiblePanel>
    </div>
  );
}
