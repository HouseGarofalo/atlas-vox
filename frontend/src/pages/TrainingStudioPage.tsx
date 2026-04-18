import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Music, Cpu, History, AlertTriangle, Play, Pause, Search, CheckCircle, Wand2, Sparkles, ClipboardCopy } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Select } from "../components/ui/Select";
import { ProgressBar } from "../components/ui/ProgressBar";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import { AudioRecorder, FileUploader } from "../components/audio/AudioRecorder";
import { useProfileStore } from "../stores/profileStore";
import { useTrainingStore } from "../stores/trainingStore";
import { useTrainingProgress } from "../hooks/useWebSocket";
import { api } from "../services/api";
import type { AudioSample, QualityResult, ReadinessResult } from "../types";
import { createLogger } from "../utils/logger";

const logger = createLogger("TrainingStudioPage");

export default function TrainingStudioPage() {
  const [searchParams] = useSearchParams();
  const { profiles, fetchProfiles } = useProfileStore();
  const { jobs, fetchJobs, startTraining, cancelJob } = useTrainingStore();
  const [selectedProfile, setSelectedProfile] = useState(searchParams.get("profile") || "");
  const [samples, setSamples] = useState<AudioSample[]>([]);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [preprocessing, setPreprocessing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [playingSampleId, setPlayingSampleId] = useState<string | null>(null);
  const [sampleQualities, setSampleQualities] = useState<Record<string, QualityResult>>({});
  const [checkingQuality, setCheckingQuality] = useState<string | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResult | null>(null);
  const [loadingReadiness, setLoadingReadiness] = useState(false);
  const [enhancing, setEnhancing] = useState<string | null>(null);
  const [enhancingAll, setEnhancingAll] = useState(false);
  // SL-29 active-learning recommender
  const [recommendations, setRecommendations] = useState<{
    text: string; fills_gaps: string[]; gap_fill_count: number; priority: number;
  }[]>([]);
  const [recommendationMethod, setRecommendationMethod] = useState<"phonemizer" | "bigram_approx" | null>(null);
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);
  const { progress, connectionStatus, connectionBanner } = useTrainingProgress(activeJobId);

  useEffect(() => {
    fetchProfiles().catch(() => toast.error("Failed to load profiles"));
    fetchJobs().catch(() => toast.error("Failed to load training jobs"));
  }, []);
  useEffect(() => {
    if (selectedProfile) {
      logger.info("profile_selected", { profile_id: selectedProfile });
      loadSamples();
      loadRecommendations();
    } else {
      setRecommendations([]);
      setRecommendationMethod(null);
    }
  }, [selectedProfile]);

  // When training completes, refresh the profile list so status updates from "training" to "ready"
  useEffect(() => {
    if (progress && ["DONE", "FAILURE"].includes(progress.state)) {
      fetchProfiles().catch(() => {});
      fetchJobs().catch(() => {});
      if (progress.state === "DONE") {
        toast.success("Training completed! Voice is ready for synthesis.");
      } else if (progress.error) {
        toast.error(`Training failed: ${progress.error}`);
      }
    }
  }, [progress?.state]);

  const loadSamples = async () => {
    try { const { samples: s } = await api.listSamples(selectedProfile); setSamples(s); } catch { setSamples([]); }
  };

  /**
   * Fetch active-learning recommendations (SL-29). Refreshed when the
   * profile changes AND when new samples are uploaded (the recommender
   * excludes already-recorded sentences).
   */
  const loadRecommendations = useCallback(async () => {
    if (!selectedProfile) return;
    setLoadingRecommendations(true);
    try {
      const res = await api.getRecommendedSamples(selectedProfile, 10);
      setRecommendations(res.recommendations);
      setRecommendationMethod(res.method);
    } catch (err) {
      logger.warn("recommendations_failed", { error: String(err) });
      setRecommendations([]);
      setRecommendationMethod(null);
    } finally {
      setLoadingRecommendations(false);
    }
  }, [selectedProfile]);

  const handleCopySentence = (text: string) => {
    navigator.clipboard?.writeText(text).then(
      () => toast.success("Copied to clipboard"),
      () => toast.error("Clipboard unavailable"),
    );
  };

  const loadReadiness = useCallback(async () => {
    if (!selectedProfile) return;
    setLoadingReadiness(true);
    try {
      const r = await api.getTrainingReadiness(selectedProfile);
      setReadiness(r);
    } catch {
      setReadiness(null);
    } finally {
      setLoadingReadiness(false);
    }
  }, [selectedProfile]);

  useEffect(() => {
    if (selectedProfile && samples.length > 0) {
      loadReadiness();
    } else {
      setReadiness(null);
    }
  }, [selectedProfile, samples.length, loadReadiness]);

  const handleCheckQuality = async (sampleId: string) => {
    setCheckingQuality(sampleId);
    try {
      const result = await api.getSampleQuality(selectedProfile, sampleId);
      setSampleQualities((prev) => ({ ...prev, [sampleId]: result }));
      if (result.passed) {
        toast.success("Sample passed quality check");
      } else {
        toast.warning(`Quality issues found (score: ${result.score.toFixed(0)}%)`);
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Quality check failed";
      toast.error(message);
    } finally {
      setCheckingQuality(null);
    }
  };

  const handleEnhance = async (sampleId: string) => {
    setEnhancing(sampleId);
    try {
      await api.enhanceSample(selectedProfile, sampleId);
      toast.success("Sample enhanced successfully");
      await loadSamples();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Enhancement failed";
      toast.error(message);
    } finally {
      setEnhancing(null);
    }
  };

  const handleEnhanceAll = async () => {
    if (samples.length === 0) return;
    setEnhancingAll(true);
    let enhanced = 0;
    let failed = 0;
    for (const sample of samples) {
      try {
        await api.enhanceSample(selectedProfile, sample.id);
        enhanced++;
      } catch {
        failed++;
      }
    }
    await loadSamples();
    setEnhancingAll(false);
    if (enhanced > 0) toast.success(`Enhanced ${enhanced} sample(s)`);
    if (failed > 0) toast.error(`${failed} sample(s) failed to enhance`);
  };

  const handlePlaySample = (sampleId: string, _filename: string) => {
    if (playingSampleId === sampleId) {
      setPlayingSampleId(null);
    } else {
      setPlayingSampleId(sampleId);
    }
  };

  const handleUpload = async (files: File[]) => {
    if (!selectedProfile) { toast.error("Select a profile first"); return; }
    const totalSize = files.reduce((sum, f) => sum + f.size, 0);
    logger.info("file_upload", { count: files.length, total_bytes: totalSize });
    setUploading(true);
    try {
      await api.uploadSamples(selectedProfile, files);
      toast.success(`${files.length} file(s) uploaded and analyzed`);
      logger.info("file_upload_complete", { count: files.length });
      await loadSamples();
      // Refresh recommendations — newly-recorded sentences now get excluded
      // and remaining gaps may have shrunk, so the next-N suggestions change.
      void loadRecommendations();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Upload failed";
      logger.error("file_upload_error", { error: message });
      toast.error(message);
    } finally {
      setUploading(false);
    }
  };

  const handleRecord = async (blob: Blob, filename: string) => {
    logger.info("recording_complete", { filename, size_bytes: blob.size });
    await handleUpload([new File([blob], filename, { type: blob.type })]);
  };

  const handlePreprocess = async () => {
    logger.info("preprocess_start", { profile_id: selectedProfile });
    setPreprocessing(true);
    try {
      const r = await api.preprocessSamples(selectedProfile);
      toast.success(r.message || "Preprocessing started");
      // Poll for completion: preprocessing is async via Celery, so we wait
      // a bit then refresh the sample list to show updated status.
      if (r.task_id) {
        setTimeout(async () => {
          await loadSamples();
          setPreprocessing(false);
          toast.success("Samples refreshed");
        }, 5000);
      } else {
        await loadSamples();
        setPreprocessing(false);
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Preprocessing failed";
      logger.error("preprocess_error", { error: message });
      toast.error(message);
      setPreprocessing(false);
    }
  };

  const handleStartTraining = async () => {
    logger.info("training_start", { profile_id: selectedProfile });
    try {
      const job = await startTraining(selectedProfile);
      setActiveJobId(job.id);
      logger.info("training_started", { job_id: job.id });
      toast.success("Training started");
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to start training";
      logger.error("training_start_error", { error: message });
      toast.error(message);
    }
  };

  const profileOptions = profiles.map((p) => ({ value: p.id, label: `${p.name} (${p.provider_name})` }));
  const profileJobs = jobs.filter((j) => j.profile_id === selectedProfile);
  const selectedProfileData = profiles.find((p) => p.id === selectedProfile);
  const isAzure = selectedProfileData?.provider_name === "azure_speech";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Training Studio</h1>
      {activeJobId && connectionBanner && (
        <div
          role="status"
          aria-live="polite"
          data-testid="training-connection-banner"
          data-connection-status={connectionStatus}
          className={`flex items-center gap-3 rounded-lg border p-3 text-sm ${
            connectionStatus === "failed"
              ? "border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] text-[var(--color-danger)]"
              : "border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]"
          }`}
        >
          <span
            className={`h-2 w-2 rounded-full ${
              connectionStatus === "polling"
                ? "bg-amber-400 animate-pulse"
                : connectionStatus === "reconnecting"
                  ? "bg-amber-400 animate-pulse"
                  : "bg-red-400"
            }`}
          />
          <span>{connectionBanner}</span>
        </div>
      )}
      <Select label="Voice Profile" value={selectedProfile} onChange={(e) => setSelectedProfile(e.target.value)} options={[{ value: "", label: "Select a profile..." }, ...profileOptions]} />

      {selectedProfile && (
        <>
          <CollapsiblePanel
            title={`Audio Samples (${samples.length})`}
            icon={<Music className="h-4 w-4 text-primary-500" />}
          >
            <div className="space-y-4">
              <FileUploader onFiles={handleUpload} />
              <AudioRecorder onRecorded={handleRecord} />
              {uploading && (
                <p className="text-sm text-[var(--color-text-secondary)]">Uploading and analyzing files...</p>
              )}
              {samples.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] px-2">
                    <span>Total: {samples.reduce((sum, s) => sum + (s.duration_seconds || 0), 0).toFixed(1)}s across {samples.length} file(s)</span>
                    <Button variant="secondary" size="sm" onClick={handleEnhanceAll} loading={enhancingAll}>
                      <Wand2 className="h-3.5 w-3.5" /> Enhance All
                    </Button>
                  </div>
                  {samples.map((s) => (
                    <div key={s.id} className="rounded border border-[var(--color-border)]">
                      <div className="flex items-center gap-3 p-2">
                        <button
                          onClick={() => handlePlaySample(s.id, s.filename)}
                          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary-500 text-white hover:bg-primary-600 transition-colors"
                          aria-label={playingSampleId === s.id ? "Stop" : "Play"}
                        >
                          {playingSampleId === s.id ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3 ml-0.5" />}
                        </button>
                        <span className="flex-1 text-sm truncate">{s.original_filename}</span>
                        {sampleQualities[s.id] && (
                          <span
                            className={`inline-block h-2.5 w-2.5 rounded-full ${
                              sampleQualities[s.id].score >= 80 ? "bg-green-500" :
                              sampleQualities[s.id].score >= 50 ? "bg-yellow-500" :
                              "bg-red-500"
                            }`}
                            title={`Quality: ${sampleQualities[s.id].score.toFixed(0)}%`}
                          />
                        )}
                        <span className="text-xs text-[var(--color-text-secondary)] uppercase hidden sm:inline">{s.format}</span>
                        <span className="text-xs text-[var(--color-text-secondary)]">{s.duration_seconds ? `${s.duration_seconds.toFixed(1)}s` : "Pending"}</span>
                        <Badge status={s.preprocessed ? "ready" : "pending"} />
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEnhance(s.id)}
                          disabled={enhancing === s.id}
                          aria-label="Enhance sample"
                          title="Enhance (audio isolation)"
                        >
                          {enhancing === s.id ? (
                            <span className="text-xs">...</span>
                          ) : (
                            <Wand2 className="h-3 w-3" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCheckQuality(s.id)}
                          disabled={checkingQuality === s.id}
                          aria-label="Check quality"
                        >
                          {checkingQuality === s.id ? (
                            <span className="text-xs">...</span>
                          ) : (
                            <Search className="h-3 w-3" />
                          )}
                        </Button>
                      </div>
                      {playingSampleId === s.id && (
                        <div className="px-2 pb-2">
                          <audio
                            src={api.audioUrl(s.filename)}
                            autoPlay
                            controls
                            onEnded={() => setPlayingSampleId(null)}
                            className="w-full h-8"
                          />
                        </div>
                      )}
                      {sampleQualities[s.id] && sampleQualities[s.id].issues.length > 0 && (
                        <div className="px-2 pb-2 space-y-1">
                          {sampleQualities[s.id].issues.map((issue, i) => (
                            <p key={i} className={`text-xs ${issue.severity === "error" ? "text-red-500" : "text-yellow-600 dark:text-yellow-400"}`}>
                              {issue.message}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {samples.some((s) => !s.preprocessed) && (
                <Button variant="secondary" onClick={handlePreprocess} loading={preprocessing}>
                  Preprocess Samples
                </Button>
              )}
            </div>
          </CollapsiblePanel>

          {isAzure && (
            <div className="flex items-start gap-3 rounded-lg border border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] p-4">
              <AlertTriangle className="h-5 w-5 shrink-0 text-[var(--color-warning)] mt-0.5" />
              <div className="text-sm text-[var(--color-warning)]">
                <p className="font-semibold mb-1">Azure Custom Voice — Consent Required</p>
                <p>Your <strong>first uploaded sample</strong> must be a consent recording. Record yourself reading:</p>
                <p className="mt-1 italic text-xs">"I [your full name] am aware that recordings of my voice will be used by [company name] to create and use a synthetic version of my voice."</p>
                <p className="mt-1 text-xs">Upload the consent recording first, then add your voice samples (5-90 seconds each). Minimum 2 files total.</p>
              </div>
            </div>
          )}

          <CollapsiblePanel
            title="Record These Next"
            icon={<Sparkles className="h-4 w-4 text-electric-500" />}
            defaultOpen={samples.length === 0}
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)]">
                <span>
                  Phoneme-balanced sentences ranked by how many gaps each fills.
                  Record them in order for the best-quality voice clone.
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={loadRecommendations}
                  loading={loadingRecommendations}
                >
                  Refresh
                </Button>
              </div>
              {recommendationMethod === "bigram_approx" && (
                <div className="rounded border border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] p-2 text-xs text-[var(--color-warning)]">
                  <AlertTriangle className="inline h-3 w-3 mr-1" />
                  Using character-bigram fallback — install espeak + phonemizer
                  for full phoneme-accurate recommendations.
                </div>
              )}
              {loadingRecommendations ? (
                <p className="text-sm text-[var(--color-text-secondary)]">Loading recommendations…</p>
              ) : recommendations.length === 0 ? (
                <p className="text-sm text-[var(--color-text-secondary)]">
                  No recommendations available. Select a profile or try refreshing.
                </p>
              ) : (
                <ol
                  data-testid="sample-recommendations"
                  className="space-y-2"
                >
                  {recommendations.map((r) => (
                    <li
                      key={`${r.priority}-${r.text}`}
                      className="flex items-start gap-3 rounded border border-[var(--color-border)] p-2"
                    >
                      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-electric-500/10 text-xs font-medium text-electric-500">
                        {r.priority}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-[var(--color-text)]">{r.text}</p>
                        {r.gap_fill_count > 0 ? (
                          <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
                            Fills {r.gap_fill_count} phoneme gap{r.gap_fill_count !== 1 ? "s" : ""}
                            {r.fills_gaps.length > 0 && r.fills_gaps.length <= 8 ? (
                              <span className="ml-1 font-mono">
                                ({r.fills_gaps.join(", ")})
                              </span>
                            ) : null}
                          </p>
                        ) : (
                          <p className="mt-1 text-xs text-[var(--color-text-tertiary)] italic">
                            Variety pick (no new gaps to fill)
                          </p>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopySentence(r.text)}
                        aria-label={`Copy sentence ${r.priority}`}
                        title="Copy to clipboard"
                      >
                        <ClipboardCopy className="h-3 w-3" />
                      </Button>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </CollapsiblePanel>

          {samples.length > 0 && (
            <CollapsiblePanel
              title="Training Readiness"
              icon={<CheckCircle className="h-4 w-4 text-green-500" />}
            >
              {loadingReadiness ? (
                <p className="text-sm text-[var(--color-text-secondary)]">Checking readiness...</p>
              ) : readiness ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-4">
                    {/* Circular progress indicator */}
                    <div className="relative h-16 w-16 shrink-0">
                      <svg className="h-16 w-16 -rotate-90" viewBox="0 0 36 36">
                        <path
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          fill="none"
                          stroke="var(--color-border, #e5e7eb)"
                          strokeWidth="3"
                        />
                        <path
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          fill="none"
                          stroke={readiness.score >= 80 ? "#22c55e" : readiness.score >= 50 ? "#f59e0b" : "#ef4444"}
                          strokeWidth="3"
                          strokeDasharray={`${readiness.score}, 100`}
                          strokeLinecap="round"
                        />
                      </svg>
                      <span className="absolute inset-0 flex items-center justify-center text-sm font-bold">
                        {Math.round(readiness.score)}%
                      </span>
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">
                        {readiness.ready ? "Ready to train" : "Not yet ready"}
                      </p>
                      <p className="text-xs text-[var(--color-text-secondary)]">
                        {readiness.sample_count} samples, {readiness.total_duration.toFixed(1)}s total audio
                      </p>
                    </div>
                  </div>
                  {readiness.recommendations.length > 0 && (
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-[var(--color-text-secondary)]">Recommendations:</p>
                      <ul className="space-y-1">
                        {readiness.recommendations.map((rec, i) => (
                          <li key={i} className="text-xs text-[var(--color-text-secondary)] flex items-start gap-1.5">
                            <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--color-text-secondary)]" />
                            {rec}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-[var(--color-text-secondary)]">Add samples to check training readiness.</p>
              )}
            </CollapsiblePanel>
          )}

          <CollapsiblePanel
            title="Train Model"
            icon={<Cpu className="h-4 w-4 text-blue-500" />}
          >
            <div className="space-y-4">
              <Button
                onClick={handleStartTraining}
                disabled={samples.length < (isAzure ? 2 : 1) || (readiness !== null && !readiness.ready)}
              >
                Start Training
              </Button>
              {readiness !== null && !readiness.ready && (
                <p className="text-xs text-[var(--color-text-secondary)]">
                  Training is disabled until readiness requirements are met. See the Readiness panel above.
                </p>
              )}
              {progress && (
                <div className="space-y-2">
                  <ProgressBar percent={progress.percent} label={progress.status} />
                  {progress.error && <p className="text-sm text-red-500">{progress.error}</p>}
                </div>
              )}
            </div>
          </CollapsiblePanel>

          {profileJobs.length > 0 && (
            <CollapsiblePanel
              title="Training History"
              icon={<History className="h-4 w-4 text-gray-500" />}
              defaultOpen={false}
            >
              <div className="space-y-2">
                {profileJobs.map((job) => (
                  <div key={job.id} className="flex items-center justify-between rounded border border-[var(--color-border)] p-3">
                    <div>
                      <p className="text-sm font-medium">{job.provider_name}</p>
                      <p className="text-xs text-[var(--color-text-secondary)]">{new Date(job.created_at).toLocaleString()}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge status={job.status} />
                      {["queued", "training"].includes(job.status) && <Button size="sm" variant="danger" onClick={() => { logger.info("job_cancel", { job_id: job.id }); cancelJob(job.id); }}>Cancel</Button>}
                    </div>
                  </div>
                ))}
              </div>
            </CollapsiblePanel>
          )}
        </>
      )}
    </div>
  );
}
