import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Type, Users, BarChart3 } from "lucide-react";
import { Button } from "../components/ui/Button";
import { TextArea } from "../components/ui/TextArea";
import { AudioPlayer } from "../components/audio/AudioPlayer";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import { useProfileStore } from "../stores/profileStore";
import { useSynthesisStore } from "../stores/synthesisStore";
import type { ComparisonResult } from "../types";
import { createLogger } from "../utils/logger";

const logger = createLogger("ComparisonPage");

export default function ComparisonPage() {
  const { profiles, fetchProfiles } = useProfileStore();
  const { comparing, comparisonResults, compare } = useSynthesisStore();
  const [text, setText] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => { fetchProfiles(); }, []);

  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    logger.info("profile_toggle", { profile_id: id, selected: next.has(id), total_selected: next.size });
    setSelected(next);
  };

  const handleCompare = async () => {
    if (!text.trim()) { toast.error("Enter text to compare"); return; }
    if (selected.size < 2) { toast.error("Select at least 2 profiles"); return; }
    logger.info("compare_start", { profile_count: selected.size, text_length: text.length });
    try {
      await compare({ text, profile_ids: Array.from(selected) });
      logger.info("compare_complete", { profile_count: selected.size });
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Comparison failed";
      logger.error("compare_error", { error: message });
      toast.error(message);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Voice Comparison</h1>

      <CollapsiblePanel title="Input Text" icon={<Type className="h-4 w-4 text-primary-500" />}>
        <TextArea label="Text to compare" rows={3} value={text} onChange={(e) => setText(e.target.value)} placeholder="Enter text to synthesize across multiple voices..." />
      </CollapsiblePanel>

      <CollapsiblePanel
        title={`Voice Selection (${selected.size} selected)`}
        icon={<Users className="h-4 w-4 text-blue-500" />}
      >
        <div className="flex flex-wrap gap-2">
          {profiles.map((p) => (
            <button key={p.id} onClick={() => toggle(p.id)} className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${selected.has(p.id) ? "border-primary-500 bg-primary-50 text-primary-700 dark:bg-primary-900 dark:text-primary-300" : "border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-gray-400"}`}>
              {p.name}
            </button>
          ))}
        </div>
      </CollapsiblePanel>

      <Button onClick={handleCompare} disabled={comparing || selected.size < 2 || !text.trim()}>
        {comparing ? "Generating..." : "Generate All"}
      </Button>

      {comparisonResults.length > 0 && (
        <CollapsiblePanel title="Results" icon={<BarChart3 className="h-4 w-4 text-green-500" />}>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {comparisonResults.map((r: ComparisonResult) => (
              <div key={r.profile_id} className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] p-4">
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="font-semibold">{r.profile_name}</h3>
                  <span className="text-xs text-[var(--color-text-secondary)]">{r.provider_name} &middot; {r.latency_ms}ms</span>
                </div>
                {r.audio_url && <AudioPlayer src={r.audio_url} />}
              </div>
            ))}
          </div>
        </CollapsiblePanel>
      )}
    </div>
  );
}
