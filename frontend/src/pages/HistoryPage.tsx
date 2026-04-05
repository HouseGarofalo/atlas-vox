import { useEffect, useState } from "react";
import { Clock, Download, Play, Pause, RefreshCw } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Select } from "../components/ui/Select";
import { Badge } from "../components/ui/Badge";
import { useAudioPlayer } from "../hooks/useAudioPlayer";
import { api } from "../services/api";
import { createLogger } from "../utils/logger";
import { getErrorMessage } from "../utils/errors";
import type { SynthesisHistoryItem } from "../types";

const logger = createLogger("HistoryPage");

export default function HistoryPage() {
  const [history, setHistory] = useState<SynthesisHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [providerFilter, setProviderFilter] = useState("");
  const { isPlaying, currentUrl, toggle } = useAudioPlayer();

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const items = await api.getSynthesisHistory(100);
      logger.info("history_loaded", { count: items.length });
      setHistory(items);
    } catch (e: unknown) {
      logger.error("history_load_failed", { error: getErrorMessage(e) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchHistory(); }, []);

  const filtered = providerFilter
    ? history.filter((h) => h.provider_name === providerFilter)
    : history;

  const providers = [...new Set(history.map((h) => h.provider_name))].sort();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Synthesis History</h1>
        <Button variant="secondary" onClick={fetchHistory} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <div className="flex gap-3">
        <Select
          value={providerFilter}
          onChange={(e) => setProviderFilter(e.target.value)}
          options={[
            { value: "", label: "All Providers" },
            ...providers.map((p) => ({ value: p, label: p })),
          ]}
        />
        <p className="self-center text-sm text-[var(--color-text-secondary)]">
          {filtered.length} of {history.length} entries
        </p>
      </div>

      {loading && history.length === 0 && (
        <Card className="py-12 text-center">
          <div className="h-6 w-6 mx-auto animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
        </Card>
      )}

      {!loading && history.length === 0 && (
        <Card className="py-12 text-center">
          <Clock className="mx-auto h-10 w-10 text-[var(--color-text-secondary)] mb-3" />
          <p className="text-[var(--color-text-secondary)]">No synthesis history yet. Try synthesizing some text first.</p>
        </Card>
      )}

      <div className="space-y-2">
        {filtered.map((item) => (
          <Card key={item.id} className="flex items-center gap-4 p-3">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => item.audio_url && toggle(item.audio_url)}
              disabled={!item.audio_url}
              className="flex-shrink-0"
            >
              {isPlaying && currentUrl === item.audio_url ? (
                <Pause className="h-3.5 w-3.5" />
              ) : (
                <Play className="h-3.5 w-3.5" />
              )}
            </Button>

            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{item.text}</p>
              <div className="mt-1 flex gap-2 text-xs text-[var(--color-text-secondary)]">
                <Badge status={item.provider_name} />
                {item.latency_ms && <span>{item.latency_ms}ms</span>}
                <span>{new Date(item.created_at).toLocaleString()}</span>
              </div>
            </div>

            {item.audio_url && (
              <a
                href={item.audio_url}
                download
                className="flex-shrink-0 text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
              >
                <Download className="h-4 w-4" />
              </a>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
