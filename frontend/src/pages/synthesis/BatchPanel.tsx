import { Layers, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { CollapsiblePanel } from "../../components/ui/CollapsiblePanel";
import { ProgressBar } from "../../components/ui/ProgressBar";
import { AudioPlayer } from "../../components/audio/AudioPlayer";
import WaveformVisualizer from "../../components/audio/WaveformVisualizer";
import type { BatchPanelProps } from "./types";

export default function BatchPanel({
  batchText,
  onSetBatchText,
  batchLoading,
  batchProgress,
  batchResults,
}: BatchPanelProps) {
  const lineCount = batchText.split("\n").filter((l) => l.trim().length > 0).length;

  return (
    <>
      <CollapsiblePanel
        title="Batch Input"
        icon={<Layers className="h-5 w-5 text-primary-500" />}
      >
        <div className="space-y-4">
          <p className="text-sm text-[var(--color-text-secondary)]">
            Enter one line per synthesis. Each line will be processed independently.
          </p>
          <textarea
            value={batchText}
            onChange={(e) => onSetBatchText(e.target.value)}
            placeholder={
              "Hello, welcome to the demo.\nThis is line two.\nAnd a third line for good measure."
            }
            rows={10}
            className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-4 py-3 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-secondary)] focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 resize-y"
          />
          <div className="flex items-center justify-between text-sm text-[var(--color-text-secondary)]">
            <span>{lineCount} lines</span>
            <span>{batchText.length} characters</span>
          </div>
        </div>
      </CollapsiblePanel>

      {batchLoading && (
        <Card>
          <ProgressBar percent={batchProgress} label="Batch Processing" />
          <div className="mt-4 flex justify-center">
            <WaveformVisualizer height={32} barCount={24} animated color="primary" />
          </div>
        </Card>
      )}

      {batchResults.length > 0 && (
        <CollapsiblePanel
          title={`Batch Results (${batchResults.filter((r) => r.status === "success").length}/${batchResults.length} succeeded)`}
          icon={<CheckCircle2 className="h-5 w-5 text-green-500" />}
        >
          <div className="space-y-4 max-h-96 overflow-y-auto">
            {batchResults.map((result, i) => (
              <Card key={`batch-${i}`} className="p-4 space-y-3">
                <div className="flex items-start gap-3">
                  {result.status === "success" ? (
                    <CheckCircle2 className="h-5 w-5 shrink-0 text-green-500 mt-0.5" />
                  ) : result.status === "error" ? (
                    <XCircle className="h-5 w-5 shrink-0 text-red-500 mt-0.5" />
                  ) : (
                    <Loader2 className="h-5 w-5 shrink-0 text-gray-400 animate-spin mt-0.5" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{result.line}</p>
                    {result.latency_ms != null && (
                      <p className="text-xs text-[var(--color-text-secondary)] mt-1">
                        Latency: {result.latency_ms}ms
                      </p>
                    )}
                    {result.error && (
                      <p className="text-xs text-red-500 mt-1">{result.error}</p>
                    )}
                  </div>
                </div>
                {result.status === "success" && result.audio_url && (
                  <AudioPlayer src={result.audio_url} compact />
                )}
              </Card>
            ))}
          </div>
        </CollapsiblePanel>
      )}
    </>
  );
}
