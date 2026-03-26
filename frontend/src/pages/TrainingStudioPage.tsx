import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Select } from "../components/ui/Select";
import { ProgressBar } from "../components/ui/ProgressBar";
import { AudioRecorder, FileUploader } from "../components/audio/AudioRecorder";
import { useProfileStore } from "../stores/profileStore";
import { useTrainingStore } from "../stores/trainingStore";
import { useTrainingProgress } from "../hooks/useWebSocket";
import { api } from "../services/api";

export default function TrainingStudioPage() {
  const [searchParams] = useSearchParams();
  const { profiles, fetchProfiles } = useProfileStore();
  const { jobs, fetchJobs, startTraining, cancelJob } = useTrainingStore();
  const [selectedProfile, setSelectedProfile] = useState(searchParams.get("profile") || "");
  const [samples, setSamples] = useState<any[]>([]);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [preprocessing, setPreprocessing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const { progress } = useTrainingProgress(activeJobId);

  useEffect(() => {
    fetchProfiles().catch(() => toast.error("Failed to load profiles"));
    fetchJobs().catch(() => toast.error("Failed to load training jobs"));
  }, []);
  useEffect(() => { if (selectedProfile) loadSamples(); }, [selectedProfile]);

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
    setUploading(true);
    try {
      await api.uploadSamples(selectedProfile, files);
      toast.success(`${files.length} file(s) uploaded and analyzed`);
      await loadSamples();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setUploading(false);
    }
  };

  const handleRecord = async (blob: Blob, filename: string) => {
    await handleUpload([new File([blob], filename, { type: blob.type })]);
  };

  const handlePreprocess = async () => {
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
    } catch (e: any) {
      toast.error(e.message);
      setPreprocessing(false);
    }
  };

  const handleStartTraining = async () => {
    try { const job = await startTraining(selectedProfile); setActiveJobId(job.id); toast.success("Training started"); } catch (e: any) { toast.error(e.message); }
  };

  const profileOptions = profiles.map((p) => ({ value: p.id, label: `${p.name} (${p.provider_name})` }));
  const profileJobs = jobs.filter((j) => j.profile_id === selectedProfile);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Training Studio</h1>
      <Select label="Voice Profile" value={selectedProfile} onChange={(e) => setSelectedProfile(e.target.value)} options={[{ value: "", label: "Select a profile..." }, ...profileOptions]} />

      {selectedProfile && (
        <>
          <Card>
            <h2 className="mb-3 text-lg font-semibold">Audio Samples ({samples.length})</h2>
            <div className="space-y-4">
              <FileUploader onFiles={handleUpload} />
              <AudioRecorder onRecorded={handleRecord} />
              {uploading && (
                <p className="text-sm text-[var(--color-text-secondary)]">Uploading and analyzing files...</p>
              )}
              {samples.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] px-2">
                    <span>Total: {samples.reduce((sum: number, s: any) => sum + (s.duration_seconds || 0), 0).toFixed(1)}s across {samples.length} file(s)</span>
                  </div>
                  {samples.map((s: any) => (
                    <div key={s.id} className="flex items-center gap-3 rounded border border-[var(--color-border)] p-2">
                      <span className="flex-1 text-sm truncate">{s.original_filename}</span>
                      <span className="text-xs text-[var(--color-text-secondary)] uppercase">{s.format}</span>
                      <span className="text-xs text-[var(--color-text-secondary)]">{s.duration_seconds ? `${s.duration_seconds.toFixed(1)}s` : "Pending"}</span>
                      <Badge status={s.preprocessed ? "ready" : "pending"} />
                    </div>
                  ))}
                </div>
              )}
              {samples.some((s: any) => !s.preprocessed) && (
                <Button variant="secondary" onClick={handlePreprocess} disabled={preprocessing}>
                  {preprocessing ? "Preprocessing..." : "Preprocess Samples"}
                </Button>
              )}
            </div>
          </Card>

          <Card>
            <h2 className="mb-3 text-lg font-semibold">Train Model</h2>
            <div className="space-y-4">
              <Button onClick={handleStartTraining} disabled={samples.length === 0}>Start Training</Button>
              {progress && (
                <div className="space-y-2">
                  <ProgressBar percent={progress.percent} label={progress.status} />
                  {progress.error && <p className="text-sm text-red-500">{progress.error}</p>}
                </div>
              )}
            </div>
          </Card>

          {profileJobs.length > 0 && (
            <Card>
              <h2 className="mb-3 text-lg font-semibold">Training History</h2>
              <div className="space-y-2">
                {profileJobs.map((job) => (
                  <div key={job.id} className="flex items-center justify-between rounded border border-[var(--color-border)] p-3">
                    <div>
                      <p className="text-sm font-medium">{job.provider_name}</p>
                      <p className="text-xs text-[var(--color-text-secondary)]">{new Date(job.created_at).toLocaleString()}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge status={job.status} />
                      {["queued", "training"].includes(job.status) && <Button size="sm" variant="danger" onClick={() => cancelJob(job.id)}>Cancel</Button>}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
