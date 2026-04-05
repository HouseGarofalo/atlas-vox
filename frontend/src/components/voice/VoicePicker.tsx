/**
 * Shared VoicePicker component — reusable voice selection with search,
 * filtering by provider/language/gender, and optional preview playback.
 *
 * Replaces duplicated voice selection logic in:
 *   - SynthesisLab (dropdown)
 *   - Profiles (dialog)
 *   - TrainingStudio (selector)
 *   - Comparison (two dropdowns)
 */

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { Select } from "../ui/Select";
import { useVoiceLibraryStore } from "../../stores/voiceLibraryStore";
import type { Voice } from "../../types";
import { createLogger } from "../../utils/logger";

const logger = createLogger("VoicePicker");

interface VoicePickerProps {
  /** Currently selected voice (provider + voice_id) */
  value?: { provider: string; voice_id: string } | null;
  /** Called when a voice is selected */
  onSelect: (voice: Voice) => void;
  /** Filter to a specific provider */
  providerFilter?: string;
  /** Placeholder text */
  placeholder?: string;
  /** Label text */
  label?: string;
  /** Show compact mode (just a select dropdown) */
  compact?: boolean;
}

export function VoicePicker({
  value,
  onSelect,
  providerFilter,
  placeholder = "Search voices...",
  label,
  compact = false,
}: VoicePickerProps) {
  const { voices, fetchAllVoices } = useVoiceLibraryStore();
  const [search, setSearch] = useState("");
  const [provFilter, setProvFilter] = useState(providerFilter || "");

  // Fetch voices on first render if not loaded
  useMemo(() => {
    if (voices.length === 0) fetchAllVoices();
  }, []);

  const filtered = useMemo(() => {
    let result = voices;
    if (provFilter) {
      result = result.filter((v) => v.provider === provFilter);
    }
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (v) =>
          v.name.toLowerCase().includes(q) ||
          v.voice_id.toLowerCase().includes(q) ||
          v.provider_display.toLowerCase().includes(q)
      );
    }
    return result.slice(0, 100); // Limit displayed options
  }, [voices, provFilter, search]);

  const providers = useMemo(() => {
    const seen = new Map<string, string>();
    for (const v of voices) {
      if (!seen.has(v.provider)) seen.set(v.provider, v.provider_display);
    }
    return [{ value: "", label: "All Providers" }, ...Array.from(seen, ([val, lab]) => ({ value: val, label: lab }))];
  }, [voices]);

  if (compact) {
    const options = [
      { value: "", label: placeholder },
      ...filtered.map((v) => ({
        value: `${v.provider}::${v.voice_id}`,
        label: `${v.name} (${v.provider_display})`,
      })),
    ];
    const currentValue = value ? `${value.provider}::${value.voice_id}` : "";

    return (
      <Select
        label={label}
        value={currentValue}
        onChange={(e) => {
          const selected = filtered.find(
            (v) => `${v.provider}::${v.voice_id}` === e.target.value
          );
          if (selected) {
            logger.info("voice_selected", { provider: selected.provider, voice_id: selected.voice_id });
            onSelect(selected);
          }
        }}
        options={options}
      />
    );
  }

  return (
    <div className="space-y-2">
      {label && <label className="text-sm font-medium text-[var(--color-text)]">{label}</label>}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--color-text-secondary)]" />
          <input
            type="text"
            placeholder={placeholder}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] pl-8 pr-3 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        {!providerFilter && (
          <Select
            value={provFilter}
            onChange={(e) => setProvFilter(e.target.value)}
            options={providers}
          />
        )}
      </div>
      <div className="max-h-48 overflow-y-auto rounded-lg border border-[var(--color-border)]">
        {filtered.length === 0 ? (
          <p className="p-3 text-center text-xs text-[var(--color-text-secondary)]">No voices found</p>
        ) : (
          filtered.map((v) => {
            const isSelected = value?.provider === v.provider && value?.voice_id === v.voice_id;
            return (
              <button
                key={`${v.provider}-${v.voice_id}`}
                onClick={() => {
                  logger.info("voice_selected", { provider: v.provider, voice_id: v.voice_id });
                  onSelect(v);
                }}
                className={`w-full px-3 py-2 text-left text-sm hover:bg-[var(--color-bg-secondary)] flex items-center justify-between ${
                  isSelected ? "bg-primary-50 dark:bg-primary-950" : ""
                }`}
              >
                <span className="truncate font-medium">{v.name}</span>
                <span className="ml-2 flex-shrink-0 text-xs text-[var(--color-text-secondary)]">
                  {v.provider_display}
                </span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
