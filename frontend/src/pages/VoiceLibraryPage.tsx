import React, { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, Pause, Play, RefreshCw, Search, UserPlus } from "lucide-react";
import { toast } from "sonner";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Select } from "../components/ui/Select";
import { Badge } from "../components/ui/Badge";
import ProviderLogo from "../components/providers/ProviderLogo";
import { useVoiceLibraryStore } from "../stores/voiceLibraryStore";
import { useProfileStore } from "../stores/profileStore";
import { api } from "../services/api";
import { createLogger } from "../utils/logger";
import type { Voice } from "../types";

const logger = createLogger("VoiceLibraryPage");

export default function VoiceLibraryPage() {
  const {
    voices,
    loading,
    error,
    filters,
    fetchAllVoices,
    setFilter,
    filteredVoices,
  } = useVoiceLibraryStore();
  const { createProfile } = useProfileStore();
  const navigate = useNavigate();

  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const [searchInput, setSearchInput] = useState(filters.search);

  const handleSearch = (value: string) => {
    setSearchInput(value);
    clearTimeout(searchTimeoutRef.current);
    searchTimeoutRef.current = setTimeout(() => {
      setFilter("search", value);
    }, 300);
  };

  useEffect(() => {
    logger.info("page_mounted");
    fetchAllVoices();
    return () => clearTimeout(searchTimeoutRef.current);
  }, []);

  const displayed = useMemo(() => filteredVoices(), [voices, filters]);

  // Derive unique providers for the filter dropdown
  const providerOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const v of voices) {
      if (!seen.has(v.provider)) {
        seen.set(v.provider, v.provider_display);
      }
    }
    const opts = [{ value: "", label: "All Providers" }];
    for (const [value, label] of seen) {
      opts.push({ value, label });
    }
    return opts;
  }, [voices]);

  // Derive unique languages for the filter dropdown
  const languageOptions = useMemo(() => {
    const langs = new Set<string>();
    for (const v of voices) {
      if (v.language) langs.add(v.language);
    }
    const opts = [{ value: "", label: "All Languages" }];
    for (const lang of Array.from(langs).sort()) {
      opts.push({ value: lang, label: languageLabel(lang) });
    }
    return opts;
  }, [voices]);

  // Derive unique genders for the filter dropdown
  const genderOptions = useMemo(() => {
    const genders = new Set<string>();
    for (const v of voices) {
      const g = v.gender;
      if (g) genders.add(g);
    }
    const opts = [{ value: "", label: "All Genders" }];
    for (const g of Array.from(genders).sort()) {
      opts.push({ value: g, label: g });
    }
    return opts;
  }, [voices]);

  const handleUseVoice = async (voice: Voice) => {
    logger.info("use_voice", { provider: voice.provider, voice_id: voice.voice_id });
    try {
      const profile = await createProfile({
        name: voice.name,
        language: voice.language,
        provider_name: voice.provider,
        voice_id: voice.voice_id,
        description: `Created from ${voice.provider_display} voice: ${voice.voice_id}`,
        tags: ["voice-library"],
      });
      logger.info("use_voice_profile_created", { profile_id: profile.id });
      toast.success(`Profile "${profile.name}" created — ready for synthesis`);
      navigate("/profiles");
    } catch (e: any) {
      logger.error("use_voice_error", { error: e.message });
      toast.error(e.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold">Voice Library</h1>
        <Button
          variant="secondary"
          onClick={() => { logger.info("refresh"); fetchAllVoices(); }}
          disabled={loading}
        >
          <RefreshCw
            className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
          />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <div className="space-y-3">
        {/* Search bar - full width */}
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-secondary)]" />
          <input
            type="text"
            placeholder="Search voices..."
            value={searchInput}
            onChange={(e) => handleSearch(e.target.value)}
            className="h-10 w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] pl-9 pr-3 text-sm text-[var(--color-text)] focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        {/* Filter dropdowns - 2 columns on mobile, 3 on desktop */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Select
            value={filters.provider ?? ""}
            onChange={(e) => {
              logger.info("filter_change", { filter: "provider", value: e.target.value || "all" });
              setFilter("provider", e.target.value || null);
            }}
            options={providerOptions}
          />
          <Select
            value={filters.language ?? ""}
            onChange={(e) => {
              logger.info("filter_change", { filter: "language", value: e.target.value || "all" });
              setFilter("language", e.target.value || null);
            }}
            options={languageOptions}
          />
          <Select
            value={filters.gender ?? ""}
            onChange={(e) => {
              logger.info("filter_change", { filter: "gender", value: e.target.value || "all" });
              setFilter("gender", e.target.value || null);
            }}
            options={genderOptions}
          />
        </div>
      </div>

      {/* Error */}
      {error && (
        <Card className="border-red-300 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          <p className="text-sm">Failed to load voices: {error}</p>
        </Card>
      )}

      {/* Loading skeleton */}
      {loading && voices.length === 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={i} className="animate-pulse space-y-3">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-gray-200 dark:bg-gray-700" />
                <div className="h-4 w-32 rounded bg-gray-200 dark:bg-gray-700" />
              </div>
              <div className="h-3 w-24 rounded bg-gray-200 dark:bg-gray-700" />
              <div className="flex gap-2">
                <div className="h-5 w-12 rounded-full bg-gray-200 dark:bg-gray-700" />
              </div>
              <div className="h-8 w-full rounded bg-gray-200 dark:bg-gray-700" />
            </Card>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && voices.length === 0 && !error && (
        <Card className="py-12 text-center">
          <p className="text-[var(--color-text-secondary)]">
            No voices available. Check that providers are configured in Admin.
          </p>
        </Card>
      )}

      {/* No results after filtering */}
      {!loading && voices.length > 0 && displayed.length === 0 && (
        <Card className="py-12 text-center">
          <p className="text-[var(--color-text-secondary)]">
            No voices match your filters. Try adjusting your search.
          </p>
        </Card>
      )}

      {/* Voice count */}
      {displayed.length > 0 && (
        <p className="text-sm text-[var(--color-text-secondary)]">
          Showing {displayed.length} of {voices.length} voice{voices.length !== 1 ? "s" : ""}
        </p>
      )}

      {/* Voice grid */}
      {displayed.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {displayed.map((voice) => (
            <VoiceCard
              key={`${voice.provider}-${voice.voice_id}`}
              voice={voice}
              onUse={() => handleUseVoice(voice)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

const VoiceCard = React.memo(function VoiceCard({
  voice,
  onUse,
}: {
  voice: Voice;
  onUse: () => void;
}) {
  const gender = voice.gender || inferGender(voice);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const handlePreview = async () => {
    // If already playing, stop
    if (isPlaying && audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlaying(false);
      return;
    }

    // If we already have a URL, play it
    if (previewUrl) {
      playAudio(previewUrl);
      return;
    }

    // Fetch preview
    logger.info("voice_preview_start", { provider: voice.provider, voice_id: voice.voice_id });
    setPreviewLoading(true);
    try {
      const result = await api.previewVoice({
        provider: voice.provider,
        voice_id: voice.voice_id,
      });
      logger.info("voice_preview_complete", { provider: voice.provider, voice_id: voice.voice_id });
      setPreviewUrl(result.audio_url);
      playAudio(result.audio_url);
    } catch (e: any) {
      logger.error("voice_preview_error", { provider: voice.provider, voice_id: voice.voice_id, error: e.message });
      toast.error(`Preview failed: ${e.message}`);
    } finally {
      setPreviewLoading(false);
    }
  };

  const playAudio = (url: string) => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    const audio = new Audio(url);
    audioRef.current = audio;
    audio.onended = () => setIsPlaying(false);
    audio.onerror = () => {
      setIsPlaying(false);
      toast.error("Failed to play audio");
    };
    audio.play();
    setIsPlaying(true);
  };

  return (
    <Card className="flex flex-col gap-3">
      {/* Provider + voice name */}
      <div className="flex items-center gap-3">
        <ProviderLogo name={voice.provider} size={28} />
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-semibold text-[var(--color-text)]">
            {voice.name}
          </h3>
          <p className="text-xs text-[var(--color-text-secondary)]">
            {voice.provider_display}
          </p>
        </div>
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-1.5">
        <Badge status={voice.language} />
        {gender && (
          <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700 dark:bg-gray-700 dark:text-gray-300">
            {gender}
          </span>
        )}
      </div>

      {/* Voice ID */}
      <p className="truncate text-xs text-[var(--color-text-secondary)]">
        ID: {voice.voice_id}
      </p>

      {/* Actions */}
      <div className="mt-auto flex gap-2 border-t border-[var(--color-border)] pt-2">
        <Button
          size="sm"
          variant="secondary"
          onClick={handlePreview}
          disabled={previewLoading}
          className="flex-shrink-0"
        >
          {previewLoading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : isPlaying ? (
            <Pause className="h-3.5 w-3.5" />
          ) : (
            <Play className="h-3.5 w-3.5" />
          )}
          {previewLoading ? "..." : isPlaying ? "Stop" : "Preview"}
        </Button>
        <Button size="sm" className="flex-1" onClick={onUse}>
          <UserPlus className="h-3.5 w-3.5" />
          Use Voice
        </Button>
      </div>
    </Card>
  );
});

/** Try to infer gender from voice name or id patterns (fallback when backend doesn't provide it). */
function inferGender(voice: Voice): string | null {
  const id = voice.voice_id.toLowerCase();
  const name = voice.name.toLowerCase();

  // Kokoro pattern: af_*, am_*, bf_*, bm_*
  if (/^[ab]f[_-]/.test(id)) return "Female";
  if (/^[ab]m[_-]/.test(id)) return "Male";

  // Common keywords
  if (name.includes("female") || name.includes("woman")) return "Female";
  if (name.includes("male") || name.includes("man ")) return "Male";

  return null;
}

/** Map language codes to human-readable labels. */
function languageLabel(code: string): string {
  const map: Record<string, string> = {
    en: "English",
    "en-US": "English (US)",
    "en-GB": "English (UK)",
    "en-AU": "English (AU)",
    "en-IN": "English (IN)",
    "en-IE": "English (IE)",
    "en-CA": "English (CA)",
    "en-NZ": "English (NZ)",
    "en-ZA": "English (ZA)",
    "en-SG": "English (SG)",
    "en-PH": "English (PH)",
    "en-HK": "English (HK)",
    "en-KE": "English (KE)",
    "en-NG": "English (NG)",
    es: "Spanish",
    fr: "French",
    de: "German",
    zh: "Chinese",
    ja: "Japanese",
    ko: "Korean",
    pt: "Portuguese",
    ru: "Russian",
    it: "Italian",
    ar: "Arabic",
    hi: "Hindi",
    nl: "Dutch",
    pl: "Polish",
    tr: "Turkish",
    sv: "Swedish",
    da: "Danish",
    fi: "Finnish",
    no: "Norwegian",
    cs: "Czech",
    uk: "Ukrainian",
  };
  return map[code] ?? code.toUpperCase();
}
