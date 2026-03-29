import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Library, Mic, Plus, Trash2, Upload, Volume2 } from "lucide-react";
import { toast } from "sonner";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Modal } from "../components/ui/Modal";
import { useProfileStore } from "../stores/profileStore";
import { useProviderStore } from "../stores/providerStore";
import { createLogger } from "../utils/logger";
import type { VoiceProfile } from "../types";

const logger = createLogger("ProfilesPage");

export default function ProfilesPage() {
  const { profiles, loading, fetchProfiles, createProfile, deleteProfile } = useProfileStore();
  const { providers, fetchProviders } = useProviderStore();
  const navigate = useNavigate();
  const [showCreate, setShowCreate] = useState(false);
  const [createMode, setCreateMode] = useState<"choose" | "training">("choose");
  const [form, setForm] = useState({ name: "", description: "", language: "en", provider_name: "" });

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
    } catch (e: any) {
      logger.error("profile_create_error", { error: e.message });
      toast.error(e.message);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this profile?")) return;
    logger.info("profile_delete", { profile_id: id });
    try {
      await deleteProfile(id);
      toast.success("Profile deleted");
      logger.info("profile_deleted", { profile_id: id });
    } catch (e: any) {
      logger.error("profile_delete_error", { profile_id: id, error: e.message });
      toast.error(e.message);
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
        <p className="text-[var(--color-text-secondary)]">Loading...</p>
      ) : profiles.length === 0 ? (
        <Card className="py-12 text-center">
          <p className="text-[var(--color-text-secondary)]">No profiles yet. Create your first voice profile.</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {profiles.map((profile) => (
            <ProfileCard
              key={profile.id}
              profile={profile}
              onDelete={() => handleDelete(profile.id)}
              onTrain={() => { logger.info("navigate_train", { profile_id: profile.id }); navigate(`/training?profile=${profile.id}`); }}
              onSynthesize={() => { logger.info("navigate_synthesize", { profile_id: profile.id }); navigate(`/synthesis?profile=${profile.id}`); }}
            />
          ))}
        </div>
      )}

      {/* New Profile Modal */}
      <Modal
        open={showCreate}
        onClose={() => { logger.info("modal_close"); setShowCreate(false); setCreateMode("choose"); }}
        title="Create Voice Profile"
      >
        {createMode === "choose" ? (
          <div className="space-y-4">
            <p className="text-sm text-[var(--color-text-secondary)]">
              Choose how to create your voice profile:
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <button
                onClick={() => {
                  setShowCreate(false);
                  setCreateMode("choose");
                  navigate("/voice-library");
                }}
                className="flex flex-col items-center gap-3 rounded-lg border-2 border-[var(--color-border)] p-6 transition-colors hover:border-primary-500 hover:bg-primary-50 dark:hover:bg-primary-950"
              >
                <Library className="h-8 w-8 text-primary-500" />
                <div className="text-center">
                  <h3 className="font-semibold text-[var(--color-text)]">Use Library Voice</h3>
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
            </div>
            <div className="flex justify-end pt-2">
              <Button variant="secondary" onClick={() => { setShowCreate(false); setCreateMode("choose"); }}>
                Cancel
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
}: {
  profile: VoiceProfile;
  onDelete: () => void;
  onTrain: () => void;
  onSynthesize: () => void;
}) {
  const isReady = profile.status === "ready";
  const hasLibraryVoice = !!profile.voice_id;

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
            <span>{profile.version_count} versions</span>
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
        <Button size="sm" variant="ghost" onClick={onDelete}>
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>
    </Card>
  );
});
