import { useEffect, useState, useRef } from "react";
import { toast } from "sonner";
import { Type, Settings, Play, Clock, Smile, Sparkles, Mic, Upload } from "lucide-react";
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

const AZURE_EMOTIONS = [
  { value: "", label: "None" },
  { value: "neutral", label: "Neutral" },
  { value: "cheerful", label: "Cheerful" },
  { value: "sad", label: "Sad" },
  { value: "angry", label: "Angry" },
  { value: "excited", label: "Excited" },
  { value: "friendly", label: "Friendly" },
  { value: "hopeful", label: "Hopeful" },
] as const;

const OUTPUT_FORMATS = [
  { value: "wav", label: "WAV" },
  { value: "mp3", label: "MP3" },
  { value: "ogg", label: "OGG" },
] as const;

type SynthesisMode = "tts" | "sts";

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
  const [emotion, setEmotion] = useState("");
  const [outputFormat, setOutputFormat] = useState("wav");

  // ElevenLabs voice settings
  const [stability, setStability] = useState(0.5);
  const [similarityBoost, setSimilarityBoost] = useState(0.75);
  const [style, setStyle] = useState(0);
  const [speakerBoost, setSpeakerBoost] = useState(false);

  // Speech-to-Speech mode
  const [synthesisMode, setSynthesisMode] = useState<SynthesisMode>("tts");
  const [stsFile, setStsFile] = useState<File | null>(null);
  const [stsLoading, setStsLoading] = useState(false);
  const [stsResult, setStsResult] = useState<{ audio_url: string; duration_seconds: number | null } | null>(null);
  const stsInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchProfiles();
    fetchHistory(20);
    api.listPresets().then(({ presets: p }) => setPresets(p)).catch(() => {});
  }, []);

  const profileOptions = profiles.map((p) => ({ value: p.id, label: `${p.name} (${p.provider_name})` }));
  const selectedProfileData = profiles.find((p) => p.id === profileId);
  const isAzure = selectedProfileData?.provider_name === "azure_speech";
  const isElevenLabs = selectedProfileData?.provider_name === "elevenlabs";

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
    logger.info("synthesis_start", { text_length: text.length, profile_id: profileId, emotion, output_format: outputFormat });

    // Wrap text with SSML emotion tags for Azure if an emotion is selected
    let finalText = text;
    let useSSML = false;
    if (isAzure && emotion) {
      finalText = `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US"><voice name=""><mstts:express-as style="${emotion}">${text}</mstts:express-as></voice></speak>`;
      useSSML = true;
    }

    // Build ElevenLabs voice settings if applicable
    const elevenLabsSettings = isElevenLabs ? { stability, similarity_boost: similarityBoost, style, use_speaker_boost: speakerBoost } : undefined;

    try {
      await synthesize({
        text: finalText,
        profile_id: profileId,
        preset_id: presetId || undefined,
        speed,
        pitch,
        volume,
        output_format: outputFormat,
        ssml: useSSML || undefined,
        ...(elevenLabsSettings ? { voice_settings: elevenLabsSettings } : {}),
      });
      logger.info("synthesis_complete", { text_length: text.length });
      toast.success("Synthesis complete");
      fetchHistory(20);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Synthesis failed";
      logger.error("synthesis_error", { error: message });
      toast.error(message);
    }
  };

  const handleSpeechToSpeech = async () => {
    if (!stsFile || !profileId || !selectedProfileData) {
      toast.error("Select a profile and upload an audio file");
      return;
    }
    logger.info("sts_start", { profile_id: profileId, filename: stsFile.name });
    setStsLoading(true);
    setStsResult(null);
    try {
      const result = await api.speechToSpeech(
        stsFile,
        selectedProfileData.voice_id || profileId,
        selectedProfileData.provider_name,
      );
      setStsResult({ audio_url: result.audio_url, duration_seconds: null });
      logger.info("sts_complete", { audio_url: result.audio_url });
      toast.success("Speech-to-Speech conversion complete");
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Speech-to-Speech failed";
      logger.error("sts_error", { error: message });
      toast.error(message);
    } finally {
      setStsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Synthesis Lab</h1>
        {/* Mode toggle: TTS / STS */}
        <div className="inline-flex rounded-lg border border-[var(--color-border)] p-0.5">
          <button
            onClick={() => setSynthesisMode("tts")}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              synthesisMode === "tts"
                ? "bg-primary-500 text-white"
                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
            }`}
          >
            <Type className="h-3.5 w-3.5" /> Text-to-Speech
          </button>
          <button
            onClick={() => setSynthesisMode("sts")}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              synthesisMode === "sts"
                ? "bg-primary-500 text-white"
                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
            }`}
          >
            <Mic className="h-3.5 w-3.5" /> Speech-to-Speech
          </button>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Main content area */}
        <div className="flex-1 min-w-0 space-y-4">
          {synthesisMode === "tts" ? (
            <>
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
            </>
          ) : (
            <>
              {/* Speech-to-Speech input */}
              <CollapsiblePanel title="Source Audio" icon={<Mic className="h-4 w-4 text-primary-500" />}>
                <div className="space-y-4">
                  <input
                    ref={stsInputRef}
                    type="file"
                    accept="audio/*"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) setStsFile(file);
                    }}
                  />
                  <div
                    onClick={() => stsInputRef.current?.click()}
                    className="flex flex-col items-center gap-3 rounded-lg border-2 border-dashed border-[var(--color-border)] p-8 cursor-pointer transition-colors hover:border-primary-400 hover:bg-primary-50/50 dark:hover:bg-primary-950/20"
                  >
                    <Upload className="h-8 w-8 text-[var(--color-text-secondary)]" />
                    <div className="text-center">
                      <p className="text-sm font-medium text-[var(--color-text)]">
                        {stsFile ? stsFile.name : "Click to upload source audio"}
                      </p>
                      <p className="text-xs text-[var(--color-text-secondary)] mt-1">
                        {stsFile
                          ? `${(stsFile.size / 1024).toFixed(1)} KB`
                          : "WAV, MP3, OGG supported"}
                      </p>
                    </div>
                  </div>
                  {stsFile && (
                    <audio src={URL.createObjectURL(stsFile)} controls className="w-full h-10" />
                  )}
                </div>
              </CollapsiblePanel>

              {/* STS Result */}
              {stsResult && (
                <CollapsiblePanel title="Converted Result" icon={<Play className="h-4 w-4 text-green-500" />}>
                  <AudioPlayer src={stsResult.audio_url} />
                  {stsResult.duration_seconds != null && (
                    <p className="mt-2 text-xs text-[var(--color-text-secondary)]">
                      Duration: {stsResult.duration_seconds.toFixed(1)}s
                    </p>
                  )}
                </CollapsiblePanel>
              )}
            </>
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
              {synthesisMode === "tts" && (
                <>
                  <Select
                    label="Persona Preset" value={presetId}
                    onChange={(e) => handlePresetSelect(e.target.value, presets)}
                    options={[{ value: "", label: "None" }, ...presets.map((p) => ({ value: p.id, label: p.name }))]}
                  />
                  <Slider label="Speed" id="speed" min={0.5} max={2} step={0.05} value={speed} onChange={(e) => setSpeed(Number(e.target.value))} displayValue={`${speed.toFixed(2)}x`} />
                  <Slider label="Pitch" id="pitch" min={-50} max={50} step={1} value={pitch} onChange={(e) => setPitch(Number(e.target.value))} displayValue={`${pitch > 0 ? "+" : ""}${pitch}`} />
                  <Slider label="Volume" id="volume" min={0} max={2} step={0.05} value={volume} onChange={(e) => setVolume(Number(e.target.value))} displayValue={`${(volume * 100).toFixed(0)}%`} />
                </>
              )}
              <Select
                label="Output Format"
                value={outputFormat}
                onChange={(e) => setOutputFormat(e.target.value)}
                options={OUTPUT_FORMATS.map((f) => ({ value: f.value, label: f.label }))}
              />
            </div>
          </CollapsiblePanel>

          {/* ElevenLabs Voice Settings */}
          {isElevenLabs && (
            <CollapsiblePanel title="Voice Settings" icon={<Sparkles className="h-4 w-4 text-violet-500" />} defaultOpen={false}>
              <div className="space-y-4">
                <div className="space-y-1">
                  <Slider
                    label="Stability"
                    id="el-stability"
                    min={0}
                    max={1}
                    step={0.05}
                    value={stability}
                    onChange={(e) => setStability(Number(e.target.value))}
                    displayValue={stability.toFixed(2)}
                  />
                  <p className="text-[10px] text-[var(--color-text-secondary)]">Lower = more expressive, Higher = more stable</p>
                </div>
                <div className="space-y-1">
                  <Slider
                    label="Similarity Boost"
                    id="el-similarity"
                    min={0}
                    max={1}
                    step={0.05}
                    value={similarityBoost}
                    onChange={(e) => setSimilarityBoost(Number(e.target.value))}
                    displayValue={similarityBoost.toFixed(2)}
                  />
                  <p className="text-[10px] text-[var(--color-text-secondary)]">How closely to match the original voice</p>
                </div>
                <div className="space-y-1">
                  <Slider
                    label="Style"
                    id="el-style"
                    min={0}
                    max={1}
                    step={0.05}
                    value={style}
                    onChange={(e) => setStyle(Number(e.target.value))}
                    displayValue={style.toFixed(2)}
                  />
                  <p className="text-[10px] text-[var(--color-text-secondary)]">Style exaggeration (increases latency)</p>
                </div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={speakerBoost}
                    onChange={(e) => setSpeakerBoost(e.target.checked)}
                    className="h-4 w-4 rounded border-[var(--color-border)] text-primary-500 focus:ring-primary-500"
                  />
                  <span className="text-sm text-[var(--color-text)]">Speaker Boost</span>
                  <span className="text-[10px] text-[var(--color-text-secondary)]">Enhance voice similarity</span>
                </label>
              </div>
            </CollapsiblePanel>
          )}

          {isAzure && (
            <CollapsiblePanel title="Emotion / Style" icon={<Smile className="h-4 w-4 text-amber-500" />}>
              <div className="flex flex-wrap gap-2">
                {AZURE_EMOTIONS.map((em) => (
                  <button
                    key={em.value}
                    onClick={() => { setEmotion(em.value); logger.info("emotion_selected", { emotion: em.value }); }}
                    className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors border ${
                      emotion === em.value
                        ? "bg-primary-500 text-white border-primary-500"
                        : "bg-transparent text-[var(--color-text-secondary)] border-[var(--color-border)] hover:border-primary-400"
                    }`}
                  >
                    {em.label}
                  </button>
                ))}
              </div>
              {emotion && (
                <p className="mt-2 text-xs text-[var(--color-text-secondary)]">
                  SSML &lt;mstts:express-as style="{emotion}"&gt; will be applied.
                </p>
              )}
            </CollapsiblePanel>
          )}

          {synthesisMode === "tts" ? (
            <Button className="w-full" onClick={handleSynthesize} disabled={loading || !text.trim() || !profileId}>
              {loading ? "Synthesizing..." : "Synthesize"}
            </Button>
          ) : (
            <Button className="w-full" onClick={handleSpeechToSpeech} disabled={stsLoading || !stsFile || !profileId}>
              {stsLoading ? "Converting..." : "Convert"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
