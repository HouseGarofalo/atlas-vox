import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Type, Settings, Play, Clock } from "lucide-react";
import { Button } from "../components/ui/Button";
import { SSMLEditor } from "../components/audio/SSMLEditor";
import { Select } from "../components/ui/Select";
import { Slider } from "../components/ui/Slider";
import { AudioPlayer } from "../components/audio/AudioPlayer";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import { useProfileStore } from "../stores/profileStore";
import { useSynthesisStore } from "../stores/synthesisStore";
import { api } from "../services/api";
import type { PersonaPreset, SynthesisHistoryItem } from "../types";
import { createLogger } from "../utils/logger";

const logger = createLogger("SynthesisLabPage");

export default function SynthesisLabPage() {
  const { profiles, fetchProfiles } = useProfileStore();
  const { lastResult, loading, synthesize, fetchHistory, history } = useSynthesisStore();
  const [text, setText] = useState("");
  const [profileId, setProfileId] = useState("");
  const [presetId, setPresetId] = useState("");
  const [presets, setPresets] = useState<PersonaPreset[]>([]);
  const [speed, setSpeed] = useState(1.0);
  const [pitch, setPitch] = useState(0);
  const [volume, setVolume] = useState(1.0);

  useEffect(() => {
    fetchProfiles();
    fetchHistory(20);
    api.listPresets().then(({ presets: p }) => setPresets(p)).catch(() => {});
  }, []);

  const profileOptions = profiles.map((p) => ({ value: p.id, label: `${p.name} (${p.provider_name})` }));

  const handleProfileSelect = (id: string) => {
    setProfileId(id);
    if (id) logger.info("profile_selected", { profile_id: id });
  };

  const handlePresetSelect = (id: string, presetsList: PersonaPreset[]) => {
    setPresetId(id);
    if (id) logger.info("preset_selected", { preset_id: id });
    const p = presetsList.find((pr) => pr.id === id);
    if (p) { setSpeed(p.speed); setPitch(p.pitch); setVolume(p.volume); }
  };

  const handleSynthesize = async () => {
    if (!text.trim() || !profileId) { toast.error("Enter text and select a profile"); return; }
    logger.info("synthesis_start", { text_length: text.length, profile_id: profileId });
    try {
      await synthesize({ text, profile_id: profileId, preset_id: presetId || undefined, speed, pitch, volume });
      logger.info("synthesis_complete", { text_length: text.length });
      toast.success("Synthesis complete");
      fetchHistory(20);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Synthesis failed";
      logger.error("synthesis_error", { error: message });
      toast.error(message);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Synthesis Lab</h1>
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Main content area */}
        <div className="flex-1 min-w-0 space-y-4">
          <CollapsiblePanel title="Text Input" icon={<Type className="h-4 w-4 text-primary-500" />}>
            <SSMLEditor value={text} onChange={setText} minHeight={180} />
            <p className="mt-1 text-xs text-[var(--color-text-secondary)]">{text.length} / 10000 characters</p>
          </CollapsiblePanel>

          {lastResult && (
            <CollapsiblePanel title="Result" icon={<Play className="h-4 w-4 text-green-500" />}>
              <AudioPlayer src={lastResult.audio_url} />
              <div className="mt-2 flex flex-wrap gap-4 text-xs text-[var(--color-text-secondary)]">
                <span>Provider: {lastResult.provider_name}</span>
                <span>Latency: {lastResult.latency_ms}ms</span>
                {lastResult.duration_seconds && <span>Duration: {lastResult.duration_seconds.toFixed(1)}s</span>}
              </div>
            </CollapsiblePanel>
          )}

          {history.length > 0 && (
            <CollapsiblePanel title="Recent History" icon={<Clock className="h-4 w-4 text-blue-500" />} defaultOpen={false}>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {history.map((h: SynthesisHistoryItem) => (
                  <div key={h.id} className="flex items-center gap-2 text-xs py-1 border-b border-[var(--color-border)] last:border-0">
                    <span className="flex-1 truncate">{h.text}</span>
                    <span className="text-[var(--color-text-secondary)]">{h.latency_ms}ms</span>
                  </div>
                ))}
              </div>
            </CollapsiblePanel>
          )}
        </div>

        {/* Settings sidebar */}
        <div className="w-full lg:w-80 xl:w-96 flex-shrink-0 space-y-4">
          <CollapsiblePanel title="Synthesis Settings" icon={<Settings className="h-4 w-4 text-gray-500" />}>
            <div className="space-y-4">
              <Select label="Voice Profile" value={profileId} onChange={(e) => handleProfileSelect(e.target.value)} options={[{ value: "", label: "Select profile..." }, ...profileOptions]} />
              <Select
                label="Persona Preset" value={presetId}
                onChange={(e) => handlePresetSelect(e.target.value, presets)}
                options={[{ value: "", label: "None" }, ...presets.map((p) => ({ value: p.id, label: p.name }))]}
              />
              <Slider label="Speed" id="speed" min={0.5} max={2} step={0.05} value={speed} onChange={(e) => setSpeed(Number(e.target.value))} displayValue={`${speed.toFixed(2)}x`} />
              <Slider label="Pitch" id="pitch" min={-50} max={50} step={1} value={pitch} onChange={(e) => setPitch(Number(e.target.value))} displayValue={`${pitch > 0 ? "+" : ""}${pitch}`} />
              <Slider label="Volume" id="volume" min={0} max={2} step={0.05} value={volume} onChange={(e) => setVolume(Number(e.target.value))} displayValue={`${(volume * 100).toFixed(0)}%`} />
            </div>
          </CollapsiblePanel>
          <Button className="w-full" onClick={handleSynthesize} disabled={loading || !text.trim() || !profileId}>
            {loading ? "Synthesizing..." : "Synthesize"}
          </Button>
        </div>
      </div>
    </div>
  );
}
