import { useEffect, useMemo, useState, useRef } from "react";
import { toast } from "sonner";
import { Type, Settings, Play, Clock, Smile, Sparkles, Mic, Upload, Layers, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { Button } from "../components/ui/Button";
import { SSMLEditor } from "../components/audio/SSMLEditor";
import { Select } from "../components/ui/Select";
import { Slider } from "../components/ui/Slider";
import { AudioPlayer } from "../components/audio/AudioPlayer";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import { ProgressBar } from "../components/ui/ProgressBar";
import { useProfileStore } from "../stores/profileStore";
import { useSettingsStore } from "../stores/settingsStore";
import { useSynthesisStore } from "../stores/synthesisStore";
import { api } from "../services/api";
import type { PersonaPreset, SynthesisHistoryItem } from "../types";
import { createLogger } from "../utils/logger";
import { getErrorMessage } from "../utils/errors";

const logger = createLogger("SynthesisLabPage");

interface BatchLineResult {
  line: string;
  status: "pending" | "success" | "error";
  audio_url?: string;
  latency_ms?: number;
  error?: string;
}

const AZURE_EMOTIONS = [
  { value: "", label: "None" },
  { value: "neutral", label: "Neutral" },
  { value: "cheerful", label: "Cheerful" },
  { value: "sad", label: "Sad" },
  { value: "angry", label: "Angry" },
  { value: "excited", label: "Excited" },
  { value: "friendly", label: "Friendly" },
  { value: "hopeful", label: "Hopeful" },
  { value: "whispering", label: "Whispering" },
  { value: "terrified", label: "Terrified" },
  { value: "unfriendly", label: "Unfriendly" },
  { value: "shouting", label: "Shouting" },
  { value: "empathetic", label: "Empathetic" },
  { value: "calm", label: "Calm" },
  { value: "gentle", label: "Gentle" },
  { value: "serious", label: "Serious" },
  { value: "depressed", label: "Depressed" },
  { value: "embarrassed", label: "Embarrassed" },
  { value: "envious", label: "Envious" },
  { value: "lyrical", label: "Lyrical" },
  { value: "poetry-reading", label: "Poetry Reading" },
  { value: "narration-professional", label: "Narration (Professional)" },
  { value: "newscast-casual", label: "Newscast (Casual)" },
  { value: "newscast-formal", label: "Newscast (Formal)" },
  { value: "documentary-narration", label: "Documentary Narration" },
  { value: "chat", label: "Chat" },
  { value: "customer-service", label: "Customer Service" },
  { value: "assistant", label: "Assistant" },
] as const;

const OUTPUT_FORMATS = [
  { value: "wav", label: "WAV" },
  { value: "mp3", label: "MP3" },
  { value: "ogg", label: "OGG" },
] as const;

type SynthesisMode = "tts" | "sts";

export default function SynthesisLabPage() {
  const { profiles, fetchProfiles } = useProfileStore();
  const { defaultProvider, audioFormat } = useSettingsStore();
  const { lastResult, loading, synthesize, fetchHistory, history } = useSynthesisStore();
  const [text, setText] = useState("");
  const [profileId, setProfileId] = useState("");
  const [presetId, setPresetId] = useState("");
  const [presets, setPresets] = useState<PersonaPreset[]>([]);
  const [speed, setSpeed] = useState(1.0);
  const [pitch, setPitch] = useState(0);
  const [volume, setVolume] = useState(1.0);
  const [emotion, setEmotion] = useState("");
  const [outputFormat, setOutputFormat] = useState(audioFormat || "wav");

  // ElevenLabs voice settings
  const [stability, setStability] = useState(0.5);
  const [similarityBoost, setSimilarityBoost] = useState(0.75);
  const [style, setStyle] = useState(0);
  const [speakerBoost, setSpeakerBoost] = useState(false);

  // Batch mode
  const [batchMode, setBatchMode] = useState(false);
  const [batchText, setBatchText] = useState("");
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchResults, setBatchResults] = useState<BatchLineResult[]>([]);
  const [batchProgress, setBatchProgress] = useState(0);

  // Speech-to-Speech mode
  const [synthesisMode, setSynthesisMode] = useState<SynthesisMode>("tts");
  const [stsFile, setStsFile] = useState<File | null>(null);
  const [stsLoading, setStsLoading] = useState(false);
  const [stsResult, setStsResult] = useState<{ audio_url: string; duration_seconds: number | null } | null>(null);
  const stsInputRef = useRef<HTMLInputElement>(null);

  // Stable blob URL for STS file — revoked on change to prevent memory leaks
  const stsBlobUrl = useMemo(() => {
    if (!stsFile) return null;
    return URL.createObjectURL(stsFile);
  }, [stsFile]);
  useEffect(() => {
    return () => { if (stsBlobUrl) URL.revokeObjectURL(stsBlobUrl); };
  }, [stsBlobUrl]);

  useEffect(() => {
    fetchProfiles();
    fetchHistory(20);
    api.listPresets().then(({ presets: p }) => setPresets(p)).catch(() => {});
  }, []);

  // Auto-select first profile matching the user's default provider
  useEffect(() => {
    if (profileId || profiles.length === 0) return;
    const match = profiles.find((p) => p.provider_name === defaultProvider);
    if (match) setProfileId(match.id);
    else if (profiles.length > 0) setProfileId(profiles[0].id);
  }, [profiles, defaultProvider]);

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

    let finalText = text;
    let useSSML = false;
    if (isAzure && emotion) {
      finalText = `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US"><voice name=""><mstts:express-as style="${emotion}">${text}</mstts:express-as></voice></speak>`;
      useSSML = true;
    }

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

  const handleBatchSynthesize = async () => {
    const lines = batchText
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
    if (lines.length === 0 || !profileId) {
      toast.error("Enter at least one line and select a profile");
      return;
    }
    logger.info("batch_synthesis_start", { lineCount: lines.length, profile_id: profileId });
    setBatchLoading(true);
    setBatchProgress(10);
    setBatchResults(lines.map((line) => ({ line, status: "pending" })));

    try {
      setBatchProgress(30);
      const results = await api.batchSynthesize({
        lines,
        profile_id: profileId,
        preset_id: presetId || undefined,
        speed,
      });
      setBatchProgress(90);

      const mapped: BatchLineResult[] = lines.map((line, i) => {
        const r = results[i];
        if (r) {
          return {
            line,
            status: "success" as const,
            audio_url: r.audio_url,
            latency_ms: r.latency_ms,
          };
        }
        return { line, status: "error" as const, error: "No result returned" };
      });

      setBatchResults(mapped);
      setBatchProgress(100);
      const successCount = mapped.filter((r) => r.status === "success").length;
      logger.info("batch_synthesis_complete", { total: lines.length, success: successCount });
      toast.success(`Batch complete: ${successCount}/${lines.length} succeeded`);
      fetchHistory(20);
    } catch (e: unknown) {
      const message = getErrorMessage(e);
      logger.error("batch_synthesis_error", { error: message });
      setBatchResults((prev) =>
        prev.map((r) => (r.status === "pending" ? { ...r, status: "error" as const, error: message } : r))
      );
      toast.error(message);
    } finally {
      setBatchLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Synthesis Lab</h1>
        <div className="flex items-center gap-3">
          {/* Single / Batch toggle */}
          <div className="inline-flex rounded-lg border border-[var(--color-border)] p-0.5">
            <button
              onClick={() => setBatchMode(false)}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                !batchMode
                  ? "bg-primary-500 text-white"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
              }`}
            >
              Single
            </button>
            <button
              onClick={() => setBatchMode(true)}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                batchMode
                  ? "bg-primary-500 text-white"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
              }`}
            >
              <Layers className="h-3.5 w-3.5" /> Batch
            </button>
          </div>

          {/* Mode toggle: TTS / STS (only shown in single mode) */}
          {!batchMode && (
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
          )}
        </div>
      </div>

      {batchMode ? (
        /* =============== BATCH MODE =============== */
        <div className="flex flex-col lg:flex-row gap-6">
          <div className="flex-1 min-w-0 space-y-4">
            <CollapsiblePanel title="Batch Input" icon={<Layers className="h-4 w-4 text-primary-500" />}>
              <div className="space-y-3">
                <p className="text-xs text-[var(--color-text-secondary)]">
                  Enter one line per synthesis. Each line will be synthesized independently.
                </p>
                <textarea
                  value={batchText}
                  onChange={(e) => setBatchText(e.target.value)}
                  placeholder={"Hello, welcome to the demo.\nThis is line two.\nAnd a third line for good measure."}
                  rows={8}
                  className="w-full rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-secondary)] focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 resize-y"
                />
                <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)]">
                  <span>
                    {batchText.split("\n").filter((l) => l.trim().length > 0).length} line(s)
                  </span>
                  <span>{batchText.length} characters</span>
                </div>
              </div>
            </CollapsiblePanel>

            {batchLoading && (
              <ProgressBar percent={batchProgress} label="Batch Progress" />
            )}

            {batchResults.length > 0 && (
              <CollapsiblePanel
                title={`Results (${batchResults.filter((r) => r.status === "success").length}/${batchResults.length} succeeded)`}
                icon={<Play className="h-4 w-4 text-green-500" />}
              >
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {batchResults.map((result, i) => (
                    <div
                      key={`batch-${i}`}
                      className="rounded-lg border border-[var(--color-border)] p-3 space-y-2"
                    >
                      <div className="flex items-start gap-2">
                        {result.status === "success" ? (
                          <CheckCircle2 className="h-4 w-4 shrink-0 text-green-500 mt-0.5" />
                        ) : result.status === "error" ? (
                          <XCircle className="h-4 w-4 shrink-0 text-red-500 mt-0.5" />
                        ) : (
                          <Loader2 className="h-4 w-4 shrink-0 text-gray-400 animate-spin mt-0.5" />
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm truncate">{result.line}</p>
                          {result.latency_ms != null && (
                            <p className="text-xs text-[var(--color-text-secondary)]">
                              Latency: {result.latency_ms}ms
                            </p>
                          )}
                          {result.error && (
                            <p className="text-xs text-red-500">{result.error}</p>
                          )}
                        </div>
                      </div>
                      {result.status === "success" && result.audio_url && (
                        <AudioPlayer src={result.audio_url} compact />
                      )}
                    </div>
                  ))}
                </div>
              </CollapsiblePanel>
            )}
          </div>

          {/* Batch settings sidebar */}
          <div className="w-full lg:w-80 xl:w-96 flex-shrink-0 space-y-4">
            <CollapsiblePanel title="Batch Settings" icon={<Settings className="h-4 w-4 text-gray-500" />}>
              <div className="space-y-4">
                <Select
                  label="Voice Profile"
                  value={profileId}
                  onChange={(e) => handleProfileSelect(e.target.value)}
                  options={[{ value: "", label: "Select profile..." }, ...profileOptions]}
                />
                <Select
                  label="Persona Preset"
                  value={presetId}
                  onChange={(e) => handlePresetSelect(e.target.value, presets)}
                  options={[{ value: "", label: "None" }, ...presets.map((p) => ({ value: p.id, label: p.name }))]}
                />
                <Slider
                  label="Speed"
                  id="batch-speed"
                  min={0.5}
                  max={2}
                  step={0.05}
                  value={speed}
                  onChange={(e) => setSpeed(Number(e.target.value))}
                  displayValue={`${speed.toFixed(2)}x`}
                />
              </div>
            </CollapsiblePanel>

            <Button
              className="w-full"
              onClick={handleBatchSynthesize}
              disabled={
                batchLoading ||
                !profileId ||
                batchText.split("\n").filter((l) => l.trim().length > 0).length === 0
              }
            >
              {batchLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Synthesizing...
                </>
              ) : (
                <>
                  <Layers className="h-4 w-4" />
                  Synthesize All
                </>
              )}
            </Button>
          </div>
        </div>
      ) : (
        /* =============== SINGLE MODE (TTS / STS) =============== */
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
                    {stsBlobUrl && (
                      <audio src={stsBlobUrl} controls className="w-full h-10" />
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
                    {profileId && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          const previewText = text.trim() ? text.slice(0, 100) : "Hello, this is a quick preview of the current settings.";
                          synthesize({ text: previewText, profile_id: profileId, speed, pitch, volume, output_format: outputFormat });
                        }}
                        disabled={loading}
                        className="mt-2"
                      >
                        <Play className="h-3.5 w-3.5" /> Quick Preview
                      </Button>
                    )}
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
      )}
    </div>
  );
}
