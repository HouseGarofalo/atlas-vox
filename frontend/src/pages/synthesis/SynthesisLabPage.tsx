import { useEffect, useState, useRef } from "react";
import { toast } from "sonner";
import AudioReactiveBackground from "../../components/audio/AudioReactiveBackground";
import { useProfileStore } from "../../stores/profileStore";
import { useSettingsStore } from "../../stores/settingsStore";
import { useSynthesisStore } from "../../stores/synthesisStore";
import { api } from "../../services/api";
import type { PersonaPreset } from "../../types";
import { createLogger } from "../../utils/logger";
import { getErrorMessage } from "../../utils/errors";

import ConsoleHeader from "./ConsoleHeader";
import BatchPanel from "./BatchPanel";
import TextToSpeechPanel from "./TextToSpeechPanel";
import SpeechToSpeechPanel from "./SpeechToSpeechPanel";
import ActivityLog from "./ActivityLog";
import VoiceChannelCard from "./VoiceChannelCard";
import AudioControlPanel from "./AudioControlPanel";
import { useProviderCapabilities } from "../../hooks/useProviderCapabilities";
import type { BatchLineResult, SynthesisMode } from "./types";

const logger = createLogger("SynthesisLabPage");

function escapeXmlText(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function escapeXmlAttribute(value: string): string {
  return escapeXmlText(value).replace(/"/g, "&quot;").replace(/'/g, "&apos;");
}

export default function SynthesisLabPage() {
  const { profiles, fetchProfiles } = useProfileStore();
  const { defaultProvider, audioFormat } = useSettingsStore();
  const { lastResult, loading, synthesize, fetchHistory, history } =
    useSynthesisStore();

  // Text & profile
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

  // Speech-to-Speech
  const [synthesisMode, setSynthesisMode] = useState<SynthesisMode>("tts");
  const [stsFile, setStsFile] = useState<File | null>(null);
  const [stsLoading, setStsLoading] = useState(false);
  const [stsResult, setStsResult] = useState<{
    audio_url: string;
    duration_seconds: number | null;
  } | null>(null);
  const stsInputRef = useRef<HTMLInputElement>(null);

  // Studio state
  const [consoleOn, setConsoleOn] = useState(true);
  const vuLevels = { input: 42, output: 55, master: 65 };

  // STS blob URL — revoked on file change and on unmount to prevent memory leaks
  const [stsBlobUrl, setStsBlobUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!stsFile) {
      setStsBlobUrl(null);
      return;
    }
    const url = URL.createObjectURL(stsFile);
    setStsBlobUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [stsFile]);

  // Initial data fetch
  useEffect(() => {
    fetchProfiles();
    fetchHistory(20);
    api
      .listPresets()
      .then(({ presets: p }) => setPresets(p))
      .catch(() => {});
  }, []);

  // Auto-select first profile matching the user's default provider
  useEffect(() => {
    if (profileId || profiles.length === 0) return;
    const match = profiles.find((p) => p.provider_name === defaultProvider);
    if (match) setProfileId(match.id);
    else if (profiles.length > 0) setProfileId(profiles[0].id);
  }, [profiles, defaultProvider]);

  // Derived values
  const profileOptions = profiles.map((p) => ({
    value: p.id,
    label: `${p.name} (${p.provider_name})`,
  }));
  const selectedProfileData = profiles.find((p) => p.id === profileId);
  const isAzure = selectedProfileData?.provider_name === "azure_speech";
  const isElevenLabs = selectedProfileData?.provider_name === "elevenlabs";

  // Live capability lookup for the selected profile's provider. Controls
  // that depend on provider-level features (SSML, streaming, word
  // boundaries) should key off this instead of hard-coded provider names.
  const providerCaps = useProviderCapabilities(selectedProfileData?.provider_name ?? null);

  // ---- Handlers ----

  const handleProfileSelect = (id: string) => {
    setProfileId(id);
    if (id) logger.info("profile_selected", { profile_id: id });
  };

  const handlePresetSelect = (id: string) => {
    setPresetId(id);
    if (id) logger.info("preset_selected", { preset_id: id });
    const p = presets.find((pr) => pr.id === id);
    if (p) {
      setSpeed(p.speed);
      setPitch(p.pitch);
      setVolume(p.volume);
    }
  };

  const handleSynthesize = async () => {
    if (!text.trim() || !profileId) {
      toast.error("Enter text and select a profile");
      return;
    }
    logger.info("synthesis_start", {
      text_length: text.length,
      profile_id: profileId,
      emotion,
      output_format: outputFormat,
    });

    let finalText = text;
    let useSSML = false;
    if (isAzure && emotion) {
      const safeEmotion = escapeXmlAttribute(emotion);
      const safeText = escapeXmlText(text);
      finalText = `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US"><voice name=""><mstts:express-as style="${safeEmotion}">${safeText}</mstts:express-as></voice></speak>`;
      useSSML = true;
    }

    const elevenLabsSettings = isElevenLabs
      ? {
          stability,
          similarity_boost: similarityBoost,
          style,
          use_speaker_boost: speakerBoost,
        }
      : undefined;

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
    logger.info("sts_start", {
      profile_id: profileId,
      filename: stsFile.name,
    });
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
      const message = getErrorMessage(e) || "Speech-to-Speech failed";
      logger.error("sts_error", { error: message });
      toast.error(message, { duration: 8000 });
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
    logger.info("batch_synthesis_start", {
      lineCount: lines.length,
      profile_id: profileId,
    });
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
      logger.info("batch_synthesis_complete", {
        total: lines.length,
        success: successCount,
      });
      toast.success(`Batch complete: ${successCount}/${lines.length} succeeded`);
      fetchHistory(20);
    } catch (e: unknown) {
      const message = getErrorMessage(e);
      logger.error("batch_synthesis_error", { error: message });
      setBatchResults((prev) =>
        prev.map((r) =>
          r.status === "pending"
            ? { ...r, status: "error" as const, error: message }
            : r,
        ),
      );
      toast.error(message);
    } finally {
      setBatchLoading(false);
    }
  };

  const handlePreview = () => {
    const previewText = text.trim() ? text.slice(0, 50) : "Quick preview test.";
    synthesize({
      text: previewText,
      profile_id: profileId,
      speed,
      pitch,
      volume,
      output_format: outputFormat,
    });
  };

  // ---- Render ----

  return (
    <div className="relative min-h-screen">
      <AudioReactiveBackground intensity="medium" />

      <div className="relative z-10 space-y-8">
        <ConsoleHeader
          consoleOn={consoleOn}
          onToggleConsole={() => setConsoleOn(!consoleOn)}
          batchMode={batchMode}
          onSetBatchMode={setBatchMode}
          synthesisMode={synthesisMode}
          onSetSynthesisMode={setSynthesisMode}
          canPreview={
            !!profileId && !batchMode && synthesisMode === "tts"
          }
          onPreview={handlePreview}
          loading={loading}
          vuLevels={vuLevels}
        />

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          {/* Main Content Area */}
          <div className="xl:col-span-2 space-y-6">
            {batchMode ? (
              <BatchPanel
                batchText={batchText}
                onSetBatchText={setBatchText}
                batchLoading={batchLoading}
                batchProgress={batchProgress}
                batchResults={batchResults}
              />
            ) : (
              <>
                {synthesisMode === "tts" ? (
                  <TextToSpeechPanel
                    text={text}
                    onSetText={setText}
                    lastResult={lastResult}
                    providerName={selectedProfileData?.provider_name ?? null}
                  />
                ) : (
                  <SpeechToSpeechPanel
                    stsFile={stsFile}
                    onSetStsFile={setStsFile}
                    stsLoading={stsLoading}
                    stsResult={stsResult}
                    stsInputRef={stsInputRef}
                    stsBlobUrl={stsBlobUrl}
                  />
                )}

                {!batchMode && <ActivityLog history={history} />}
              </>
            )}
          </div>

          {/* Studio Control Panel */}
          <div className="space-y-6">
            <VoiceChannelCard
              profileId={profileId}
              onProfileSelect={handleProfileSelect}
              profileOptions={profileOptions}
              presetId={presetId}
              onPresetSelect={handlePresetSelect}
              presets={presets}
              outputFormat={outputFormat}
              onSetOutputFormat={setOutputFormat}
              synthesisMode={synthesisMode}
            />

            <AudioControlPanel
              synthesisMode={synthesisMode}
              batchMode={batchMode}
              batchText={batchText}
              speed={speed}
              onSetSpeed={setSpeed}
              pitch={pitch}
              onSetPitch={setPitch}
              volume={volume}
              onSetVolume={setVolume}
              isElevenLabs={isElevenLabs}
              stability={stability}
              onSetStability={setStability}
              similarityBoost={similarityBoost}
              onSetSimilarityBoost={setSimilarityBoost}
              speakerBoost={speakerBoost}
              onSetSpeakerBoost={setSpeakerBoost}
              isAzure={isAzure}
              emotion={emotion}
              onSetEmotion={setEmotion}
              capabilities={providerCaps.capabilities}
              loading={loading}
              batchLoading={batchLoading}
              stsLoading={stsLoading}
              stsFile={stsFile}
              profileId={profileId}
              text={text}
              onSynthesize={handleSynthesize}
              onBatchSynthesize={handleBatchSynthesize}
              onSpeechToSpeech={handleSpeechToSpeech}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
