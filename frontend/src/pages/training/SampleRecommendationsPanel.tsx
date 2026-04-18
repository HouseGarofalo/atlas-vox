/**
 * SampleRecommendationsPanel — SL-29 "Record These Next" list.
 *
 * Extracted from TrainingStudioPage.tsx as part of P2-20 (decompose large pages).
 */

import { AlertTriangle, ClipboardCopy } from "lucide-react";
import { Button } from "../../components/ui/Button";

export interface Recommendation {
  text: string;
  fills_gaps: string[];
  gap_fill_count: number;
  priority: number;
}

export interface SampleRecommendationsPanelProps {
  recommendations: Recommendation[];
  method: "phonemizer" | "bigram_approx" | null;
  loading: boolean;
  onRefresh: () => void;
  onCopy: (text: string) => void;
}

export function SampleRecommendationsPanel({
  recommendations,
  method,
  loading,
  onRefresh,
  onCopy,
}: SampleRecommendationsPanelProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)]">
        <span>
          Phoneme-balanced sentences ranked by how many gaps each fills. Record them
          in order for the best-quality voice clone.
        </span>
        <Button variant="ghost" size="sm" onClick={onRefresh} loading={loading}>
          Refresh
        </Button>
      </div>
      {method === "bigram_approx" && (
        <div className="rounded border border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] p-2 text-xs text-[var(--color-warning)]">
          <AlertTriangle className="inline h-3 w-3 mr-1" />
          Using character-bigram fallback — install espeak + phonemizer for full
          phoneme-accurate recommendations.
        </div>
      )}
      {loading ? (
        <p className="text-sm text-[var(--color-text-secondary)]">
          Loading recommendations…
        </p>
      ) : recommendations.length === 0 ? (
        <p className="text-sm text-[var(--color-text-secondary)]">
          No recommendations available. Select a profile or try refreshing.
        </p>
      ) : (
        <ol data-testid="sample-recommendations" className="space-y-2">
          {recommendations.map((r) => (
            <li
              key={`${r.priority}-${r.text}`}
              className="flex items-start gap-3 rounded border border-[var(--color-border)] p-2"
            >
              <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-electric-500/10 text-xs font-medium text-electric-500">
                {r.priority}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-[var(--color-text)]">{r.text}</p>
                {r.gap_fill_count > 0 ? (
                  <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
                    Fills {r.gap_fill_count} phoneme gap
                    {r.gap_fill_count !== 1 ? "s" : ""}
                    {r.fills_gaps.length > 0 && r.fills_gaps.length <= 8 ? (
                      <span className="ml-1 font-mono">
                        ({r.fills_gaps.join(", ")})
                      </span>
                    ) : null}
                  </p>
                ) : (
                  <p className="mt-1 text-xs text-[var(--color-text-tertiary)] italic">
                    Variety pick (no new gaps to fill)
                  </p>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onCopy(r.text)}
                aria-label={`Copy sentence ${r.priority}`}
                title="Copy to clipboard"
              >
                <ClipboardCopy className="h-3 w-3" />
              </Button>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
