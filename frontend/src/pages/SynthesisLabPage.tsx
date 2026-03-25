import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { TextArea } from "../components/ui/TextArea";
import { Select } from "../components/ui/Select";
import { Slider } from "../components/ui/Slider";
import { AudioPlayer } from "../components/audio/AudioPlayer";
import { useProfileStore } from "../stores/profileStore";
import { useSynthesisStore } from "../stores/synthesisStore";
import { api } from "../services/api";

export default function SynthesisLabPage() {
  const { profiles, fetchProfiles } = useProfileStore();
  const { lastResult, loading, synthesize, fetchHistory, history } = useSynthesisStore();
  const [text, setText] = useState("");
  const [profileId, setProfileId] = useState("");
  const [presetId, setPresetId] = useState("");
  const [presets, setPresets] = useState<any[]>([]);
  const [speed, setSpeed] = useState(1.0);
  const [pitch, setPitch] = useState(0);
  const [volume, setVolume] = useState(1.0);

  useEffect(() => {
    fetchProfiles();
    fetchHistory(20);
    api.listPresets().then(({ presets: p }) => setPresets(p)).catch(() => {});
  }, []);

  const profileOptions = profiles.map((p) => ({ value: p.id, label: `${p.name} (${p.provider_name})` }));

  const handleSynthesize = async () => {
    if (!text.trim() || !profileId) { toast.error("Enter text and select a profile"); return; }
    try {
      await synthesize({ text, profile_id: profileId, preset_id: presetId || undefined, speed, pitch, volume });
      toast.success("Synthesis complete");
      fetchHistory(20);
    } catch (e: any) { toast.error(e.message); }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Synthesis Lab</h1>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <TextArea label="Text to synthesize" rows={6} value={text} onChange={(e) => setText(e.target.value)} placeholder="Enter text or SSML here..." />
            <p className="mt-1 text-xs text-[var(--color-text-secondary)]">{text.length} / 10000 characters</p>
          </Card>
          {lastResult && (
            <Card>
              <h3 className="mb-2 text-sm font-semibold">Result</h3>
              <AudioPlayer src={lastResult.audio_url} />
              <div className="mt-2 flex gap-4 text-xs text-[var(--color-text-secondary)]">
                <span>Provider: {lastResult.provider_name}</span>
                <span>Latency: {lastResult.latency_ms}ms</span>
                {lastResult.duration_seconds && <span>Duration: {lastResult.duration_seconds.toFixed(1)}s</span>}
              </div>
            </Card>
          )}
          {history.length > 0 && (
            <Card>
              <h3 className="mb-2 text-sm font-semibold">Recent</h3>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {history.map((h: any) => (
                  <div key={h.id} className="flex items-center gap-2 text-xs py-1 border-b border-[var(--color-border)] last:border-0">
                    <span className="flex-1 truncate">{h.text}</span>
                    <span className="text-[var(--color-text-secondary)]">{h.latency_ms}ms</span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
        <div className="space-y-4">
          <Card>
            <h3 className="mb-3 text-sm font-semibold">Settings</h3>
            <div className="space-y-4">
              <Select label="Voice Profile" value={profileId} onChange={(e) => setProfileId(e.target.value)} options={[{ value: "", label: "Select profile..." }, ...profileOptions]} />
              <Select
                label="Persona Preset" value={presetId}
                onChange={(e) => {
                  setPresetId(e.target.value);
                  const p = presets.find((pr: any) => pr.id === e.target.value);
                  if (p) { setSpeed(p.speed); setPitch(p.pitch); setVolume(p.volume); }
                }}
                options={[{ value: "", label: "None" }, ...presets.map((p: any) => ({ value: p.id, label: p.name }))]}
              />
              <Slider label="Speed" id="speed" min={0.5} max={2} step={0.05} value={speed} onChange={(e) => setSpeed(Number(e.target.value))} displayValue={`${speed.toFixed(2)}x`} />
              <Slider label="Pitch" id="pitch" min={-50} max={50} step={1} value={pitch} onChange={(e) => setPitch(Number(e.target.value))} displayValue={`${pitch > 0 ? "+" : ""}${pitch}`} />
              <Slider label="Volume" id="volume" min={0} max={2} step={0.05} value={volume} onChange={(e) => setVolume(Number(e.target.value))} displayValue={`${(volume * 100).toFixed(0)}%`} />
            </div>
          </Card>
          <Button className="w-full" onClick={handleSynthesize} disabled={loading || !text.trim() || !profileId}>
            {loading ? "Synthesizing..." : "Synthesize"}
          </Button>
        </div>
      </div>
    </div>
  );
}
