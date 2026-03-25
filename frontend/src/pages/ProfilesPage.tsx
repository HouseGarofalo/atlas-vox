import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Modal } from "../components/ui/Modal";
import { useProfileStore } from "../stores/profileStore";
import { useProviderStore } from "../stores/providerStore";
import type { VoiceProfile } from "../types";

export default function ProfilesPage() {
  const { profiles, loading, fetchProfiles, createProfile, deleteProfile } = useProfileStore();
  const { providers, fetchProviders } = useProviderStore();
  const navigate = useNavigate();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", language: "en", provider_name: "kokoro" });

  useEffect(() => {
    fetchProfiles();
    fetchProviders();
  }, []);

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    try {
      await createProfile(form);
      toast.success("Profile created");
      setShowCreate(false);
      setForm({ name: "", description: "", language: "en", provider_name: "kokoro" });
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this profile?")) return;
    try {
      await deleteProfile(id);
      toast.success("Profile deleted");
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const providerOptions = providers
    .filter((p) => p.enabled)
    .map((p) => ({ value: p.name, label: p.display_name }));
  if (!providerOptions.length) providerOptions.push({ value: "kokoro", label: "Kokoro" });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Voice Profiles</h1>
        <Button onClick={() => setShowCreate(true)}>
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
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {profiles.map((profile) => (
            <ProfileCard
              key={profile.id}
              profile={profile}
              onDelete={() => handleDelete(profile.id)}
              onTrain={() => navigate(`/training?profile=${profile.id}`)}
            />
          ))}
        </div>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Voice Profile">
        <div className="space-y-4">
          <Input label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="My Voice" />
          <Input label="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Optional description" />
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
          <Select label="Provider" value={form.provider_name} onChange={(e) => setForm({ ...form, provider_name: e.target.value })} options={providerOptions} />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={handleCreate}>Create</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function ProfileCard({ profile, onDelete, onTrain }: { profile: VoiceProfile; onDelete: () => void; onTrain: () => void }) {
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold">{profile.name}</h3>
          <p className="text-xs text-[var(--color-text-secondary)]">{profile.provider_name} &middot; {profile.language}</p>
        </div>
        <Badge status={profile.status} />
      </div>
      {profile.description && <p className="text-sm text-[var(--color-text-secondary)] line-clamp-2">{profile.description}</p>}
      <div className="flex gap-4 text-xs text-[var(--color-text-secondary)]">
        <span>{profile.sample_count} samples</span>
        <span>{profile.version_count} versions</span>
      </div>
      <div className="flex gap-2 mt-auto pt-2 border-t border-[var(--color-border)]">
        <Button size="sm" variant="secondary" onClick={onTrain}><Upload className="h-3 w-3" /> Train</Button>
        <Button size="sm" variant="ghost" onClick={onDelete}><Trash2 className="h-3 w-3" /></Button>
      </div>
    </Card>
  );
}
