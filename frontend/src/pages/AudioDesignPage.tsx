import { useEffect, useState, useRef, useCallback } from "react";
import {
  Upload,
  Trash2,
  Scissors,
  Combine,
  Wand2,
  Sparkles,
  Download,
  Music,
  Search,
  Radio,
  Mic,
  AudioLines,
  FileAudio,
  Settings2,
  BarChart3,
  AlertCircle,
  CheckSquare,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "../components/ui/Button";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import { Slider } from "../components/ui/Slider";
import { AudioTimeline, type Region } from "../components/audio/AudioTimeline";
import { useAudioDesignStore } from "../stores/audioDesignStore";
import { useProviderStore } from "../stores/providerStore";
import { api } from "../services/api";
import { createLogger } from "../utils/logger";

const logger = createLogger("AudioDesignPage");

const EXPORT_FORMATS = [
  { value: "wav", label: "WAV (lossless)" },
  { value: "mp3", label: "MP3" },
  { value: "ogg", label: "OGG Vorbis" },
  { value: "flac", label: "FLAC (lossless)" },
] as const;

const SAMPLE_RATES = [
  { value: "", label: "Original" },
  { value: "8000", label: "8 kHz (telephone)" },
  { value: "16000", label: "16 kHz (speech)" },
  { value: "22050", label: "22.05 kHz" },
  { value: "44100", label: "44.1 kHz (CD)" },
  { value: "48000", label: "48 kHz (studio)" },
] as const;

function fmtRate(rate: number): string {
  return rate >= 1000 ? `${(rate / 1000).toFixed(1)}k` : String(rate);
}

export default function AudioDesignPage() {
  const {
    clips,
    selectedClipId,
    analysis,
    processingEngine,
    effects,
    exportFormat,
    exportSampleRate,
    loading,
    processing,
    error,
    fetchFiles,
    uploadClip,
    removeClip,
    trimClip,
    concatClips,
    applyEffects,
    analyzeClip,
    isolateClip,
    exportClip,
    setSelectedClip,
    setProcessingEngine,
    updateEffect,
    setExportFormat,
    setExportSampleRate,
    clearError,
  } = useAudioDesignStore();

  const { providers, fetchProviders } = useProviderStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [region, setRegion] = useState<Region | null>(null);
  const [selectedForConcat, setSelectedForConcat] = useState<Set<string>>(new Set());
  const [crossfadeMs, setCrossfadeMs] = useState(0);
  const [voiceDesignDesc, setVoiceDesignDesc] = useState("");
  const [soundEffectDesc, setSoundEffectDesc] = useState("");
  const [soundEffectDuration, setSoundEffectDuration] = useState(5);
  const [s2sVoiceId, setS2sVoiceId] = useState("");
  const [designingVoice, setDesigningVoice] = useState(false);
  const [generatingEffect, setGeneratingEffect] = useState(false);
  const [convertingVoice, setConvertingVoice] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [voicePreviews, setVoicePreviews] = useState<{ voice_id: string; audio_base64: string }[]>([]);

  const selectedClip = clips.find((c) => c.file_id === selectedClipId);
  const elevenlabsProvider = providers.find((p) => p.id === "elevenlabs");
  const isElevenLabsAvailable = elevenlabsProvider?.enabled ?? false;
  const elevenlabsHealthy = elevenlabsProvider?.health?.healthy;

  useEffect(() => {
    fetchFiles();
    fetchProviders();
  }, [fetchFiles, fetchProviders]);

  const handleFileUpload = useCallback(async (files: FileList | null) => {
    if (!files) return;
    logger.info("file_upload_start", { count: files.length });
    for (const file of Array.from(files)) {
      try {
        await uploadClip(file);
        toast.success(`Uploaded: ${file.name}`);
        logger.info("file_uploaded", { name: file.name, size: file.size });
      } catch {
        toast.error(`Failed to upload: ${file.name}`);
      }
    }
  }, [uploadClip]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      handleFileUpload(e.dataTransfer.files);
    },
    [handleFileUpload],
  );

  const handleTrim = useCallback(async () => {
    if (!selectedClipId || !region) return;
    logger.info("trim_start", { fileId: selectedClipId, start: region.start, end: region.end });
    try {
      await trimClip(selectedClipId, region.start, region.end);
      toast.success("Audio trimmed — new clip created");
      setRegion(null);
    } catch {
      toast.error("Trim failed");
    }
  }, [selectedClipId, region, trimClip]);

  const handleConcat = useCallback(async () => {
    const ids = Array.from(selectedForConcat);
    if (ids.length < 2) {
      toast.error("Select at least 2 clips to join");
      return;
    }
    logger.info("concat_start", { fileIds: ids, crossfadeMs });
    try {
      await concatClips(ids, crossfadeMs);
      toast.success("Clips joined — new clip created");
      setSelectedForConcat(new Set());
    } catch {
      toast.error("Join failed");
    }
  }, [selectedForConcat, concatClips, crossfadeMs]);

  const handleApplyEffects = useCallback(async () => {
    if (!selectedClipId) return;
    logger.info("effects_apply_start", { fileId: selectedClipId, effects: effects.filter((e) => e.enabled).map((e) => e.type) });
    try {
      await applyEffects(selectedClipId);
      toast.success("Effects applied — new clip created");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Effects failed");
    }
  }, [selectedClipId, applyEffects, effects]);

  const handleAnalyze = useCallback(async () => {
    if (!selectedClipId) return;
    logger.info("analyze_start", { fileId: selectedClipId });
    try {
      await analyzeClip(selectedClipId);
      toast.success("Analysis complete");
    } catch {
      toast.error("Analysis failed");
    }
  }, [selectedClipId, analyzeClip]);

  const handleIsolate = useCallback(async () => {
    if (!selectedClipId) return;
    logger.info("isolate_start", { fileId: selectedClipId });
    try {
      await isolateClip(selectedClipId);
      toast.success("Audio isolation complete — new clip created");
    } catch {
      toast.error("Audio isolation failed — is ElevenLabs configured?");
    }
  }, [selectedClipId, isolateClip]);

  const handleExport = useCallback(async () => {
    if (!selectedClipId) return;
    logger.info("export_start", { fileId: selectedClipId, format: exportFormat, sampleRate: exportSampleRate });
    try {
      const result = await exportClip(selectedClipId);
      const fullUrl = api.fullAudioUrl(result.audio_url);
      const a = document.createElement("a");
      a.href = fullUrl;
      a.download = result.filename;
      a.click();
      toast.success(`Exported as ${exportFormat.toUpperCase()}`);
      logger.info("export_complete", { format: exportFormat, filename: result.filename });
    } catch {
      toast.error("Export failed");
    }
  }, [selectedClipId, exportClip, exportFormat, exportSampleRate]);

  const handleDeleteClip = useCallback(async (fileId: string) => {
    logger.info("delete_clip", { fileId });
    await removeClip(fileId);
    setConfirmDelete(null);
    toast.success("Clip deleted");
  }, [removeClip]);

  const handleSpeechToSpeech = useCallback(async () => {
    if (!selectedClipId || !s2sVoiceId) return;
    setConvertingVoice(true);
    logger.info("s2s_start", { fileId: selectedClipId, voiceId: s2sVoiceId });
    try {
      const clip = selectedClip;
      if (!clip) return;
      // Fetch the clip audio, send to S2S, then re-import the result as a new clip
      const response = await fetch(api.fullAudioUrl(clip.audio_url));
      if (!response.ok) throw new Error(`Failed to fetch source audio: ${response.status}`);
      const blob = await response.blob();
      const file = new File([blob], clip.filename, { type: "audio/wav" });
      const result = await api.speechToSpeech(file, s2sVoiceId, "elevenlabs");
      // Download converted audio and add to clips
      const convertedResp = await fetch(api.fullAudioUrl(result.audio_url));
      if (!convertedResp.ok) throw new Error(`Failed to fetch converted audio: ${convertedResp.status}`);
      const convertedBlob = await convertedResp.blob();
      const convertedFile = new File([convertedBlob], `s2s_${clip.filename}`, { type: "audio/mp3" });
      await uploadClip(convertedFile);
      toast.success("Voice conversion complete — added to clips");
    } catch {
      toast.error("Speech-to-speech failed");
    } finally {
      setConvertingVoice(false);
    }
  }, [selectedClipId, s2sVoiceId, selectedClip, uploadClip]);

  const handleDesignVoice = useCallback(async () => {
    if (!voiceDesignDesc.trim()) return;
    setDesigningVoice(true);
    logger.info("voice_design_start", { description: voiceDesignDesc.slice(0, 80) });
    try {
      const result = await api.designVoice(voiceDesignDesc);
      setVoicePreviews(result.previews);
      toast.success(`Generated ${result.previews.length} voice preview(s)`);
    } catch {
      toast.error("Voice design failed");
    } finally {
      setDesigningVoice(false);
    }
  }, [voiceDesignDesc]);

  const handleGenerateSoundEffect = useCallback(async () => {
    if (!soundEffectDesc.trim()) return;
    setGeneratingEffect(true);
    logger.info("sfx_start", { description: soundEffectDesc.slice(0, 80), duration: soundEffectDuration });
    try {
      const result = await api.generateSoundEffect(soundEffectDesc, soundEffectDuration);
      // Download the generated SFX and add to clips
      const sfxResp = await fetch(api.fullAudioUrl(result.audio_url));
      if (!sfxResp.ok) throw new Error(`Failed to fetch sound effect: ${sfxResp.status}`);
      const sfxBlob = await sfxResp.blob();
      const sfxFile = new File([sfxBlob], `sfx_${soundEffectDesc.slice(0, 20).replace(/\s+/g, "_")}.mp3`, { type: "audio/mp3" });
      await uploadClip(sfxFile);
      toast.success("Sound effect generated — added to clips");
    } catch {
      toast.error("Sound effect generation failed");
    } finally {
      setGeneratingEffect(false);
    }
  }, [soundEffectDesc, soundEffectDuration, uploadClip]);

  const handleSelectAll = useCallback(() => {
    if (selectedForConcat.size === clips.length) {
      setSelectedForConcat(new Set());
    } else {
      setSelectedForConcat(new Set(clips.map((c) => c.file_id)));
    }
  }, [clips, selectedForConcat]);

  const toggleConcatSelect = (fileId: string) => {
    setSelectedForConcat((prev) => {
      const next = new Set(prev);
      if (next.has(fileId)) next.delete(fileId);
      else next.add(fileId);
      return next;
    });
  };

  const audioSrc = selectedClip ? api.fullAudioUrl(selectedClip.audio_url) : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Audio Design Studio</h1>
          <p className="text-sm text-[var(--color-text-secondary)]">
            Import, enhance, trim, join, and export audio files
          </p>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*"
            multiple
            className="hidden"
            onChange={(e) => handleFileUpload(e.target.files)}
            aria-label="Import audio files"
          />
          <Button variant="primary" onClick={() => fileInputRef.current?.click()} disabled={loading}>
            <Upload className="h-4 w-4 mr-2" />
            {loading ? "Uploading..." : "Import Audio"}
          </Button>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-900/20 px-4 py-3" role="alert">
          <AlertCircle className="h-5 w-5 text-red-500 shrink-0" />
          <span className="flex-1 text-sm text-red-800 dark:text-red-200">{error}</span>
          <button onClick={clearError} className="text-red-500 hover:text-red-700" aria-label="Dismiss error">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Main layout */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Left — Main content area */}
        <div className="flex-1 min-w-0 space-y-4">
          {/* Drop zone (when no clips) */}
          {clips.length === 0 && !loading && (
            <div
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              className="flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-[var(--color-border)] p-12 text-[var(--color-text-secondary)] hover:border-primary-400 hover:bg-primary-50/50 dark:hover:bg-primary-900/10 transition-colors cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
              role="button"
              aria-label="Drop audio files here or click to browse"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click(); }}
            >
              <Upload className="h-10 w-10 opacity-50" />
              <p className="text-lg font-medium">Drop audio files here</p>
              <p className="text-sm">WAV, MP3, OGG, FLAC, M4A supported</p>
            </div>
          )}

          {/* Loading state */}
          {loading && clips.length === 0 && (
            <div className="flex items-center justify-center h-32 text-sm text-[var(--color-text-secondary)]">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-500 border-t-transparent mr-3" />
              Loading audio files...
            </div>
          )}

          {/* Timeline */}
          {selectedClip && audioSrc && (
            <CollapsiblePanel
              title="Waveform Timeline"
              icon={<AudioLines className="h-4 w-4 text-primary-500" />}
              actions={
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleTrim}
                    disabled={!region || processing}
                    title="Trim to selection"
                    aria-label="Trim audio to selected region"
                  >
                    <Scissors className="h-3.5 w-3.5 mr-1" />
                    Trim
                  </Button>
                </div>
              }
            >
              <AudioTimeline
                src={audioSrc}
                onRegionChange={setRegion}
                onReady={(dur) => logger.info("timeline_loaded", { duration: dur })}
              />
            </CollapsiblePanel>
          )}

          {/* Clips list */}
          {clips.length > 0 && (
            <CollapsiblePanel
              title={`Audio Clips (${clips.length})`}
              icon={<FileAudio className="h-4 w-4 text-blue-500" />}
              actions={
                <div className="flex gap-1">
                  <Button variant="ghost" size="sm" onClick={handleSelectAll} title="Select all / none" aria-label={selectedForConcat.size === clips.length ? "Deselect all" : "Select all"}>
                    <CheckSquare className="h-3.5 w-3.5" />
                  </Button>
                  {selectedForConcat.size >= 2 && (
                    <Button variant="secondary" size="sm" onClick={handleConcat} disabled={processing}>
                      <Combine className="h-3.5 w-3.5 mr-1" />
                      Join ({selectedForConcat.size})
                    </Button>
                  )}
                </div>
              }
            >
              <div className="space-y-1" role="listbox" aria-label="Audio clips">
                {clips.map((clip) => (
                  <div
                    key={clip.file_id}
                    role="option"
                    aria-selected={clip.file_id === selectedClipId}
                    className={`flex items-center gap-3 rounded-lg px-3 py-2 cursor-pointer transition-colors ${
                      clip.file_id === selectedClipId
                        ? "bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800"
                        : "hover:bg-[var(--color-hover)] border border-transparent"
                    }`}
                    onClick={() => setSelectedClip(clip.file_id)}
                  >
                    <input
                      type="checkbox"
                      checked={selectedForConcat.has(clip.file_id)}
                      onChange={(e) => {
                        e.stopPropagation();
                        toggleConcatSelect(clip.file_id);
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="h-4 w-4 rounded accent-primary-500"
                      aria-label={`Select ${clip.original_filename} for joining`}
                    />
                    <Music className="h-4 w-4 text-[var(--color-text-secondary)] shrink-0" />
                    <span className="flex-1 text-sm truncate" title={clip.original_filename}>
                      {clip.original_filename}
                    </span>
                    <span className="text-xs text-[var(--color-text-secondary)] uppercase">{clip.format}</span>
                    <span className="text-xs text-[var(--color-text-secondary)]">{clip.duration_seconds.toFixed(1)}s</span>
                    <span className="text-xs text-[var(--color-text-secondary)]">{fmtRate(clip.sample_rate)}Hz</span>
                    {confirmDelete === clip.file_id ? (
                      <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                        <Button variant="danger" size="sm" onClick={() => handleDeleteClip(clip.file_id)} aria-label="Confirm delete">
                          Delete
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => setConfirmDelete(null)} aria-label="Cancel delete">
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setConfirmDelete(clip.file_id);
                        }}
                        aria-label={`Delete ${clip.original_filename}`}
                      >
                        <Trash2 className="h-3.5 w-3.5 text-red-500" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>

              {/* Crossfade slider (visible when 2+ selected for join) */}
              {selectedForConcat.size >= 2 && (
                <div className="mt-3 px-1">
                  <Slider
                    label="Crossfade"
                    id="crossfade-ms"
                    min={0}
                    max={2000}
                    step={50}
                    value={crossfadeMs}
                    onChange={(e) => setCrossfadeMs(Number(e.target.value))}
                    displayValue={crossfadeMs === 0 ? "None" : `${crossfadeMs}ms`}
                  />
                </div>
              )}

              {/* Drop zone for adding more files */}
              <div
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                className="mt-3 flex items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--color-border)] py-3 text-sm text-[var(--color-text-secondary)] hover:border-primary-400 transition-colors cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
                role="button"
                aria-label="Add more audio files"
              >
                <Upload className="h-4 w-4" />
                Drop more files or click to add
              </div>
            </CollapsiblePanel>
          )}

          {/* Quality Analysis */}
          {analysis && (
            <CollapsiblePanel
              title="Quality Analysis"
              icon={<BarChart3 className="h-4 w-4 text-green-500" />}
            >
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="text-center">
                  <div className={`text-2xl font-bold ${analysis.quality.score >= 70 ? "text-green-500" : analysis.quality.score >= 40 ? "text-yellow-500" : "text-red-500"}`}>
                    {analysis.quality.score.toFixed(0)}
                  </div>
                  <div className="text-xs text-[var(--color-text-secondary)]">Score / 100</div>
                </div>
                {analysis.quality.snr_db != null && (
                  <div className="text-center">
                    <div className="text-2xl font-bold">{analysis.quality.snr_db.toFixed(1)}</div>
                    <div className="text-xs text-[var(--color-text-secondary)]">SNR (dB)</div>
                  </div>
                )}
                {analysis.quality.rms_db != null && (
                  <div className="text-center">
                    <div className="text-2xl font-bold">{analysis.quality.rms_db.toFixed(1)}</div>
                    <div className="text-xs text-[var(--color-text-secondary)]">RMS (dB)</div>
                  </div>
                )}
                <div className="text-center">
                  <div className="text-2xl font-bold">{fmtRate(analysis.sample_rate)}</div>
                  <div className="text-xs text-[var(--color-text-secondary)]">Sample Rate</div>
                </div>
              </div>

              {analysis.pitch_mean != null && (
                <div className="mt-3 grid grid-cols-3 gap-3 text-sm">
                  <div><span className="text-[var(--color-text-secondary)]">Pitch:</span> {analysis.pitch_mean.toFixed(0)} Hz</div>
                  <div><span className="text-[var(--color-text-secondary)]">Energy:</span> {analysis.energy_mean?.toFixed(4)}</div>
                  <div><span className="text-[var(--color-text-secondary)]">Spectral:</span> {analysis.spectral_centroid_mean?.toFixed(0)} Hz</div>
                </div>
              )}

              {analysis.quality.issues.length > 0 && (
                <div className="mt-3 space-y-1">
                  {analysis.quality.issues.map((issue, i) => (
                    <p key={i} className={`text-xs ${issue.severity === "error" ? "text-red-500" : issue.severity === "warning" ? "text-yellow-600 dark:text-yellow-400" : "text-[var(--color-text-secondary)]"}`}>
                      {issue.message}
                    </p>
                  ))}
                </div>
              )}
            </CollapsiblePanel>
          )}
        </div>

        {/* Right — Sidebar */}
        <div className="w-full lg:w-80 xl:w-96 flex-shrink-0 space-y-4">
          {/* Processing Engine */}
          <CollapsiblePanel
            title="Processing Engine"
            icon={<Radio className="h-4 w-4 text-purple-500" />}
          >
            <div className="space-y-2">
              <label className="flex items-center gap-3 cursor-pointer rounded-lg px-3 py-2 hover:bg-[var(--color-hover)] transition-colors">
                <input
                  type="radio"
                  name="engine"
                  checked={processingEngine === "local"}
                  onChange={() => { setProcessingEngine("local"); logger.info("engine_changed", { engine: "local" }); }}
                  className="accent-primary-500"
                />
                <div>
                  <div className="text-sm font-medium">Local (Built-in)</div>
                  <div className="text-xs text-[var(--color-text-secondary)]">Noise reduction, normalize, trim, gain</div>
                </div>
              </label>
              <label className={`flex items-center gap-3 cursor-pointer rounded-lg px-3 py-2 hover:bg-[var(--color-hover)] transition-colors ${!isElevenLabsAvailable ? "opacity-50" : ""}`}>
                <input
                  type="radio"
                  name="engine"
                  checked={processingEngine === "elevenlabs"}
                  onChange={() => { setProcessingEngine("elevenlabs"); logger.info("engine_changed", { engine: "elevenlabs" }); }}
                  disabled={!isElevenLabsAvailable}
                  className="accent-primary-500"
                />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">ElevenLabs</span>
                    {isElevenLabsAvailable && (
                      <span className={`inline-block h-2 w-2 rounded-full ${elevenlabsHealthy === true ? "bg-green-500" : elevenlabsHealthy === false ? "bg-red-500" : "bg-gray-400"}`} title={elevenlabsHealthy === true ? "Online" : elevenlabsHealthy === false ? "Offline" : "Unknown"} />
                    )}
                  </div>
                  <div className="text-xs text-[var(--color-text-secondary)]">
                    {isElevenLabsAvailable
                      ? "AI isolation, voice conversion, voice design, SFX"
                      : "Not configured — enable in Providers"}
                  </div>
                </div>
              </label>
            </div>
          </CollapsiblePanel>

          {/* Effects Chain */}
          <CollapsiblePanel
            title="Effects Chain"
            icon={<Settings2 className="h-4 w-4 text-orange-500" />}
            actions={
              <Button
                variant="primary"
                size="sm"
                onClick={handleApplyEffects}
                disabled={!selectedClipId || processing || !effects.some((e) => e.enabled)}
              >
                {processing ? "Applying..." : "Apply"}
              </Button>
            }
          >
            <div className="space-y-4">
              {effects.map((effect, i) => (
                <div key={effect.type} className="space-y-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={effect.enabled}
                      onChange={(e) => {
                        updateEffect(i, { enabled: e.target.checked });
                        logger.info("effect_toggled", { type: effect.type, enabled: e.target.checked });
                      }}
                      className="h-4 w-4 rounded accent-primary-500"
                      aria-label={`Enable ${effect.type.replace(/_/g, " ")}`}
                    />
                    <span className="text-sm font-medium capitalize">
                      {effect.type.replace(/_/g, " ")}
                    </span>
                  </label>
                  {effect.enabled && effect.type === "noise_reduction" && (
                    <Slider
                      label="Strength"
                      id={`nr-strength-${i}`}
                      min={0.1}
                      max={1.0}
                      step={0.05}
                      value={effect.strength ?? 0.5}
                      onChange={(e) => updateEffect(i, { strength: Number(e.target.value) })}
                      displayValue={`${((effect.strength ?? 0.5) * 100).toFixed(0)}%`}
                    />
                  )}
                  {effect.enabled && effect.type === "trim_silence" && (
                    <Slider
                      label="Threshold"
                      id={`ts-threshold-${i}`}
                      min={-60}
                      max={-20}
                      step={1}
                      value={effect.threshold_db ?? -40}
                      onChange={(e) => updateEffect(i, { threshold_db: Number(e.target.value) })}
                      displayValue={`${effect.threshold_db ?? -40} dB`}
                    />
                  )}
                  {effect.enabled && effect.type === "gain" && (
                    <Slider
                      label="Gain"
                      id={`gain-db-${i}`}
                      min={-20}
                      max={20}
                      step={0.5}
                      value={effect.gain_db ?? 0}
                      onChange={(e) => updateEffect(i, { gain_db: Number(e.target.value) })}
                      displayValue={`${(effect.gain_db ?? 0) > 0 ? "+" : ""}${effect.gain_db ?? 0} dB`}
                    />
                  )}
                </div>
              ))}
            </div>
          </CollapsiblePanel>

          {/* ElevenLabs Tools (only when ElevenLabs engine selected) */}
          {processingEngine === "elevenlabs" && isElevenLabsAvailable && (
            <CollapsiblePanel
              title="ElevenLabs Tools"
              icon={<Sparkles className="h-4 w-4 text-yellow-500" />}
            >
              <div className="space-y-4">
                {/* Audio Isolation */}
                <div>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleIsolate}
                    disabled={!selectedClipId || processing}
                    className="w-full"
                    aria-label="Run AI audio isolation on selected clip"
                  >
                    <Wand2 className="h-4 w-4 mr-2" />
                    {processing ? "Isolating..." : "Audio Isolation"}
                  </Button>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-1">
                    Remove background noise using AI
                  </p>
                </div>

                {/* Speech-to-Speech */}
                <div className="space-y-2">
                  <label htmlFor="s2s-voice-id" className="text-sm font-medium">Speech-to-Speech</label>
                  <input
                    id="s2s-voice-id"
                    type="text"
                    placeholder="Target ElevenLabs voice ID"
                    value={s2sVoiceId}
                    onChange={(e) => setS2sVoiceId(e.target.value)}
                    className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-1.5 text-sm"
                    aria-label="Target ElevenLabs voice ID for speech-to-speech conversion"
                  />
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleSpeechToSpeech}
                    disabled={!selectedClipId || !s2sVoiceId || convertingVoice}
                    className="w-full"
                  >
                    <Mic className="h-4 w-4 mr-2" />
                    {convertingVoice ? "Converting..." : "Convert Voice"}
                  </Button>
                </div>

                {/* Voice Design */}
                <div className="space-y-2">
                  <label htmlFor="voice-design-desc" className="text-sm font-medium">Voice Design</label>
                  <textarea
                    id="voice-design-desc"
                    placeholder="Describe the voice you want..."
                    value={voiceDesignDesc}
                    onChange={(e) => setVoiceDesignDesc(e.target.value)}
                    rows={2}
                    className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-1.5 text-sm resize-none"
                    aria-label="Natural language voice description for AI voice generation"
                  />
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleDesignVoice}
                    disabled={!voiceDesignDesc.trim() || designingVoice}
                    className="w-full"
                  >
                    <Sparkles className="h-4 w-4 mr-2" />
                    {designingVoice ? "Designing..." : "Design Voice"}
                  </Button>
                  {voicePreviews.length > 0 && (
                    <div className="space-y-2 mt-2">
                      <div className="text-xs text-[var(--color-text-secondary)]">{voicePreviews.length} preview(s):</div>
                      {voicePreviews.map((preview, i) => (
                        <div key={preview.voice_id} className="flex items-center gap-2 rounded border border-[var(--color-border)] p-2">
                          <audio
                            src={`data:audio/mp3;base64,${preview.audio_base64}`}
                            controls
                            className="h-8 flex-1"
                          />
                          <span className="text-xs text-[var(--color-text-secondary)] shrink-0">#{i + 1}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Sound Effects */}
                <div className="space-y-2">
                  <label htmlFor="sfx-desc" className="text-sm font-medium">Sound Effects</label>
                  <input
                    id="sfx-desc"
                    type="text"
                    placeholder="Describe the sound effect..."
                    value={soundEffectDesc}
                    onChange={(e) => setSoundEffectDesc(e.target.value)}
                    className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-1.5 text-sm"
                    aria-label="Text description for AI sound effect generation"
                  />
                  <Slider
                    label="Duration"
                    id="sfx-duration"
                    min={1}
                    max={22}
                    step={0.5}
                    value={soundEffectDuration}
                    onChange={(e) => setSoundEffectDuration(Number(e.target.value))}
                    displayValue={`${soundEffectDuration}s`}
                  />
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleGenerateSoundEffect}
                    disabled={!soundEffectDesc.trim() || generatingEffect}
                    className="w-full"
                  >
                    <Music className="h-4 w-4 mr-2" />
                    {generatingEffect ? "Generating..." : "Generate SFX"}
                  </Button>
                </div>
              </div>
            </CollapsiblePanel>
          )}

          {/* Analyze */}
          <CollapsiblePanel
            title="Analyze"
            icon={<Search className="h-4 w-4 text-teal-500" />}
          >
            <Button
              variant="secondary"
              size="sm"
              onClick={handleAnalyze}
              disabled={!selectedClipId || processing}
              className="w-full"
              aria-label="Run quality and spectral analysis on selected clip"
            >
              <BarChart3 className="h-4 w-4 mr-2" />
              {processing ? "Analyzing..." : "Run Quality Analysis"}
            </Button>
            <p className="text-xs text-[var(--color-text-secondary)] mt-1">
              SNR, RMS, clipping, silence ratio, pitch, spectral analysis
            </p>
          </CollapsiblePanel>

          {/* Export */}
          <CollapsiblePanel
            title="Export"
            icon={<Download className="h-4 w-4 text-green-500" />}
          >
            <div className="space-y-3">
              <div>
                <label htmlFor="export-format" className="text-sm font-medium text-[var(--color-text)]">Format</label>
                <select
                  id="export-format"
                  value={exportFormat}
                  onChange={(e) => { setExportFormat(e.target.value); logger.info("export_format_changed", { format: e.target.value }); }}
                  className="mt-1 w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-1.5 text-sm"
                >
                  {EXPORT_FORMATS.map((f) => (
                    <option key={f.value} value={f.value}>{f.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="export-sample-rate" className="text-sm font-medium text-[var(--color-text)]">Sample Rate</label>
                <select
                  id="export-sample-rate"
                  value={exportSampleRate ?? ""}
                  onChange={(e) => setExportSampleRate(e.target.value ? Number(e.target.value) : null)}
                  className="mt-1 w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-1.5 text-sm"
                >
                  {SAMPLE_RATES.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
              </div>
              <Button
                variant="primary"
                onClick={handleExport}
                disabled={!selectedClipId || processing}
                className="w-full"
              >
                <Download className="h-4 w-4 mr-2" />
                {processing ? "Exporting..." : "Export Audio"}
              </Button>
            </div>
          </CollapsiblePanel>
        </div>
      </div>
    </div>
  );
}
