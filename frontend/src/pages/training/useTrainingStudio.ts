/**
 * useTrainingStudio — orchestration hook for TrainingStudioPage.
 *
 * Extracted from TrainingStudioPage.tsx as part of P2-20 (decompose large pages).
 * Groups all the sample + recommendation + readiness + upload/record/train
 * side-effects into one hook so the page file is purely layout/wiring.
 *
 * Behaviour is preserved exactly — the hook body is copied from the
 * page-component body; only `return` has been added to expose the state and
 * handlers for the JSX.
 */

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { useProfileStore } from "../../stores/profileStore";
import { useTrainingStore } from "../../stores/trainingStore";
import { useTrainingProgress } from "../../hooks/useWebSocket";
import { api } from "../../services/api";
import { createLogger } from "../../utils/logger";
import type { AudioSample, QualityResult, ReadinessResult } from "../../types";
import type { Recommendation } from "./SampleRecommendationsPanel";

const logger = createLogger("TrainingStudioPage");

export function useTrainingStudio(initialProfileId: string) {
  const { profiles, fetchProfiles } = useProfileStore();
  const { jobs, fetchJobs, startTraining, cancelJob } = useTrainingStore();

  const [selectedProfile, setSelectedProfile] = useState(initialProfileId);
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
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [recommendationMethod, setRecommendationMethod] = useState<
    "phonemizer" | "bigram_approx" | null
  >(null);
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);
  const { progress, connectionStatus, connectionBanner } = useTrainingProgress(activeJobId);

  useEffect(() => {
    fetchProfiles().catch(() => toast.error("Failed to load profiles"));
    fetchJobs().catch(() => toast.error("Failed to load training jobs"));
  }, []);

  const loadSamples = useCallback(async () => {
    try {
      const { samples: s } = await api.listSamples(selectedProfile);
      setSamples(s);
    } catch {
      setSamples([]);
    }
  }, [selectedProfile]);

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

  const handleCopySentence = (text: string) => {
    navigator.clipboard?.writeText(text).then(
      () => toast.success("Copied to clipboard"),
      () => toast.error("Clipboard unavailable"),
    );
  };

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
      toast.error(e instanceof Error ? e.message : "Quality check failed");
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
      toast.error(e instanceof Error ? e.message : "Enhancement failed");
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

  const handlePlaySample = (sampleId: string) => {
    setPlayingSampleId((prev) => (prev === sampleId ? null : sampleId));
  };

  const handleUpload = async (files: File[]) => {
    if (!selectedProfile) {
      toast.error("Select a profile first");
      return;
    }
    const totalSize = files.reduce((sum, f) => sum + f.size, 0);
    logger.info("file_upload", { count: files.length, total_bytes: totalSize });
    setUploading(true);
    try {
      await api.uploadSamples(selectedProfile, files);
      toast.success(`${files.length} file(s) uploaded and analyzed`);
      logger.info("file_upload_complete", { count: files.length });
      await loadSamples();
      // Refresh recommendations — newly-recorded sentences now get excluded.
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

  const handleCancelJob = (jobId: string) => {
    logger.info("job_cancel", { job_id: jobId });
    cancelJob(jobId);
  };

  return {
    // stores (pass-through)
    profiles,
    jobs,
    // profile selection
    selectedProfile,
    setSelectedProfile,
    // samples state
    samples,
    sampleQualities,
    playingSampleId,
    setPlayingSampleId,
    enhancing,
    enhancingAll,
    checkingQuality,
    uploading,
    preprocessing,
    // recommendations
    recommendations,
    recommendationMethod,
    loadingRecommendations,
    // readiness
    readiness,
    loadingReadiness,
    // training progress
    progress,
    connectionStatus,
    connectionBanner,
    activeJobId,
    // handlers
    loadRecommendations,
    handleCopySentence,
    handleCheckQuality,
    handleEnhance,
    handleEnhanceAll,
    handlePlaySample,
    handleUpload,
    handleRecord,
    handlePreprocess,
    handleStartTraining,
    handleCancelJob,
  };
}
