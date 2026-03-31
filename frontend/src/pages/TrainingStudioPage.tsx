import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Music, Cpu, History, AlertTriangle } from "lucide-react";
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
import type { AudioSample } from "../types";
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
  const { progress } = useTrainingProgress(activeJobId);

  useEffect(() => {
    fetchProfiles().catch(() => toast.error("Failed to load profiles"));
    fetchJobs().catch(() => toast.error("Failed to load training jobs"));
  }, []);
  useEffect(() => {
    if (selectedProfile) {
      logger.info("profile_selected", { profile_id: selectedProfile });
      loadSamples();
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
    try { const { samples: s } = await api.listSamples(selectedProfile); setSamples(s); } catch { /* empty */ }
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
                  </div>
                  {samples.map((s) => (
                    <div key={s.id} className="flex items-center gap-3 rounded border border-[var(--color-border)] p-2">
                      <span className="flex-1 text-sm truncate">{s.original_filename}</span>
                      <span className="text-xs text-[var(--color-text-secondary)] uppercase hidden sm:inline">{s.format}</span>
                      <span className="text-xs text-[var(--color-text-secondary)]">{s.duration_seconds ? `${s.duration_seconds.toFixed(1)}s` : "Pending"}</span>
                      <Badge status={s.preprocessed ? "ready" : "pending"} />
                    </div>
                  ))}
                </div>
              )}
              {samples.some((s) => !s.preprocessed) && (
                <Button variant="secondary" onClick={handlePreprocess} disabled={preprocessing}>
                  {preprocessing ? "Preprocessing..." : "Preprocess Samples"}
                </Button>
              )}
            </div>
          </CollapsiblePanel>

          {isAzure && (
            <div className="flex items-start gap-3 rounded-lg border border-amber-300 bg-amber-50 p-4 dark:border-amber-700 dark:bg-amber-900/20">
              <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
              <div className="text-sm text-amber-800 dark:text-amber-200">
                <p className="font-semibold mb-1">Azure Custom Voice — Consent Required</p>
                <p>Your <strong>first uploaded sample</strong> must be a consent recording. Record yourself reading:</p>
                <p className="mt-1 italic text-xs">"I [your full name] am aware that recordings of my voice will be used by [company name] to create and use a synthetic version of my voice."</p>
                <p className="mt-1 text-xs">Upload the consent recording first, then add your voice samples (5-90 seconds each). Minimum 2 files total.</p>
              </div>
            </div>
          )}

          <CollapsiblePanel
            title="Train Model"
            icon={<Cpu className="h-4 w-4 text-blue-500" />}
          >
            <div className="space-y-4">
              <Button onClick={handleStartTraining} disabled={samples.length < (isAzure ? 2 : 1)}>Start Training</Button>
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
