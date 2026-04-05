import { useEffect, useState } from "react";
import { BookOpen, Download, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { api } from "../services/api";
import { createLogger } from "../utils/logger";
import { getErrorMessage } from "../utils/errors";

const logger = createLogger("PronunciationPage");

interface PronEntry {
  id: string;
  word: string;
  ipa: string;
  language: string;
  profile_id: string | null;
  created_at: string;
  updated_at: string;
}

export default function PronunciationPage() {
  const [entries, setEntries] = useState<PronEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [newWord, setNewWord] = useState("");
  const [newIpa, setNewIpa] = useState("");

  const fetchEntries = async () => {
    setLoading(true);
    try {
      const data = await api.listPronunciation({ search: search || undefined });
      setEntries(data.entries);
    } catch (e: unknown) {
      logger.error("fetch_failed", { error: getErrorMessage(e) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchEntries(); }, []);

  const handleAdd = async () => {
    if (!newWord.trim() || !newIpa.trim()) return;
    try {
      await api.createPronunciation({ word: newWord.trim(), ipa: newIpa.trim() });
      toast.success(`Added pronunciation for "${newWord}"`);
      setNewWord("");
      setNewIpa("");
      fetchEntries();
    } catch (e: unknown) {
      toast.error(getErrorMessage(e));
    }
  };

  const handleDelete = async (id: string, word: string) => {
    try {
      await api.deletePronunciation(id);
      toast.success(`Removed "${word}"`);
      setEntries((prev) => prev.filter((e) => e.id !== id));
    } catch (e: unknown) {
      toast.error(getErrorMessage(e));
    }
  };

  const handleSearch = () => { fetchEntries(); };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Pronunciation Dictionary</h1>
          <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
            Define custom pronunciations for names, acronyms, and domain-specific terms.
            Entries are automatically applied as SSML phoneme tags during synthesis.
          </p>
        </div>
        <div className="flex gap-2">
          <a href="/api/v1/pronunciation/export" download>
            <Button variant="secondary" size="sm">
              <Download className="h-4 w-4" /> Export CSV
            </Button>
          </a>
        </div>
      </div>

      {/* Add new entry */}
      <Card>
        <h3 className="text-sm font-semibold mb-3">Add Pronunciation</h3>
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <Input
              label="Word"
              value={newWord}
              onChange={(e) => setNewWord(e.target.value)}
              placeholder='e.g., "GIF"'
            />
          </div>
          <div className="flex-1">
            <Input
              label="IPA Pronunciation"
              value={newIpa}
              onChange={(e) => setNewIpa(e.target.value)}
              placeholder='e.g., "/dʒɪf/"'
            />
          </div>
          <Button onClick={handleAdd} disabled={!newWord.trim() || !newIpa.trim()}>
            <Plus className="h-4 w-4" /> Add
          </Button>
        </div>
      </Card>

      {/* Search */}
      <div className="flex gap-3">
        <div className="flex-1">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search words..."
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
        </div>
        <Button variant="secondary" onClick={handleSearch}>Search</Button>
      </div>

      {/* Entries table */}
      {loading ? (
        <Card className="py-8 text-center text-[var(--color-text-secondary)]">Loading...</Card>
      ) : entries.length === 0 ? (
        <Card className="py-12 text-center">
          <BookOpen className="mx-auto h-10 w-10 text-[var(--color-text-secondary)] mb-3" />
          <p className="text-[var(--color-text-secondary)]">
            No pronunciation entries yet. Add words above to customize how they're spoken.
          </p>
        </Card>
      ) : (
        <div className="overflow-hidden rounded-lg border border-[var(--color-border)]">
          <table className="w-full text-sm">
            <thead className="bg-[var(--color-bg-secondary)]">
              <tr>
                <th className="px-4 py-2 text-left font-medium">Word</th>
                <th className="px-4 py-2 text-left font-medium">IPA</th>
                <th className="px-4 py-2 text-left font-medium">Language</th>
                <th className="px-4 py-2 w-16" />
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {entries.map((entry) => (
                <tr key={entry.id} className="hover:bg-[var(--color-bg-secondary)]">
                  <td className="px-4 py-2 font-medium">{entry.word}</td>
                  <td className="px-4 py-2 font-mono text-[var(--color-text-secondary)]">{entry.ipa}</td>
                  <td className="px-4 py-2 text-[var(--color-text-secondary)]">{entry.language}</td>
                  <td className="px-4 py-2">
                    <button
                      onClick={() => handleDelete(entry.id, entry.word)}
                      className="text-[var(--color-text-secondary)] hover:text-red-500"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-[var(--color-text-secondary)]">
        {entries.length} entries. Pronunciations are applied automatically to all synthesis requests using SSML &lt;phoneme&gt; tags.
      </p>
    </div>
  );
}
