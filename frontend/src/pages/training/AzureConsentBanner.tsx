/**
 * AzureConsentBanner — warning banner shown when an Azure Custom Voice
 * profile is selected, reminding the user to upload a consent recording.
 *
 * Extracted from TrainingStudioPage.tsx as part of P2-20 (decompose large pages).
 */

import { AlertTriangle } from "lucide-react";

export function AzureConsentBanner() {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] p-4">
      <AlertTriangle className="h-5 w-5 shrink-0 text-[var(--color-warning)] mt-0.5" />
      <div className="text-sm text-[var(--color-warning)]">
        <p className="font-semibold mb-1">Azure Custom Voice — Consent Required</p>
        <p>
          Your <strong>first uploaded sample</strong> must be a consent recording.
          Record yourself reading:
        </p>
        <p className="mt-1 italic text-xs">
          "I [your full name] am aware that recordings of my voice will be used by
          [company name] to create and use a synthetic version of my voice."
        </p>
        <p className="mt-1 text-xs">
          Upload the consent recording first, then add your voice samples (5-90
          seconds each). Minimum 2 files total.
        </p>
      </div>
    </div>
  );
}
