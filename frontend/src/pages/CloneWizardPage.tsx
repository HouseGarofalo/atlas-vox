import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import {
  Upload,
  FileAudio,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Trash2,
  Play,
  Loader2,
  ExternalLink,
} from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Select } from "../components/ui/Select";
import { ProgressBar } from "../components/ui/ProgressBar";
import { api } from "../services/api";
import { useProfileStore } from "../stores/profileStore";
import { useProviderStore } from "../stores/providerStore";
import { createLogger } from "../utils/logger";
import { getErrorMessage } from "../utils/errors";
import type { Provider } from "../types";

const logger = createLogger("CloneWizardPage");

const ACCEPTED_FORMATS = ".wav,.mp3,.flac";
const ACCEPTED_MIME = ["audio/wav", "audio/mpeg", "audio/flac", "audio/x-wav", "audio/x-flac"];

interface UploadedFile {
  file: File;
  /** Human-readable duration string, set after decode */
  duration: string | null;
  /** Duration in seconds */
  durationSeconds: number | null;
  /** Format label derived from file extension */
  format: string;
}

/** Decode an audio file in the browser to measure its duration. */
function decodeDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const ctx = new AudioContext();
      ctx
        .decodeAudioData(reader.result as ArrayBuffer)
        .then((buf) => {
          resolve(buf.duration);
          void ctx.close();
        })
        .catch(reject);
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsArrayBuffer(file);
  });
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileFormat(name: string): string {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  switch (ext) {
    case "wav":
      return "WAV";
    case "mp3":
      return "MP3";
    case "flac":
      return "FLAC";
    default:
      return ext.toUpperCase() || "Unknown";
  }
}

const STEP_LABELS = [
  "Upload Samples",
  "Quality Check",
  "Select Provider",
  "Clone",
  "Done",
] as const;

