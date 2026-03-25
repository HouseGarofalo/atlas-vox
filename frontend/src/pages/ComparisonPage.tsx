import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { TextArea } from "../components/ui/TextArea";
import { AudioPlayer } from "../components/audio/AudioPlayer";
import { useProfileStore } from "../stores/profileStore";
import { useSynthesisStore } from "../stores/synthesisStore";

export default function ComparisonPage() {
  const { profiles, fetchProfiles } = useProfileStore();
  const { comparing, comparisonResults, compare } = useSynthesisStore();
  const [text, setText] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => { fetchProfiles(); }, []);

  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelected(next);
  };

  const handleCompare = async () => {
    if (!text.trim()) { toast.error("Enter text to compare"); return; }
    if (selected.size < 2) { toast.error("Select at least 2 profiles"); return; }
    try { await compare({ text, profile_ids: Array.from(selected) }); } catch (e: any) { toast.error(e.message); }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Voice Comparison</h1>
      <Card>
        <TextArea label="Text to compare" rows={3} value={text} onChange={(e) => setText(e.target.value)} placeholder="Enter text to synthesize across multiple voices..." />
      </Card>
      <Card>
        <h3 className="mb-3 text-sm font-semibold">Select Voices ({selected.size} selected)</h3>
        <div className="flex flex-wrap gap-2">
          {profiles.map((p) => (
            <button key={p.id} onClick={() => toggle(p.id)} className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${selected.has(p.id) ? "border-primary-500 bg-primary-50 text-primary-700 dark:bg-primary-900 dark:text-primary-300" : "border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-gray-400"}`}>
              {p.name}
            </button>
          ))}
        </div>
      </Card>
      <Button onClick={handleCompare} disabled={comparing || selected.size < 2 || !text.trim()}>
        {comparing ? "Generating..." : "Generate All"}
      </Button>
      {comparisonResults.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {comparisonResults.map((r: any) => (
            <Card key={r.profile_id}>
              <div className="mb-2 flex items-center justify-between">
                <h3 className="font-semibold">{r.profile_name}</h3>
                <span className="text-xs text-[var(--color-text-secondary)]">{r.provider_name} &middot; {r.latency_ms}ms</span>
              </div>
              {r.audio_url && <AudioPlayer src={r.audio_url} />}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
