import { useEffect, useMemo, useState, useRef } from "react";
import { toast } from "sonner";
import { Type, Settings, Play, Clock, Smile, Sparkles, Mic, Upload, Layers, CheckCircle2, XCircle, Loader2, Power } from "lucide-react";
import { Button } from "../components/ui/Button";
import { SSMLEditor } from "../components/audio/SSMLEditor";
import { Select } from "../components/ui/Select";
import { AudioPlayer } from "../components/audio/AudioPlayer";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import { ProgressBar } from "../components/ui/ProgressBar";
import { Card } from "../components/ui/Card";
import AudioReactiveBackground from "../components/audio/AudioReactiveBackground";
import RotaryKnob from "../components/audio/RotaryKnob";
import VUMeter from "../components/audio/VUMeter";
import WaveformVisualizer from "../components/audio/WaveformVisualizer";
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
  const style = 0; // ElevenLabs style exaggeration — static, no UI control yet
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

  // Studio state
  const [consoleOn, setConsoleOn] = useState(true);

  // Static decorative studio VU levels — only animate when real audio is playing
  const vuLevels = { input: 42, output: 55, master: 65 };

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
    <div className="relative min-h-screen">
      {/* Audio-reactive background */}
      <AudioReactiveBackground intensity="medium" />

      <div className="relative z-10 space-y-8">
        {/* Studio Console Header */}
        <Card variant="console" className="p-6">
          <div className="flex items-center justify-between mb-6">
            {/* Console power and status */}
            <div className="flex items-center gap-6">
              <button
                onClick={() => setConsoleOn(!consoleOn)}
                className={`flex items-center gap-3 px-4 py-2 rounded-xl transition-all duration-300 ${
                  consoleOn
                    ? 'bg-led-green/20 text-led-green border border-led-green/30'
                    : 'bg-studio-slate/20 text-studio-silver border border-studio-slate/30'
                }`}
              >
                <Power className="h-5 w-5" />
                <span className="font-mono text-sm">
                  {consoleOn ? 'ONLINE' : 'STANDBY'}
                </span>
                {consoleOn && <div className="w-2 h-2 bg-led-green rounded-full animate-led-pulse" />}
              </button>

              <div className="flex items-center gap-4">
                <h1 className="text-2xl font-display font-bold text-white">
                  SYNTHESIS CONSOLE
                </h1>
                <div className="text-xs font-mono text-studio-silver bg-studio-obsidian/50 px-3 py-1 rounded border border-studio-slate/30">
                  {new Date().toLocaleTimeString()}
                </div>
              </div>
            </div>

            {/* Master VU meters */}
            <div className="flex items-center gap-6">
              <div className="text-center">
                <div className="text-xs font-mono text-studio-silver mb-1">INPUT</div>
                <VUMeter level={vuLevels.input} barCount={6} height={20} />
              </div>
              <div className="text-center">
                <div className="text-xs font-mono text-studio-silver mb-1">OUTPUT</div>
                <VUMeter level={vuLevels.output} barCount={6} height={20} />
              </div>
              <div className="text-center">
                <div className="text-xs font-mono text-studio-silver mb-1">MASTER</div>
                <VUMeter level={vuLevels.master} barCount={8} height={24} />
              </div>
            </div>
          </div>

          {/* Mode Selection */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Single / Batch toggle */}
              <div className="inline-flex rounded-xl border border-studio-slate/30 p-1 bg-studio-obsidian/30">
                <button
                  onClick={() => setBatchMode(false)}
                  className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200 ${
                    !batchMode
                      ? "bg-gradient-studio text-white shadow-lg"
                      : "text-studio-silver hover:text-white hover:bg-white/5"
                  }`}
                >
                  Single
                </button>
                <button
                  onClick={() => setBatchMode(true)}
                  className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200 ${
                    batchMode
                      ? "bg-gradient-studio text-white shadow-lg"
                      : "text-studio-silver hover:text-white hover:bg-white/5"
                  }`}
                >
                  <Layers className="h-4 w-4" /> Batch
                </button>
              </div>

              {/* Mode toggle: TTS / STS (only shown in single mode) */}
              {!batchMode && (
                <div className="inline-flex rounded-xl border border-studio-slate/30 p-1 bg-studio-obsidian/30">
                  <button
                    onClick={() => setSynthesisMode("tts")}
                    className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200 ${
                      synthesisMode === "tts"
                        ? "bg-gradient-studio text-white shadow-lg"
                        : "text-studio-silver hover:text-white hover:bg-white/5"
                    }`}
                  >
                    <Type className="h-4 w-4" /> Text-to-Speech
                  </button>
                  <button
                    onClick={() => setSynthesisMode("sts")}
                    className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200 ${
                      synthesisMode === "sts"
                        ? "bg-gradient-studio text-white shadow-lg"
                        : "text-studio-silver hover:text-white hover:bg-white/5"
                    }`}
                  >
                    <Mic className="h-4 w-4" /> Speech-to-Speech
                  </button>
                </div>
              )}
            </div>

            {/* Quick actions */}
            <div className="flex items-center gap-3">
              {profileId && !batchMode && synthesisMode === "tts" && (
                <Button
                  size="sm"
                  variant="electric"
                  onClick={() => {
                    const previewText = text.trim() ? text.slice(0, 50) : "Quick preview test.";
                    synthesize({ text: previewText, profile_id: profileId, speed, pitch, volume, output_format: outputFormat });
                  }}
                  disabled={loading}
                  className="font-mono"
                >
                  <Play className="h-3.5 w-3.5" /> PREVIEW
                </Button>
              )}
            </div>
          </div>
        </Card>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          {/* Main Content Area */}
          <div className="xl:col-span-2 space-y-6">
            {batchMode ? (
              /* =============== BATCH MODE =============== */
              <>
                <CollapsiblePanel title="Batch Input" icon={<Layers className="h-5 w-5 text-primary-500" />}>
                  <div className="space-y-4">
                    <p className="text-sm text-[var(--color-text-secondary)]">
                      Enter one line per synthesis. Each line will be processed independently.
                    </p>
                    <textarea
                      value={batchText}
                      onChange={(e) => setBatchText(e.target.value)}
                      placeholder={"Hello, welcome to the demo.\nThis is line two.\nAnd a third line for good measure."}
                      rows={10}
                      className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-4 py-3 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-secondary)] focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 resize-y"
                    />
                    <div className="flex items-center justify-between text-sm text-[var(--color-text-secondary)]">
                      <span>
                        {batchText.split("\n").filter((l) => l.trim().length > 0).length} lines
                      </span>
                      <span>{batchText.length} characters</span>
                    </div>
                  </div>
                </CollapsiblePanel>

                {batchLoading && (
                  <Card>
                    <ProgressBar percent={batchProgress} label="Batch Processing" />
                    <div className="mt-4 flex justify-center">
                      <WaveformVisualizer height={32} barCount={24} animated color="primary" />
                    </div>
                  </Card>
                )}

                {batchResults.length > 0 && (
                  <CollapsiblePanel
                    title={`Batch Results (${batchResults.filter((r) => r.status === "success").length}/${batchResults.length} succeeded)`}
                    icon={<CheckCircle2 className="h-5 w-5 text-green-500" />}
                  >
                    <div className="space-y-4 max-h-96 overflow-y-auto">
                      {batchResults.map((result, i) => (
                        <Card
                          key={`batch-${i}`}
                          className="p-4 space-y-3"
                        >
                          <div className="flex items-start gap-3">
                            {result.status === "success" ? (
                              <CheckCircle2 className="h-5 w-5 shrink-0 text-green-500 mt-0.5" />
                            ) : result.status === "error" ? (
                              <XCircle className="h-5 w-5 shrink-0 text-red-500 mt-0.5" />
                            ) : (
                              <Loader2 className="h-5 w-5 shrink-0 text-gray-400 animate-spin mt-0.5" />
                            )}
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate">{result.line}</p>
                              {result.latency_ms != null && (
                                <p className="text-xs text-[var(--color-text-secondary)] mt-1">
                                  Latency: {result.latency_ms}ms
                                </p>
                              )}
                              {result.error && (
                                <p className="text-xs text-red-500 mt-1">{result.error}</p>
                              )}
                            </div>
                          </div>
                          {result.status === "success" && result.audio_url && (
                            <AudioPlayer src={result.audio_url} compact />
                          )}
                        </Card>
                      ))}
                    </div>
                  </CollapsiblePanel>
                )}
              </>
            ) : (
              /* =============== SINGLE MODE (TTS / STS) =============== */
              <>
                {synthesisMode === "tts" ? (
                  <>
                    <CollapsiblePanel title="Text Input" icon={<Type className="h-5 w-5 text-primary-500" />}>
                      <SSMLEditor value={text} onChange={setText} minHeight={200} />
                      <div className="flex items-center justify-between mt-3">
                        <p className="text-sm text-[var(--color-text-secondary)]">
                          {text.length} / 10,000 characters
                        </p>
                        <WaveformVisualizer
                          height={20}
                          barCount={15}
                          animated={text.length > 0}
                          color="primary"
                          className="w-32"
                        />
                      </div>
                    </CollapsiblePanel>

                    {lastResult && (
                      <CollapsiblePanel title="Synthesis Result" icon={<Play className="h-5 w-5 text-green-500" />}>
                        <Card className="space-y-4">
                          <AudioPlayer src={lastResult.audio_url} />
                          <div className="grid grid-cols-3 gap-4 text-center">
                            <div>
                              <div className="text-sm font-medium text-[var(--color-text)]">Provider</div>
                              <div className="text-xs text-[var(--color-text-secondary)]">{lastResult.provider_name}</div>
                            </div>
                            <div>
                              <div className="text-sm font-medium text-[var(--color-text)]">Latency</div>
                              <div className="text-xs text-[var(--color-text-secondary)]">{lastResult.latency_ms}ms</div>
                            </div>
                            {lastResult.duration_seconds && (
                              <div>
                                <div className="text-sm font-medium text-[var(--color-text)]">Duration</div>
                                <div className="text-xs text-[var(--color-text-secondary)]">{lastResult.duration_seconds.toFixed(1)}s</div>
                              </div>
                            )}
                          </div>
                          <WaveformVisualizer height={32} barCount={20} animated={false} color="secondary" />
                        </Card>
                      </CollapsiblePanel>
                    )}
                  </>
                ) : (
                  <>
                    {/* Speech-to-Speech input */}
                    <CollapsiblePanel title="Source Audio Input" icon={<Mic className="h-5 w-5 text-primary-500" />}>
                      <div className="space-y-6">
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
                          className="flex flex-col items-center gap-4 rounded-xl border-2 border-dashed border-[var(--color-border)] p-12 cursor-pointer transition-all duration-300 hover:border-primary-400 hover:bg-primary-50/50 dark:hover:bg-primary-950/20"
                        >
                          <div className="p-4 rounded-full bg-primary-500/10">
                            <Upload className="h-8 w-8 text-primary-500" />
                          </div>
                          <div className="text-center">
                            <p className="text-lg font-medium text-[var(--color-text)]">
                              {stsFile ? stsFile.name : "Upload source audio file"}
                            </p>
                            <p className="text-sm text-[var(--color-text-secondary)] mt-2">
                              {stsFile
                                ? `${(stsFile.size / 1024 / 1024).toFixed(1)} MB`
                                : "WAV, MP3, OGG supported • Max 50MB"}
                            </p>
                          </div>
                        </div>
                        {stsBlobUrl && (
                          <Card>
                            <audio src={stsBlobUrl} controls className="w-full" />
                            <div className="mt-3">
                              <WaveformVisualizer height={24} barCount={20} animated={false} color="electric" />
                            </div>
                          </Card>
                        )}
                      </div>
                    </CollapsiblePanel>

                    {/* STS Result */}
                    {stsResult && (
                      <CollapsiblePanel title="Converted Result" icon={<Play className="h-5 w-5 text-green-500" />}>
                        <Card className="space-y-4">
                          <AudioPlayer src={stsResult.audio_url} />
                          {stsResult.duration_seconds != null && (
                            <div className="text-center">
                              <div className="text-sm font-medium text-[var(--color-text)]">Duration</div>
                              <div className="text-xs text-[var(--color-text-secondary)]">{stsResult.duration_seconds.toFixed(1)}s</div>
                            </div>
                          )}
                          <WaveformVisualizer height={32} barCount={20} animated={false} color="secondary" />
                        </Card>
                      </CollapsiblePanel>
                    )}
                  </>
                )}

                {/* Recent History */}
                {history.length > 0 && (
                  <CollapsiblePanel title="Activity Log" icon={<Clock className="h-5 w-5 text-electric-400" />} defaultOpen={false}>
                    <Card variant="console" className="max-h-64 overflow-y-auto">
                      <div className="space-y-2">
                        {history.slice(0, 8).map((h: SynthesisHistoryItem, index) => (
                          <div key={h.id} className="flex items-center gap-3 p-2 rounded-lg bg-studio-charcoal/30 hover:bg-studio-charcoal/50 transition-all duration-200">
                            <div className="flex flex-col items-center">
                              <div className="w-2 h-2 bg-led-green rounded-full" />
                              <span className="text-xs font-mono text-studio-silver mt-1">{(index + 1).toString().padStart(2, '0')}</span>
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-xs text-white truncate font-medium">{h.text}</p>
                              <div className="flex items-center gap-2 mt-1">
                                <span className="text-xs text-studio-silver">{h.provider_name}</span>
                                <span className="text-xs text-secondary-400">{h.latency_ms}ms</span>
                              </div>
                            </div>
                            <WaveformVisualizer height={12} barCount={6} animated={false} color="electric" className="w-12" />
                          </div>
                        ))}
                      </div>
                    </Card>
                  </CollapsiblePanel>
                )}
              </>
            )}
          </div>

          {/* Studio Control Panel */}
          <div className="space-y-6">
            {/* Voice Channel Settings */}
            <Card variant="console" className="p-6">
              <h3 className="text-lg font-display font-bold text-white mb-6 flex items-center gap-2">
                <Settings className="h-5 w-5 text-primary-400" />
                VOICE CHANNEL
              </h3>

              <div className="space-y-6">
                <Select
                  label="Voice Profile"
                  value={profileId}
                  onChange={(e) => handleProfileSelect(e.target.value)}
                  options={[{ value: "", label: "Select profile..." }, ...profileOptions]}
                  className="text-white"
                />

                {synthesisMode === "tts" && (
                  <Select
                    label="Persona Preset"
                    value={presetId}
                    onChange={(e) => handlePresetSelect(e.target.value, presets)}
                    options={[{ value: "", label: "None" }, ...presets.map((p) => ({ value: p.id, label: p.name }))]}
                    className="text-white"
                  />
                )}

                <Select
                  label="Output Format"
                  value={outputFormat}
                  onChange={(e) => setOutputFormat(e.target.value)}
                  options={OUTPUT_FORMATS.map((f) => ({ value: f.value, label: f.label }))}
                  className="text-white"
                />
              </div>
            </Card>

            {/* Rotary Control Section */}
            {synthesisMode === "tts" && (
              <Card variant="console" className="p-6">
                <h3 className="text-lg font-display font-bold text-white mb-6 flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-secondary-400" />
                  AUDIO PROCESSING
                </h3>

                <div className="grid grid-cols-2 gap-6">
                  <RotaryKnob
                    value={speed}
                    onChange={setSpeed}
                    min={0.5}
                    max={2}
                    step={0.05}
                    label="Speed"
                    colorFrom="hsl(var(--electric-500))"
                    colorTo="hsl(var(--electric-600))"
                    size="md"
                  />
                  <RotaryKnob
                    value={pitch}
                    onChange={setPitch}
                    min={-50}
                    max={50}
                    step={1}
                    label="Pitch"
                    colorFrom="hsl(var(--primary-500))"
                    colorTo="hsl(var(--primary-600))"
                    size="md"
                  />
                  <RotaryKnob
                    value={volume}
                    onChange={setVolume}
                    min={0}
                    max={2}
                    step={0.05}
                    label="Volume"
                    colorFrom="hsl(var(--secondary-400))"
                    colorTo="hsl(var(--secondary-500))"
                    size="md"
                  />
                  {batchMode && (
                    <div className="flex flex-col items-center justify-center">
                      <div className="text-center">
                        <div className="text-xs font-mono text-studio-silver mb-2">BATCH COUNT</div>
                        <div className="text-2xl font-bold text-white">
                          {batchText.split("\n").filter((l) => l.trim().length > 0).length}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </Card>
            )}

            {/* ElevenLabs Voice Settings */}
            {isElevenLabs && synthesisMode === "tts" && (
              <CollapsiblePanel title="Voice Settings" icon={<Sparkles className="h-5 w-5 text-violet-400" />} defaultOpen={false}>
                <Card variant="console" className="p-4 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <RotaryKnob
                      value={stability}
                      onChange={setStability}
                      min={0}
                      max={1}
                      step={0.05}
                      label="Stability"
                      colorFrom="hsl(260, 85%, 55%)"
                      colorTo="hsl(280, 85%, 55%)"
                      size="sm"
                    />
                    <RotaryKnob
                      value={similarityBoost}
                      onChange={setSimilarityBoost}
                      min={0}
                      max={1}
                      step={0.05}
                      label="Similarity"
                      colorFrom="hsl(310, 85%, 55%)"
                      colorTo="hsl(330, 85%, 55%)"
                      size="sm"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-studio-silver">Speaker Boost</span>
                    <label className="flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={speakerBoost}
                        onChange={(e) => setSpeakerBoost(e.target.checked)}
                        className="sr-only"
                      />
                      <div className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${speakerBoost ? 'bg-primary-500' : 'bg-studio-slate'}`}>
                        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${speakerBoost ? 'translate-x-6' : 'translate-x-1'}`} />
                      </div>
                    </label>
                  </div>
                </Card>
              </CollapsiblePanel>
            )}

            {/* Azure Emotion Controls */}
            {isAzure && synthesisMode === "tts" && (
              <CollapsiblePanel title="Expression Style" icon={<Smile className="h-5 w-5 text-amber-400" />} defaultOpen={false}>
                <div className="grid grid-cols-2 gap-2">
                  {AZURE_EMOTIONS.slice(0, 12).map((em) => (
                    <button
                      key={em.value}
                      onClick={() => { setEmotion(em.value); }}
                      className={`rounded-lg px-3 py-2 text-xs font-medium transition-all duration-200 ${
                        emotion === em.value
                          ? "bg-gradient-studio text-white"
                          : "bg-studio-charcoal/30 text-studio-silver hover:bg-studio-charcoal/50 hover:text-white"
                      }`}
                    >
                      {em.label}
                    </button>
                  ))}
                </div>
              </CollapsiblePanel>
            )}

            {/* Main Action Button */}
            <Card variant="console" className="p-6">
              {batchMode ? (
                <Button
                  className="w-full text-lg py-4"
                  variant="primary"
                  audioReactive
                  onClick={handleBatchSynthesize}
                  disabled={
                    batchLoading ||
                    !profileId ||
                    batchText.split("\n").filter((l) => l.trim().length > 0).length === 0
                  }
                >
                  {batchLoading ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      PROCESSING BATCH...
                    </>
                  ) : (
                    <>
                      <Layers className="h-5 w-5" />
                      SYNTHESIZE BATCH
                    </>
                  )}
                </Button>
              ) : synthesisMode === "tts" ? (
                <Button
                  className="w-full text-lg py-4"
                  variant="primary"
                  audioReactive
                  onClick={handleSynthesize}
                  disabled={loading || !text.trim() || !profileId}
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      SYNTHESIZING...
                    </>
                  ) : (
                    <>
                      <Play className="h-5 w-5" />
                      SYNTHESIZE AUDIO
                    </>
                  )}
                </Button>
              ) : (
                <Button
                  className="w-full text-lg py-4"
                  variant="electric"
                  audioReactive
                  onClick={handleSpeechToSpeech}
                  disabled={stsLoading || !stsFile || !profileId}
                >
                  {stsLoading ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      CONVERTING...
                    </>
                  ) : (
                    <>
                      <Mic className="h-5 w-5" />
                      CONVERT VOICE
                    </>
                  )}
                </Button>
              )}
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
