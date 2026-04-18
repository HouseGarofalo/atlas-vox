import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getErrorMessage } from "../utils/errors";
import { Library, Mic, Plus, Trash2, Upload, Volume2, GitCompare, Sparkles, Play, Pause, Gauge } from "lucide-react";
import { toast } from "sonner";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Modal } from "../components/ui/Modal";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { AudioPlayer } from "../components/audio/AudioPlayer";
import { useProfileStore } from "../stores/profileStore";
import { useProviderStore } from "../stores/providerStore";
import { api } from "../services/api";
import { createLogger } from "../utils/logger";
import type { VoiceProfile } from "../types";

const logger = createLogger("ProfilesPage");

export default function ProfilesPage() {
  const { profiles, loading, error, fetchProfiles, createProfile, deleteProfile } = useProfileStore();
  const { providers, fetchProviders } = useProviderStore();
  const navigate = useNavigate();
  const [showCreate, setShowCreate] = useState(false);
  const [createMode, setCreateMode] = useState<"choose" | "training" | "design">("choose");
  const [form, setForm] = useState({ name: "", description: "", language: "en", provider_name: "" });
  const [compareProfile, setCompareProfile] = useState<VoiceProfile | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  // Voice Design state
  const [designDescription, setDesignDescription] = useState("");
  const [designText, setDesignText] = useState("");
  const [designPreviews, setDesignPreviews] = useState<{ voice_id: string; audio_base64: string }[]>([]);
  const [designLoading, setDesignLoading] = useState(false);
  const [designPlaying, setDesignPlaying] = useState<string | null>(null);
  const [designCreating, setDesignCreating] = useState(false);

  useEffect(() => {
    fetchProfiles();
    fetchProviders();
  }, []);

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    logger.info("profile_create", { provider: form.provider_name, language: form.language });
    try {
      await createProfile(form);
      toast.success("Profile created");
      logger.info("profile_created");
      setShowCreate(false);
      setCreateMode("choose");
      setForm({ name: "", description: "", language: "en", provider_name: "" });
    } catch (e: unknown) {
      logger.error("profile_create_error", { error: getErrorMessage(e) });
      toast.error(getErrorMessage(e));
    }
  };

  const handleDelete = async (id: string) => {
    logger.info("profile_delete", { profile_id: id });
    try {
      await deleteProfile(id);
      toast.success("Profile deleted");
      logger.info("profile_deleted", { profile_id: id });
    } catch (e: unknown) {
      logger.error("profile_delete_error", { profile_id: id, error: getErrorMessage(e) });
      toast.error(getErrorMessage(e));
    } finally {
      setDeleteTarget(null);
    }
  };

  const handleGeneratePreviews = async () => {
    if (!designDescription.trim()) { toast.error("Enter a voice description"); return; }
    logger.info("voice_design_start", { description: designDescription });
    setDesignLoading(true);
    setDesignPreviews([]);
    try {
      const result = await api.designVoice(designDescription, designText || undefined);
      setDesignPreviews(result.previews);
      if (result.previews.length === 0) toast.info("No previews generated. Try a different description.");
      else toast.success(`${result.previews.length} preview(s) generated`);
    } catch (e: unknown) {
      const message = e instanceof Error ? getErrorMessage(e) : "Voice design failed";
      logger.error("voice_design_error", { error: message });
      toast.error(message);
    } finally {
      setDesignLoading(false);
    }
  };

  const handleUseDesignedVoice = async (voiceId: string) => {
    setDesignCreating(true);
    try {
      await createProfile({
        name: designDescription.slice(0, 60) || "Designed Voice",
        description: designDescription,
        language: "en",
        provider_name: "elevenlabs",
        voice_id: voiceId,
      });
      toast.success("Profile created from designed voice");
      setShowCreate(false);
      setCreateMode("choose");
      setDesignDescription("");
      setDesignText("");
      setDesignPreviews([]);
    } catch (e: unknown) {
      const message = e instanceof Error ? getErrorMessage(e) : "Failed to create profile";
      toast.error(message);
    } finally {
      setDesignCreating(false);
    }
  };

  // Filter to providers that support cloning or fine-tuning for training mode.
  // Only show providers with actual training capabilities -- never fall back
  // to non-training providers like Kokoro which cannot clone or fine-tune.
  const trainingProviderOptions = providers
    .filter(
      (p) =>
        p.enabled &&
        p.capabilities &&
        (p.capabilities.supports_cloning || p.capabilities.supports_fine_tuning)
    )
    .map((p) => ({ value: p.name, label: p.display_name }));

  const providerOptions = trainingProviderOptions.length
    ? trainingProviderOptions
    : [{ value: "", label: "No training-capable providers available" }];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Voice Profiles</h1>
        <Button onClick={() => { logger.info("modal_open"); setShowCreate(true); setCreateMode("choose"); }}>
          <Plus className="h-4 w-4" /> New Profile
        </Button>
      </div>

      {loading && !profiles.length ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} variant="card" height={200} />
          ))}
        </div>
      ) : error && !profiles.length ? (
        <Card className="py-8 text-center space-y-3">
          <p className="text-sm text-[var(--color-error)]">Failed to load profiles: {error}</p>
          <Button variant="secondary" onClick={() => fetchProfiles()}>
            Retry
          </Button>
        </Card>
      ) : profiles.length === 0 ? (
        <EmptyState
          icon={<Mic className="h-12 w-12" />}
          title="No voice profiles yet"
          description="Create your first voice profile to start training and synthesizing."
          action={{ label: "Create Profile", onClick: () => { setShowCreate(true); setCreateMode("choose"); } }}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {profiles.map((profile) => (
            <ProfileCard
              key={profile.id}
              profile={profile}
              onDelete={() => { setDeleteTarget(profile.id); }}
              onTrain={() => { logger.info("navigate_train", { profile_id: profile.id }); navigate(`/training?profile=${profile.id}`); }}
              onSynthesize={() => { logger.info("navigate_synthesize", { profile_id: profile.id }); navigate(`/synthesis?profile=${profile.id}`); }}
              onCompare={() => { logger.info("version_compare_open", { profile_id: profile.id }); setCompareProfile(profile); }}
            />
          ))}
        </div>
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => { if (deleteTarget) handleDelete(deleteTarget); }}
        title="Delete Voice Profile"
        description="Are you sure you want to delete this profile? This action cannot be undone."
        confirmLabel="Delete Profile"
        variant="danger"
      />

      {/* Version Compare Modal */}
      <VersionCompareModal
        profile={compareProfile}
        open={compareProfile !== null}
        onClose={() => setCompareProfile(null)}
      />

      {/* New Profile Modal */}
      <Modal
        open={showCreate}
        onClose={() => { logger.info("modal_close"); setShowCreate(false); setCreateMode("choose"); }}
        title="Create Voice Profile"
        wide
      >
        {createMode === "choose" ? (
          <div className="space-y-4">
            <p className="text-sm text-[var(--color-text-secondary)]">
              Choose how to create your voice profile:
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <button
                onClick={() => {
                  setShowCreate(false);
                  setCreateMode("choose");
                  navigate("/library");
                }}
                className="flex flex-col items-center gap-3 rounded-lg border-2 border-[var(--color-border)] p-6 transition-colors hover:border-primary-500 hover:bg-primary-50 dark:hover:bg-primary-950"
              >
                <Library className="h-8 w-8 text-primary-500" />
                <div className="text-center">
                  <h3 className="font-semibold text-[var(--color-text)]">Library Voice</h3>
                  <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
                    Pick a pre-built voice from the library. Instantly ready for synthesis.
                  </p>
                </div>
              </button>
              <button
                onClick={() => {
                  setCreateMode("training");
                  // Default to first training-capable provider
                  if (trainingProviderOptions.length > 0 && !form.provider_name) {
                    setForm((f) => ({ ...f, provider_name: trainingProviderOptions[0].value }));
                  }
                }}
                className="flex flex-col items-center gap-3 rounded-lg border-2 border-[var(--color-border)] p-6 transition-colors hover:border-primary-500 hover:bg-primary-50 dark:hover:bg-primary-950"
              >
                <Mic className="h-8 w-8 text-primary-500" />
                <div className="text-center">
                  <h3 className="font-semibold text-[var(--color-text)]">Custom Voice (Training)</h3>
                  <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
                    Clone or fine-tune a voice from your own audio samples.
                  </p>
                </div>
              </button>
              <button
                onClick={() => {
                  setCreateMode("design");
                  setDesignDescription("");
                  setDesignText("");
                  setDesignPreviews([]);
                }}
                className="flex flex-col items-center gap-3 rounded-lg border-2 border-[var(--color-border)] p-6 transition-colors hover:border-primary-500 hover:bg-primary-50 dark:hover:bg-primary-950"
              >
                <Sparkles className="h-8 w-8 text-violet-500" />
                <div className="text-center">
                  <h3 className="font-semibold text-[var(--color-text)]">Design Voice (AI)</h3>
                  <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
                    Describe a voice in natural language and generate it with AI.
                  </p>
                </div>
              </button>
            </div>
            <div className="flex justify-end pt-2">
              <Button variant="secondary" onClick={() => { setShowCreate(false); setCreateMode("choose"); }}>
                Cancel
              </Button>
            </div>
          </div>
        ) : createMode === "design" ? (
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="block text-sm font-medium text-[var(--color-text)]">Voice Description</label>
              <textarea
                value={designDescription}
                onChange={(e) => setDesignDescription(e.target.value)}
                placeholder="A warm, friendly female voice with a British accent"
                rows={3}
                className="w-full rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm text-[var(--color-text)] focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>
            <Input
              label="Preview Text (optional)"
              value={designText}
              onChange={(e) => setDesignText(e.target.value)}
              placeholder="Hello, this is a preview of the designed voice."
            />
            <Button onClick={handleGeneratePreviews} loading={designLoading} disabled={!designDescription.trim()}>
              <Sparkles className="h-4 w-4" /> Generate Previews
            </Button>

            {designPreviews.length > 0 && (
              <div className="space-y-3">
                <p className="text-sm font-medium text-[var(--color-text)]">Generated Previews</p>
                {designPreviews.map((preview, idx) => (
                  <div
                    key={preview.voice_id}
                    className="flex items-center gap-3 rounded-lg border border-[var(--color-border)] p-3"
                  >
                    <button
                      onClick={() => {
                        if (designPlaying === preview.voice_id) {
                          setDesignPlaying(null);
                        } else {
                          setDesignPlaying(preview.voice_id);
                        }
                      }}
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-500 text-white hover:bg-primary-600 transition-colors"
                    >
                      {designPlaying === preview.voice_id ? (
                        <Pause className="h-3.5 w-3.5" />
                      ) : (
                        <Play className="h-3.5 w-3.5 ml-0.5" />
                      )}
                    </button>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">Voice {idx + 1}</p>
                      <p className="text-xs text-[var(--color-text-secondary)] truncate">{preview.voice_id}</p>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleUseDesignedVoice(preview.voice_id)}
                      disabled={designCreating}
                    >
                      Use This Voice
                    </Button>
                    {designPlaying === preview.voice_id && (
                      <audio
                        src={`data:audio/mpeg;base64,${preview.audio_base64}`}
                        autoPlay
                        onEnded={() => setDesignPlaying(null)}
                        className="hidden"
                      />
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => setCreateMode("choose")}>
                Back
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <Input
              label="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="My Custom Voice"
            />
            <Input
              label="Description"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Optional description"
            />
            <Select
              label="Language"
              value={form.language}
              onChange={(e) => setForm({ ...form, language: e.target.value })}
              options={[
                { value: "en", label: "English" },
                { value: "es", label: "Spanish" },
                { value: "fr", label: "French" },
                { value: "de", label: "German" },
                { value: "zh", label: "Chinese" },
                { value: "ja", label: "Japanese" },
              ]}
            />
            <Select
              label="Provider (supports training)"
              value={form.provider_name}
              onChange={(e) => setForm({ ...form, provider_name: e.target.value })}
              options={providerOptions}
            />
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => setCreateMode("choose")}>
                Back
              </Button>
              <Button onClick={handleCreate}>Create</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

const ProfileCard = React.memo(function ProfileCard({
  profile,
  onDelete,
  onTrain,
  onSynthesize,
  onCompare,
}: {
  profile: VoiceProfile;
  onDelete: () => void;
  onTrain: () => void;
  onSynthesize: () => void;
  onCompare: () => void;
}) {
  const isReady = profile.status === "ready";
  const hasLibraryVoice = !!profile.voice_id;
  // Card-local navigator — the outer page's `navigate` is out of scope inside
  // this memoised child, so we pull our own via the hook.
  const navigate = useNavigate();

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold">{profile.name}</h3>
          <p className="text-xs text-[var(--color-text-secondary)]">
            {profile.provider_name} &middot; {profile.language}
            {profile.voice_id && (
              <span className="ml-1 text-primary-500"> &middot; {profile.voice_id}</span>
            )}
          </p>
        </div>
        <Badge status={profile.status} />
      </div>
      {profile.description && (
        <p className="text-sm text-[var(--color-text-secondary)] line-clamp-2">{profile.description}</p>
      )}
      <div className="flex gap-4 text-xs text-[var(--color-text-secondary)]">
        {hasLibraryVoice ? (
          <span>Library voice</span>
        ) : (
          <>
            <span>{profile.sample_count} samples</span>
            <span>{profile.version_count} version{profile.version_count !== 1 ? "s" : ""}</span>
          </>
        )}
      </div>
      <div className="flex gap-2 mt-auto pt-2 border-t border-[var(--color-border)]">
        {isReady ? (
          <Button size="sm" onClick={onSynthesize}>
            <Volume2 className="h-3 w-3" /> Synthesize
          </Button>
        ) : (
          <Button size="sm" variant="secondary" onClick={onTrain}>
            <Upload className="h-3 w-3" /> Train
          </Button>
        )}
        {profile.version_count > 1 && (
          <Button size="sm" variant="secondary" onClick={onCompare}>
            <GitCompare className="h-3 w-3" />
          </Button>
        )}
        {/* VQ-36: jump to the per-profile quality dashboard. Enabled as soon
            as there's any synthesis history or version metrics to show. */}
        <Button
          size="sm"
          variant="ghost"
          onClick={() => navigate(`/profiles/${profile.id}/quality`)}
          aria-label="View quality dashboard"
          title="Quality dashboard"
        >
          <Gauge className="h-3 w-3" />
        </Button>
        <Button size="sm" variant="ghost" onClick={onDelete}>
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>
    </Card>
  );
});

// VersionInfo type — imported from shared types
type VersionInfo = import("../types").ModelVersion;

function VersionCompareModal({ profile, open, onClose }: { profile: VoiceProfile | null; open: boolean; onClose: () => void }) {
  const [versions, setVersions] = useState<VersionInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<[string, string]>(["", ""]);
  const [testText, setTestText] = useState("Hello, this is a version comparison test.");
  const [comparing, setComparing] = useState(false);
  const [results, setResults] = useState<{ version_id: string; audio_url: string | null; error: string | null }[]>([]);
  const [promoting, setPromoting] = useState<string | null>(null);
  const { activateVersion } = useProfileStore();

  useEffect(() => {
    if (!open || !profile) return;
    setLoading(true);
    setSelected(["", ""]);
    setResults([]);
    api.listVersions(profile.id)
      .then(({ versions: v }) => {
        setVersions(v);
        // Auto-select latest two
        if (v.length >= 2) {
          setSelected([v[v.length - 2].id, v[v.length - 1].id]);
        }
      })
      .catch(() => toast.error("Failed to load versions"))
      .finally(() => setLoading(false));
  }, [open, profile]);

  const handlePromote = async (versionId: string) => {
    if (!profile) return;
    setPromoting(versionId);
    try {
      await activateVersion(profile.id, versionId);
      toast.success(`Activated version`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to activate version");
    } finally {
      setPromoting(null);
    }
  };

  /**
   * Safely parse the metrics_json field on a version. Returns an empty
   * object if the payload is missing, malformed, or not an object — so
   * the UI never blows up on an old version row.
   */
  const parseMetrics = (v: VersionInfo | undefined): Record<string, unknown> => {
    if (!v?.metrics_json) return {};
    try {
      const parsed = JSON.parse(v.metrics_json);
      return parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>) : {};
    } catch {
      return {};
    }
  };

  const formatMetric = (key: string, val: unknown): string | null => {
    if (val == null) return null;
    if (key === "quality_wer" && typeof val === "number") return `WER ${(val * 100).toFixed(1)}%`;
    if (key === "mos" && typeof val === "number") return `MOS ${val.toFixed(2)}`;
    if (key === "speaker_similarity" && typeof val === "number") return `Similarity ${(val * 100).toFixed(0)}%`;
    if (key === "is_regression") return val ? "⚠ Regression" : "✓ No regression";
    if (key === "method" && typeof val === "string") return `Method: ${val}`;
    if (typeof val === "number") return `${key}: ${val.toFixed(3)}`;
    if (typeof val === "string") return `${key}: ${val}`;
    return null;
  };

  const handleCompare = async () => {
    if (!profile || !selected[0] || !selected[1]) return;
    setComparing(true);
    setResults([]);
    const newResults: typeof results = [];

    for (const versionId of selected) {
      try {
        // Pass version_id directly — does NOT change the profile's active version
        const result = await api.synthesize({ text: testText, profile_id: profile.id, version_id: versionId });
        newResults.push({ version_id: versionId, audio_url: result.audio_url, error: null });
      } catch (e: unknown) {
        const message = e instanceof Error ? getErrorMessage(e) : "Synthesis failed";
        newResults.push({ version_id: versionId, audio_url: null, error: message });
      }
    }

    setResults(newResults);
    setComparing(false);
  };

  const versionOptions = versions.map((v) => ({ value: v.id, label: `v${v.version_number} (${new Date(v.created_at).toLocaleDateString()})` }));

  return (
    <Modal open={open} onClose={onClose} title={`Compare Versions - ${profile?.name ?? ""}`} wide>
      {loading ? (
        <p className="text-sm text-[var(--color-text-secondary)]">Loading versions...</p>
      ) : versions.length < 2 ? (
        <p className="text-sm text-[var(--color-text-secondary)]">Need at least 2 versions to compare.</p>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Version A"
              value={selected[0]}
              onChange={(e) => setSelected([e.target.value, selected[1]])}
              options={[{ value: "", label: "Select..." }, ...versionOptions]}
            />
            <Select
              label="Version B"
              value={selected[1]}
              onChange={(e) => setSelected([selected[0], e.target.value])}
              options={[{ value: "", label: "Select..." }, ...versionOptions]}
            />
          </div>

          {/* Version details side by side */}
          <div className="grid grid-cols-2 gap-4">
            {selected.map((vId, idx) => {
              const v = versions.find((ver) => ver.id === vId);
              const metrics = parseMetrics(v);
              const isActive = profile?.active_version_id === vId;
              return (
                <div
                  key={idx}
                  data-testid={`version-details-${idx}`}
                  className={`rounded border p-3 text-xs space-y-1 ${
                    isActive
                      ? "border-[var(--color-accent)] bg-[var(--color-hover)]"
                      : "border-[var(--color-border)]"
                  }`}
                >
                  {v ? (
                    <>
                      <div className="flex items-center justify-between">
                        <p className="font-medium">Version {v.version_number}</p>
                        {isActive && (
                          <span className="rounded-full bg-[var(--color-success-bg)] px-2 py-0.5 text-[10px] font-medium text-[var(--color-success)]">
                            Active
                          </span>
                        )}
                      </div>
                      {v.provider_name && (
                        <p className="text-[var(--color-text-secondary)]">Provider: {v.provider_name}</p>
                      )}
                      <p className="text-[var(--color-text-secondary)]">
                        Created: {new Date(v.created_at).toLocaleString()}
                      </p>
                      {/* Quality metrics (populated by SL-27 regression detector
                          + per-training Whisper-check). Absent for old rows. */}
                      {Object.keys(metrics).length > 0 && (
                        <ul className="mt-1 space-y-0.5" data-testid={`version-metrics-${idx}`}>
                          {Object.entries(metrics)
                            .map(([k, val]) => formatMetric(k, val))
                            .filter((line): line is string => line != null)
                            .slice(0, 6)
                            .map((line) => (
                              <li
                                key={line}
                                className={
                                  line.startsWith("⚠")
                                    ? "text-amber-500"
                                    : "text-[var(--color-text-secondary)]"
                                }
                              >
                                {line}
                              </li>
                            ))}
                        </ul>
                      )}
                      {!isActive && (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => handlePromote(v.id)}
                          loading={promoting === v.id}
                          disabled={promoting !== null}
                          className="mt-2"
                        >
                          Promote to Active
                        </Button>
                      )}
                    </>
                  ) : (
                    <p className="text-[var(--color-text-secondary)]">Select a version</p>
                  )}
                </div>
              );
            })}
          </div>

          <Input
            label="Test Text"
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
            placeholder="Enter text to synthesize for comparison"
          />

          <Button
            onClick={handleCompare}
            loading={comparing}
            disabled={!selected[0] || !selected[1] || selected[0] === selected[1] || !testText.trim()}
          >
            Synthesize Test
          </Button>

          {results.length > 0 && (
            <div className="grid grid-cols-2 gap-4">
              {results.map((r, idx) => {
                const v = versions.find((ver) => ver.id === r.version_id);
                return (
                  <div key={idx} className="space-y-2">
                    <p className="text-sm font-medium">Version {v?.version_number ?? "?"}</p>
                    {r.error ? (
                      <p className="text-xs text-red-500">{r.error}</p>
                    ) : r.audio_url ? (
                      <AudioPlayer src={r.audio_url} compact />
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}

          <div className="flex justify-end pt-2">
            <Button variant="secondary" onClick={onClose}>Close</Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
