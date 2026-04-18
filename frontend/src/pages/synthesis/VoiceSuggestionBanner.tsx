import { useEffect, useState } from "react";
import { Sparkles, X } from "lucide-react";
import { api } from "../../services/api";
import { createLogger } from "../../utils/logger";

const logger = createLogger("VoiceSuggestionBanner");

interface VoiceSuggestionBannerProps {
  /** Current text the user is editing; banner re-evaluates as this changes. */
  text: string;
  /** Currently-selected profile id — suppressed when already on the top suggestion. */
  currentProfileId: string;
  /** Hand the user's accepted choice back to the page state. */
  onAccept: (profileId: string) => void;
}

/**
 * SL-30 "Atlas suggests…" banner.
 *
 * Fetches a provider/voice routing suggestion whenever the input text
 * stabilises for ~500ms. Hides itself when the user is already on the
 * recommended profile or dismisses it. Non-blocking — failures are
 * silent (this is advisory UI, not a hard gate).
 */
export function VoiceSuggestionBanner({
  text,
  currentProfileId,
  onAccept,
}: VoiceSuggestionBannerProps) {
  const [suggestion, setSuggestion] = useState<{
    profile_id: string;
    profile_name: string;
    provider_name: string;
    top_context: string;
  } | null>(null);
  const [dismissed, setDismissed] = useState<string | null>(null);

  useEffect(() => {
    const trimmed = text.trim();
    if (trimmed.length < 20) {
      setSuggestion(null);
      return;
    }
    // Debounce rapid typing — waiting ~500ms avoids flooding the backend
    // during text entry. The api client's cancelKey also aborts prior
    // in-flight calls if the timer still fires.
    const handle = setTimeout(() => {
      api
        .recommendVoice(trimmed, 3)
        .then((res) => {
          if (!res.recommendations || res.recommendations.length === 0) {
            setSuggestion(null);
            return;
          }
          const top = res.recommendations[0];
          setSuggestion({
            profile_id: top.profile_id,
            profile_name: top.profile_name,
            provider_name: top.provider_name,
            top_context: res.top_context,
          });
          logger.info("voice_suggestion", {
            context: res.top_context,
            profile: top.profile_name,
          });
        })
        .catch(() => {
          /* Silent — advisory UI. */
        });
    }, 500);
    return () => clearTimeout(handle);
  }, [text]);

  if (!suggestion) return null;
  if (dismissed === suggestion.profile_id) return null;
  // Don't nag the user if they're already on the top pick.
  if (currentProfileId && currentProfileId === suggestion.profile_id) return null;

  const contextLabel = suggestion.top_context.replace("_", " ");

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="voice-suggestion-banner"
      className="flex items-center gap-3 rounded-lg border border-[var(--color-border)] bg-gradient-to-r from-electric-500/10 to-primary-500/10 px-3 py-2 text-sm"
    >
      <Sparkles className="h-4 w-4 shrink-0 text-electric-500" />
      <div className="flex-1 min-w-0">
        <span className="text-[var(--color-text-secondary)]">
          Atlas suggests{" "}
        </span>
        <span className="font-medium text-[var(--color-text)]">
          {suggestion.profile_name}
        </span>
        <span className="text-[var(--color-text-secondary)]">
          {" "}for this {contextLabel} text.
        </span>
      </div>
      <button
        onClick={() => onAccept(suggestion.profile_id)}
        className="rounded-md bg-electric-500 px-3 py-1 text-xs font-medium text-white hover:bg-electric-600 transition-colors"
      >
        Use it
      </button>
      <button
        onClick={() => setDismissed(suggestion.profile_id)}
        className="rounded-md p-1 text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
        aria-label="Dismiss suggestion"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
