import { useEffect, useMemo, useState } from "react";
import { Sparkles, SlidersHorizontal } from "lucide-react";
import { api } from "../../services/api";
import { createLogger } from "../../utils/logger";

const logger = createLogger("ProsodyPreview");

interface ProsodyWord {
  index: number;
  text: string;
  pitch: number;
  energy: number;
  duration_ms: number;
  syllables: number;
  is_sentence_end: boolean;
  emphasis: "normal" | "reduced" | "strong";
  reasons: string[];
}

interface ProsodyResponse {
  text: string;
  emotion: string | null;
  words: ProsodyWord[];
  sentence_count: number;
  total_duration_ms: number;
  pitch_min: number;
  pitch_max: number;
  ssml: string;
  supported_emotions: string[];
}

export interface ProsodyPreviewProps {
  /** Current input text. Updates trigger a debounced preview re-fetch. */
  text: string;
  /** Optional Azure emotion label overlaid on the heuristic. */
  emotion?: string | null;
  /**
   * Called whenever the preview (including user emphasis edits) produces a
   * fresh SSML string the parent can feed into synthesize(). Optional —
   * if omitted the panel is purely informational.
   */
  onSsmlChange?: (ssml: string) => void;
  /** Optional callback when the user changes the emotion dropdown. */
  onEmotionChange?: (emotion: string | null) => void;
}

/**
 * VQ-37 — prosody/emotion visual preview.
 *
 * Renders a tappable word timeline with pitch contour, energy bars, and
 * duration-proportional widths. Clicking a word cycles its emphasis
 * (reduced → normal → strong) and the panel re-fetches the preview so
 * SSML + durations stay in sync. No audio is generated — the preview is
 * a pure prediction users can tweak before calling synthesize().
 */
export function ProsodyPreview({
  text,
  emotion,
  onSsmlChange,
  onEmotionChange,
}: ProsodyPreviewProps) {
  const [preview, setPreview] = useState<ProsodyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // User-selected emphasis per word index. Defaults to the heuristic
  // value; explicit overrides persist across preview refreshes.
  const [overrides, setOverrides] = useState<Record<number, string>>({});

  // Debounced fetch.
  useEffect(() => {
    const trimmed = text.trim();
    if (!trimmed) {
      setPreview(null);
      return;
    }
    const handle = setTimeout(() => {
      setLoading(true);
      setError(null);
      api
        .prosodyPreview(trimmed, { emotion, emphasis: overrides })
        .then((res) => {
          setPreview(res);
          onSsmlChange?.(res.ssml);
          logger.info("prosody_preview_ok", {
            word_count: res.words.length,
            duration_ms: res.total_duration_ms,
          });
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : "Preview unavailable");
          logger.warn("prosody_preview_failed", { error: String(err) });
        })
        .finally(() => setLoading(false));
    }, 400);
    return () => clearTimeout(handle);
  }, [text, emotion, overrides, onSsmlChange]);

  const cycleEmphasis = (idx: number, current: string) => {
    const next =
      current === "normal" ? "strong" : current === "strong" ? "reduced" : "normal";
    setOverrides((prev) => ({ ...prev, [idx]: next }));
  };

  // SVG pitch contour path — built once per preview for performance.
  const pitchPath = useMemo(() => {
    if (!preview?.words.length) return { line: "", points: [] };
    const height = 80;
    const pad = 8;
    const domain = Math.max(0.4, Math.max(...preview.words.map((w) => Math.abs(w.pitch))));
    const step = 100 / Math.max(1, preview.words.length - 1);
    const points = preview.words.map((w, i) => {
      const x = i * step;
      // Map pitch [-domain, +domain] into y [height-pad, pad] (invert: higher pitch = higher on screen)
      const normalized = (w.pitch + domain) / (2 * domain);
      const y = height - pad - normalized * (height - 2 * pad);
      return { x, y, word: w };
    });
    const line = points
      .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
      .join(" ");
    return { line, points };
  }, [preview]);

  if (!text.trim()) return null;

  return (
    <div
      data-testid="prosody-preview"
      className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-3 space-y-3"
    >
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <SlidersHorizontal className="h-4 w-4 text-electric-500" />
          <span>Prosody Preview</span>
          {preview && (
            <span className="text-xs text-[var(--color-text-secondary)]">
              · {preview.words.length} words · {(preview.total_duration_ms / 1000).toFixed(1)}s predicted
            </span>
          )}
        </div>
        {preview && preview.supported_emotions.length > 0 && onEmotionChange && (
          <label className="flex items-center gap-2 text-xs text-[var(--color-text-secondary)]">
            <Sparkles className="h-3 w-3" />
            Emotion
            <select
              value={emotion ?? ""}
              onChange={(e) => onEmotionChange(e.target.value || null)}
              className="rounded border border-[var(--color-border)] bg-[var(--color-bg)] px-2 py-0.5 text-xs"
            >
              <option value="">(none)</option>
              {preview.supported_emotions.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </label>
        )}
      </header>

      {error && (
        <p className="text-xs text-red-500">{error}</p>
      )}

      {preview && preview.words.length > 0 && (
        <>
          <svg
            data-testid="prosody-sparkline"
            viewBox="0 0 100 80"
            preserveAspectRatio="none"
            className="w-full h-20 text-electric-500"
            aria-label="Predicted pitch contour"
          >
            <path d={pitchPath.line} fill="none" stroke="currentColor" strokeWidth="0.8" />
            {pitchPath.points.map((p) => (
              <circle
                key={p.word.index}
                cx={p.x}
                cy={p.y}
                r={p.word.emphasis === "strong" ? 1.6 : p.word.emphasis === "reduced" ? 0.8 : 1.2}
                fill="currentColor"
                opacity={p.word.emphasis === "reduced" ? 0.4 : 1}
              />
            ))}
          </svg>

          <div
            data-testid="prosody-word-timeline"
            className="flex flex-wrap gap-1 text-sm"
          >
            {preview.words.map((w) => {
              const shade = Math.round(w.energy * 100);
              const tone =
                w.emphasis === "strong"
                  ? "border-electric-500 bg-electric-500/20"
                  : w.emphasis === "reduced"
                    ? "border-[var(--color-border)] opacity-50"
                    : "border-[var(--color-border)]";
              const title =
                `${w.text} — pitch ${w.pitch.toFixed(2)}, ` +
                `energy ${w.energy.toFixed(2)}, ${w.duration_ms}ms, ` +
                `${w.syllables} syl · click to cycle emphasis`;
              return (
                <button
                  key={w.index}
                  type="button"
                  onClick={() => cycleEmphasis(w.index, w.emphasis)}
                  title={title}
                  aria-label={title}
                  data-emphasis={w.emphasis}
                  className={`rounded border px-1.5 py-0.5 transition-all hover:border-electric-500 ${tone}`}
                  style={{
                    // Proportional width based on syllables — visual cue
                    // that longer words take longer to say.
                    minWidth: `${Math.max(24, w.syllables * 16)}px`,
                  }}
                >
                  <span>{w.text}</span>
                  <span
                    aria-hidden="true"
                    className="ml-1 inline-block h-1 w-4 rounded-full bg-primary-500"
                    style={{ opacity: 0.2 + (shade / 100) * 0.8 }}
                  />
                </button>
              );
            })}
          </div>

          <p className="text-xs text-[var(--color-text-tertiary)]">
            Click a word to cycle its emphasis (normal → strong → reduced).
            SSML updates live.
          </p>
        </>
      )}

      {loading && !preview && (
        <div className="h-20 w-full animate-pulse rounded bg-[var(--color-bg-tertiary)]" />
      )}
    </div>
  );
}