export default function CloneWizardPage() {
  const [step, setStep] = useState(1);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [providerId, setProviderId] = useState("");
  const [profileName, setProfileName] = useState("");
  const [cloneLoading, setCloneLoading] = useState(false);
  const [cloneProgress, setCloneProgress] = useState(0);
  const [cloneError, setCloneError] = useState<string | null>(null);
  const [createdProfileId, setCreatedProfileId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { fetchProfiles, createProfile } = useProfileStore();
  const { providers, fetchProviders } = useProviderStore();

  useEffect(() => {
    fetchProviders();
    fetchProfiles();
  }, [fetchProviders, fetchProfiles]);

  // Filter providers that support cloning
  const cloningProviders = useMemo(
    () =>
      providers.filter(
        (p: Provider) => p.enabled && p.capabilities?.supports_cloning
      ),
    [providers]
  );

  const providerOptions = useMemo(
    () => [
      { value: "", label: "Select a provider..." },
      ...cloningProviders.map((p: Provider) => ({
        value: p.name,
        label: `${p.display_name} (min ${p.capabilities?.min_samples_for_cloning ?? "?"} samples)`,
      })),
    ],
    [cloningProviders]
  );

  const selectedProvider = cloningProviders.find((p: Provider) => p.name === providerId);
  const minSamples = selectedProvider?.capabilities?.min_samples_for_cloning ?? 1;
  const totalDuration = files.reduce(
    (sum, f) => sum + (f.durationSeconds ?? 0),
    0
  );

  // --- File handling ---

  const addFiles = async (incoming: File[]) => {
    const valid = incoming.filter((f) => {
      if (!ACCEPTED_MIME.includes(f.type) && !f.name.match(/\.(wav|mp3|flac)$/i)) {
        toast.error(`Unsupported format: ${f.name}`);
        return false;
      }
      return true;
    });

    const newEntries: UploadedFile[] = valid.map((file) => ({
      file,
      duration: null,
      durationSeconds: null,
      format: getFileFormat(file.name),
    }));

    setFiles((prev) => [...prev, ...newEntries]);

    // Decode durations in the background
    for (let i = 0; i < valid.length; i++) {
      try {
        const dur = await decodeDuration(valid[i]);
        setFiles((prev) =>
          prev.map((entry) =>
            entry.file === valid[i]
              ? { ...entry, duration: formatDuration(dur), durationSeconds: dur }
              : entry
          )
        );
      } catch {
        logger.warn("decode_duration_failed", { filename: valid[i].name });
      }
    }

    logger.info("files_added", { count: valid.length });
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const dropped = Array.from(e.dataTransfer.files);
    void addFiles(dropped);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      void addFiles(Array.from(e.target.files));
      e.target.value = "";
    }
  };

  // --- Clone workflow ---

  const handleStartClone = async () => {
    if (!providerId || !profileName.trim()) {
      toast.error("Select a provider and enter a profile name");
      return;
    }
    if (files.length < minSamples) {
      toast.error(`Need at least ${minSamples} sample(s) for this provider`);
      return;
    }

    logger.info("clone_start", { provider: providerId, fileCount: files.length, profileName });
    setCloneLoading(true);
    setCloneError(null);
    setCloneProgress(10);

    try {
      // Step 1: Create profile
      setCloneProgress(15);
      const profile = await createProfile({
        name: profileName.trim(),
        provider_name: providerId,
        description: `Voice clone created with ${files.length} sample(s)`,
      });
      logger.info("clone_profile_created", { profileId: profile.id });
      setCloneProgress(30);

      // Step 2: Upload samples
      const rawFiles = files.map((f) => f.file);
      await api.uploadSamples(profile.id, rawFiles);
      logger.info("clone_samples_uploaded", { count: rawFiles.length });
      setCloneProgress(55);

      // Step 3: Start training / cloning
      await api.startTraining(profile.id, { provider_name: providerId });
      logger.info("clone_training_started", { profileId: profile.id });
      setCloneProgress(80);

      // Step 4: Simulate finishing (real progress would come from polling)
      setCloneProgress(100);
      setCreatedProfileId(profile.id);
      setStep(5);
      toast.success("Voice cloning started successfully!");
      // Refresh profiles so the new one shows up
      void fetchProfiles(true);
    } catch (e: unknown) {
      const message = getErrorMessage(e);
      logger.error("clone_error", { error: message });
      setCloneError(message);
      toast.error(message);
    } finally {
      setCloneLoading(false);
    }
  };

  // --- Navigation ---

  const canAdvance = (): boolean => {
    switch (step) {
      case 1:
        return files.length > 0;
      case 2:
        return files.length > 0;
      case 3:
        return !!providerId && !!profileName.trim() && files.length >= minSamples;
      default:
        return false;
    }
  };

  const handleNext = () => {
    if (step === 4) {
      void handleStartClone();
      return;
    }
    if (canAdvance() && step < 5) {
      setStep(step + 1);
    }
  };

  const handleBack = () => {
    if (step > 1) setStep(step - 1);
  };

  // --- Render ---

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Voice Cloning Wizard</h1>

      {/* Stepper */}
      <div className="flex items-center gap-2">
        {STEP_LABELS.map((label, i) => {
          const stepNum = i + 1;
          const isActive = step === stepNum;
          const isComplete = step > stepNum;
          return (
            <div key={label} className="flex items-center gap-2">
              {i > 0 && (
                <div
                  className={`h-px w-6 sm:w-10 ${
                    isComplete ? "bg-primary-500" : "bg-[var(--color-border)]"
                  }`}
                />
              )}
              <div className="flex items-center gap-1.5">
                <div
                  className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold transition-colors ${
                    isActive
                      ? "bg-primary-500 text-white"
                      : isComplete
                        ? "bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300"
                        : "bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500"
                  }`}
                >
                  {isComplete ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    stepNum
                  )}
                </div>
                <span
                  className={`hidden text-xs font-medium sm:inline ${
                    isActive
                      ? "text-[var(--color-text)]"
                      : "text-[var(--color-text-secondary)]"
                  }`}
                >
                  {label}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Step content */}
      <Card className="min-h-[320px]">
        {/* Step 1: Upload */}
        {step === 1 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Upload Audio Samples</h2>
            <p className="text-sm text-[var(--color-text-secondary)]">
              Add voice recordings for cloning. Supported formats: WAV, MP3, FLAC.
            </p>

            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_FORMATS}
              multiple
              className="hidden"
              onChange={handleFileInput}
            />

            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`flex flex-col items-center gap-3 rounded-lg border-2 border-dashed p-10 cursor-pointer transition-colors ${
                dragActive
                  ? "border-primary-500 bg-primary-50/50 dark:bg-primary-950/20"
                  : "border-[var(--color-border)] hover:border-primary-400 hover:bg-primary-50/30 dark:hover:bg-primary-950/10"
              }`}
            >
              <Upload className="h-10 w-10 text-[var(--color-text-secondary)]" />
              <div className="text-center">
                <p className="text-sm font-medium text-[var(--color-text)]">
                  Drag & drop audio files here, or click to browse
                </p>
                <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
                  WAV, MP3, FLAC accepted
                </p>
              </div>
            </div>

            {files.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium">
                  {files.length} file{files.length !== 1 ? "s" : ""} selected
                </p>
                {files.map((f, i) => (
                  <div
                    key={`${f.file.name}-${i}`}
                    className="flex items-center gap-3 rounded-lg border border-[var(--color-border)] p-3"
                  >
                    <FileAudio className="h-5 w-5 shrink-0 text-primary-500" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{f.file.name}</p>
                      <p className="text-xs text-[var(--color-text-secondary)]">
                        {formatSize(f.file.size)}
                        {f.duration && ` \u00B7 ${f.duration}`}
                        {` \u00B7 ${f.format}`}
                      </p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFile(i);
                      }}
                      className="shrink-0 rounded p-1 text-[var(--color-text-secondary)] hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30"
                      aria-label={`Remove ${f.file.name}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Step 2: Quality Check */}
        {step === 2 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Preview & Quality Check</h2>
            <p className="text-sm text-[var(--color-text-secondary)]">
              Review your uploaded samples before proceeding.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="rounded-lg border border-[var(--color-border)] p-4 text-center">
                <p className="text-2xl font-bold text-primary-500">{files.length}</p>
                <p className="text-xs text-[var(--color-text-secondary)]">Total Files</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] p-4 text-center">
                <p className="text-2xl font-bold text-primary-500">
                  {formatDuration(totalDuration)}
                </p>
                <p className="text-xs text-[var(--color-text-secondary)]">Total Duration</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] p-4 text-center">
                <p className="text-2xl font-bold text-primary-500">
                  {[...new Set(files.map((f) => f.format))].join(", ") || "--"}
                </p>
                <p className="text-xs text-[var(--color-text-secondary)]">Formats</p>
              </div>
            </div>

            <div className="space-y-2 max-h-64 overflow-y-auto">
              {files.map((f, i) => (
                <div
                  key={`${f.file.name}-${i}`}
                  className="flex items-center gap-3 rounded-lg border border-[var(--color-border)] p-3"
                >
                  <FileAudio className="h-5 w-5 shrink-0 text-primary-500" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{f.file.name}</p>
                    <div className="flex gap-3 text-xs text-[var(--color-text-secondary)]">
                      <span>{f.format}</span>
                      <span>{formatSize(f.file.size)}</span>
                      {f.duration && <span>{f.duration}</span>}
                    </div>
                  </div>
                  <CheckCircle2 className="h-5 w-5 shrink-0 text-green-500" />
                </div>
              ))}
            </div>

            {totalDuration < 6 && (
              <p className="text-xs text-amber-600 dark:text-amber-400">
                Tip: Most cloning providers work best with at least 6 seconds of audio.
              </p>
            )}
          </div>
        )}

        {/* Step 3: Select Provider */}
        {step === 3 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Select Cloning Provider</h2>
            <p className="text-sm text-[var(--color-text-secondary)]">
              Choose a provider that supports voice cloning, and give your new voice a name.
            </p>

            <div className="space-y-4 max-w-md">
              <div className="space-y-1">
                <label
                  htmlFor="profile-name"
                  className="block text-sm font-medium text-[var(--color-text)]"
                >
                  Voice Name
                </label>
                <input
                  id="profile-name"
                  type="text"
                  value={profileName}
                  onChange={(e) => setProfileName(e.target.value)}
                  placeholder="e.g., My Custom Voice"
                  className="h-10 w-full rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg)] px-3 text-sm text-[var(--color-text)] focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
              </div>

              <Select
                label="Cloning Provider"
                value={providerId}
                onChange={(e) => setProviderId(e.target.value)}
                options={providerOptions}
              />

              {selectedProvider && (
                <div className="rounded-lg border border-[var(--color-border)] p-3 text-sm space-y-1">
                  <p className="font-medium">{selectedProvider.display_name}</p>
                  <p className="text-xs text-[var(--color-text-secondary)]">
                    Minimum samples: {selectedProvider.capabilities?.min_samples_for_cloning ?? "?"} |
                    GPU required: {selectedProvider.capabilities?.requires_gpu ? "Yes" : "No"} |
                    Languages: {selectedProvider.capabilities?.supported_languages?.join(", ") || "All"}
                  </p>
                  {files.length < minSamples && (
                    <p className="text-xs text-red-500 mt-1">
                      You have {files.length} sample(s) but this provider requires at least {minSamples}.
                    </p>
                  )}
                </div>
              )}

              {cloningProviders.length === 0 && (
                <p className="text-sm text-amber-600 dark:text-amber-400">
                  No providers with cloning capability are currently enabled.
                  Please enable a cloning-capable provider in{" "}
                  <Link to="/providers" className="underline">
                    Providers
                  </Link>
                  .
                </p>
              )}
            </div>
          </div>
        )}

        {/* Step 4: Start Cloning */}
        {step === 4 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Start Cloning</h2>
            <p className="text-sm text-[var(--color-text-secondary)]">
              Review and confirm your clone configuration.
            </p>

            <div className="rounded-lg border border-[var(--color-border)] p-4 space-y-3">
              <div className="grid grid-cols-2 gap-y-2 text-sm">
                <span className="text-[var(--color-text-secondary)]">Voice Name</span>
                <span className="font-medium">{profileName}</span>
                <span className="text-[var(--color-text-secondary)]">Provider</span>
                <span className="font-medium">{selectedProvider?.display_name ?? providerId}</span>
                <span className="text-[var(--color-text-secondary)]">Samples</span>
                <span className="font-medium">{files.length} file(s)</span>
                <span className="text-[var(--color-text-secondary)]">Total Duration</span>
                <span className="font-medium">{formatDuration(totalDuration)}</span>
              </div>
            </div>

            {cloneLoading && (
              <div className="space-y-3">
                <ProgressBar percent={cloneProgress} label="Cloning Progress" />
                <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {cloneProgress < 30
                    ? "Creating profile..."
                    : cloneProgress < 55
                      ? "Uploading samples..."
                      : cloneProgress < 80
                        ? "Starting training..."
                        : "Finalizing..."}
                </div>
              </div>
            )}

            {cloneError && (
              <div className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400">
                {cloneError}
              </div>
            )}
          </div>
        )}

        {/* Step 5: Done */}
        {step === 5 && (
          <div className="flex flex-col items-center justify-center gap-4 py-8">
            <CheckCircle2 className="h-16 w-16 text-green-500" />
            <h2 className="text-xl font-semibold">Voice Cloning Started!</h2>
            <p className="text-sm text-[var(--color-text-secondary)] text-center max-w-md">
              Your voice clone training has been initiated. It may take a few minutes
              depending on the provider and sample size. You can track progress in the
              Training Studio.
            </p>
            <div className="flex gap-3 mt-4">
              {createdProfileId && (
                <Link to="/profiles">
                  <Button variant="primary">
                    <ExternalLink className="h-4 w-4" />
                    View Profiles
                  </Button>
                </Link>
              )}
              <Link to="/training">
                <Button variant="secondary">
                  <Play className="h-4 w-4" />
                  Training Studio
                </Button>
              </Link>
              <Button
                variant="ghost"
                onClick={() => {
                  setStep(1);
                  setFiles([]);
                  setProfileName("");
                  setProviderId("");
                  setCloneProgress(0);
                  setCloneError(null);
                  setCreatedProfileId(null);
                }}
              >
                Clone Another
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Navigation buttons */}
      {step < 5 && (
        <div className="flex justify-between">
          <Button
            variant="secondary"
            onClick={handleBack}
            disabled={step === 1}
          >
            <ChevronLeft className="h-4 w-4" />
            Back
          </Button>
          {step === 4 ? (
            <Button
              onClick={handleNext}
              disabled={cloneLoading}
            >
              {cloneLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Cloning...
                </>
              ) : (
                "Start Cloning"
              )}
            </Button>
          ) : (
            <Button
              onClick={handleNext}
              disabled={!canAdvance()}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
