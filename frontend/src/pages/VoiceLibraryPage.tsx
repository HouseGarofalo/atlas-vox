import React, { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { VirtuosoGrid } from "react-virtuoso";
import { getErrorMessage } from "../utils/errors";
import { Loader2, Pause, Play, RefreshCw, Search, UserPlus, Radio, Filter } from "lucide-react";
import { toast } from "sonner";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Select } from "../components/ui/Select";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import ProviderLogo from "../components/providers/ProviderLogo";
import AudioReactiveBackground from "../components/audio/AudioReactiveBackground";
import WaveformVisualizer from "../components/audio/WaveformVisualizer";
import { useAudioPlayer } from "../hooks/useAudioPlayer";
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
  const [selectedVoices, setSelectedVoices] = useState<Set<string>>(new Set());

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
    } catch (e: unknown) {
      logger.error("use_voice_error", { error: getErrorMessage(e) });
      toast.error(getErrorMessage(e));
    }
  };

  return (
    <div className="relative min-h-screen">
      {/* Audio-reactive background */}
      <AudioReactiveBackground intensity="subtle" />

      <div className="relative z-10 space-y-8">
        {/* Studio Header */}
        <div className="flex flex-col gap-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-display font-bold text-gradient mb-2">
                Voice Library
              </h1>
              <p className="text-[var(--color-text-secondary)] font-medium">
                Professional voice catalog with real-time preview and instant profile creation
              </p>
            </div>

            <div className="flex items-center gap-4">
              {/* Voice count display */}
              {displayed.length > 0 && (
                <Card variant="console" className="px-4 py-2">
                  <div className="flex items-center gap-3">
                    <Radio className="h-4 w-4 text-secondary-400" />
                    <span className="font-mono text-sm text-white">
                      {displayed.length} / {voices.length}
                    </span>
                    <div className="w-2 h-2 bg-led-green rounded-full animate-led-pulse" />
                  </div>
                </Card>
              )}

              <Button
                variant="secondary"
                onClick={() => { logger.info("refresh"); fetchAllVoices(); }}
                disabled={loading}
                audioReactive
              >
                <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                Refresh Library
              </Button>
            </div>
          </div>
        </div>

        {/* Studio Control Panel */}
        <CollapsiblePanel
          title="Voice Control Panel"
          icon={<Filter className="h-5 w-5 text-electric-400" />}
          defaultOpen={true}
        >
          <Card variant="console" className="p-6">
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              {/* Search Channel */}
              <div className="lg:col-span-2">
                <label className="block text-xs font-mono text-studio-silver mb-3 uppercase tracking-wider">
                  Search Channel
                </label>
                <div className="relative">
                  <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-studio-silver" />
                  <input
                    type="text"
                    placeholder="Search voices by name, ID, or provider..."
                    value={searchInput}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="w-full h-12 pl-12 pr-4 rounded-xl bg-studio-obsidian/50 border border-studio-slate/30 text-white placeholder:text-studio-silver/50 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 font-mono"
                  />
                  {/* Search activity indicator */}
                  <div className="absolute right-4 top-1/2 -translate-y-1/2">
                    <WaveformVisualizer
                      height={16}
                      barCount={6}
                      animated={searchInput.length > 0}
                      color="primary"
                      className="w-12"
                    />
                  </div>
                </div>
              </div>

              {/* Filter Controls */}
              <div>
                <label className="block text-xs font-mono text-studio-silver mb-3 uppercase tracking-wider">
                  Provider
                </label>
                <Select
                  value={filters.provider ?? ""}
                  onChange={(e) => {
                    logger.info("filter_change", { filter: "provider", value: e.target.value || "all" });
                    setFilter("provider", e.target.value || null);
                  }}
                  options={providerOptions}
                  className="bg-studio-obsidian/50 border-studio-slate/30 text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-studio-silver mb-3 uppercase tracking-wider">
                  Language
                </label>
                <Select
                  value={filters.language ?? ""}
                  onChange={(e) => {
                    logger.info("filter_change", { filter: "language", value: e.target.value || "all" });
                    setFilter("language", e.target.value || null);
                  }}
                  options={languageOptions}
                  className="bg-studio-obsidian/50 border-studio-slate/30 text-white"
                />
              </div>
            </div>

            {/* Additional filter row */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mt-6">
              <div>
                <label className="block text-xs font-mono text-studio-silver mb-3 uppercase tracking-wider">
                  Gender
                </label>
                <Select
                  value={filters.gender ?? ""}
                  onChange={(e) => {
                    logger.info("filter_change", { filter: "gender", value: e.target.value || "all" });
                    setFilter("gender", e.target.value || null);
                  }}
                  options={genderOptions}
                  className="bg-studio-obsidian/50 border-studio-slate/30 text-white"
                />
              </div>

              {/* Library Stats */}
              <div className="lg:col-span-3 flex items-end gap-6">
                <div className="text-center">
                  <div className="text-xs font-mono text-studio-silver mb-1">TOTAL VOICES</div>
                  <div className="text-2xl font-bold text-white">{voices.length}</div>
                </div>
                <div className="text-center">
                  <div className="text-xs font-mono text-studio-silver mb-1">FILTERED</div>
                  <div className="text-2xl font-bold text-secondary-400">{displayed.length}</div>
                </div>
                <div className="text-center">
                  <div className="text-xs font-mono text-studio-silver mb-1">PROVIDERS</div>
                  <div className="text-2xl font-bold text-electric-400">{providerOptions.length - 1}</div>
                </div>
              </div>
            </div>
          </Card>
        </CollapsiblePanel>

        {/* Error State */}
        {error && (
          <Card className="border-red-500/20 bg-red-500/10">
            <div className="flex items-center gap-3 text-red-400">
              <div className="w-3 h-3 bg-led-red rounded-full animate-led-pulse" />
              <p className="font-medium">Failed to load voice library: {error}</p>
            </div>
          </Card>
        )}

        {/* Loading State */}
        {loading && voices.length === 0 && (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <Card key={i} variant="studio" className="animate-pulse space-y-4 p-6">
                <div className="h-12 bg-studio-slate/20 rounded" />
                <div className="space-y-2">
                  <div className="h-4 bg-studio-slate/20 rounded w-3/4" />
                  <div className="h-3 bg-studio-slate/20 rounded w-1/2" />
                </div>
                <div className="flex gap-2">
                  <div className="h-6 w-16 bg-studio-slate/20 rounded-full" />
                  <div className="h-6 w-12 bg-studio-slate/20 rounded-full" />
                </div>
                <div className="h-10 bg-studio-slate/20 rounded" />
              </Card>
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && voices.length === 0 && !error && (
          <Card variant="console" className="py-16 text-center">
            <div className="space-y-4">
              <div className="flex justify-center">
                <Radio className="h-16 w-16 text-studio-slate" />
              </div>
              <div>
                <h3 className="text-xl font-display font-bold text-white mb-2">
                  No Voices Available
                </h3>
                <p className="text-studio-silver">
                  Check that providers are configured and healthy in the Providers panel.
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* No Results After Filtering */}
        {!loading && voices.length > 0 && displayed.length === 0 && (
          <Card variant="console" className="py-16 text-center">
            <div className="space-y-4">
              <div className="flex justify-center">
                <Search className="h-16 w-16 text-studio-slate" />
              </div>
              <div>
                <h3 className="text-xl font-display font-bold text-white mb-2">
                  No Matching Voices
                </h3>
                <p className="text-studio-silver">
                  Try adjusting your search terms or filters to find what you're looking for.
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* Voice Grid */}
        {displayed.length > 0 && (
          <div className="space-y-6">
            <VirtuosoGrid
              totalCount={displayed.length}
              overscan={200}
              useWindowScroll
              listClassName="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
              itemContent={(index) => {
                const voice = displayed[index];
                const voiceKey = `${voice.provider}-${voice.voice_id}`;

                return (
                  <StudioVoiceCard
                    key={voiceKey}
                    voice={voice}
                    onUse={() => handleUseVoice(voice)}
                    isSelected={selectedVoices.has(voiceKey)}
                    onSelect={() => {
                      const newSelected = new Set(selectedVoices);
                      if (newSelected.has(voiceKey)) {
                        newSelected.delete(voiceKey);
                      } else {
                        newSelected.add(voiceKey);
                      }
                      setSelectedVoices(newSelected);
                    }}
                  />
                );
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

const StudioVoiceCard = React.memo(function StudioVoiceCard({
  voice,
  onUse,
  isSelected,
  onSelect,
}: {
  voice: Voice;
  onUse: () => void;
  isSelected?: boolean;
  onSelect?: () => void;
}) {
  const gender = voice.gender || inferGender(voice);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isHovered, setIsHovered] = useState(false);
  const { isPlaying, currentUrl, toggle, stop } = useAudioPlayer();
  const isThisPlaying = isPlaying && currentUrl === previewUrl;

  // Provider colors
  const getProviderColors = (provider: string): [string, string] => {
    const colors: Record<string, [string, string]> = {
      elevenlabs: ["#7C3AED", "#9333EA"],
      azure_speech: ["#0078D4", "#106EBE"],
      kokoro: ["#EC4899", "#BE185D"],
      piper: ["#10B981", "#059669"],
      coqui_xtts: ["#F59E0B", "#D97706"],
      styletts2: ["#8B5CF6", "#7C3AED"],
      cosyvoice: ["#06B6D4", "#0891B2"],
      dia: ["#F59E0B", "#D97706"],
      dia2: ["#A855F7", "#9333EA"],
    };
    return colors[provider] || ["hsl(var(--studio-primary))", "hsl(var(--studio-accent))"];
  };

  const [colorFrom, colorTo] = getProviderColors(voice.provider);

  const handlePreview = async () => {
    if (isThisPlaying) {
      stop();
      return;
    }

    if (previewUrl) {
      toggle(previewUrl);
      return;
    }

    logger.info("voice_preview_start", { provider: voice.provider, voice_id: voice.voice_id });
    setPreviewLoading(true);
    try {
      const result = await api.previewVoice({
        provider: voice.provider,
        voice_id: voice.voice_id,
      });
      logger.info("voice_preview_complete", { provider: voice.provider, voice_id: voice.voice_id });
      setPreviewUrl(result.audio_url);
      toggle(result.audio_url);
    } catch (e: unknown) {
      logger.error("voice_preview_error", { provider: voice.provider, voice_id: voice.voice_id, error: getErrorMessage(e) });
      toast.error(`Preview failed: ${getErrorMessage(e)}`);
    } finally {
      setPreviewLoading(false);
    }
  };

  // Generate sample waveform based on voice characteristics
  const waveformData = Array.from({ length: 20 }, (_, i) => {
    const base = Math.sin(i * 0.4) * 0.5 + 0.5;
    const hash = voice.voice_id.split('').reduce((a, b) => a + b.charCodeAt(0), 0);
    return base + (Math.sin(i * 0.2 + hash) * 0.3);
  });

  return (
    <Card
      variant="studio"
      waveform
      className={`group relative overflow-hidden cursor-pointer transition-all duration-500 hover:-translate-y-1 ${
        isSelected ? "ring-2 ring-primary-500 shadow-studio" : ""
      }`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onSelect}
    >
      {/* Provider gradient background */}
      <div
        className="absolute inset-0 opacity-5 group-hover:opacity-10 transition-opacity duration-500"
        style={{
          background: `linear-gradient(135deg, ${colorFrom}20 0%, ${colorTo}20 100%)`
        }}
      />

      {/* Floating orb element */}
      <div
        className="absolute -top-8 -right-8 w-32 h-32 rounded-full opacity-15 group-hover:scale-110 transition-transform duration-700 blur-xl"
        style={{
          background: `linear-gradient(135deg, ${colorFrom}60, ${colorTo}60)`
        }}
      />

      <div className="relative z-10">
        {/* Voice Waveform Header */}
        <div className="mb-6 h-16 flex items-center">
          <WaveformVisualizer
            data={waveformData}
            height={64}
            barCount={20}
            animated={isHovered || isThisPlaying}
            color="primary"
            className="w-full"
          />
        </div>

        {/* Provider Logo & Info */}
        <div className="flex items-start gap-4 mb-4">
          <div className="relative">
            <div className="p-3 rounded-xl bg-studio-charcoal/20 border border-studio-slate/20">
              <ProviderLogo name={voice.provider} size={32} />
            </div>
            {/* Status LED */}
            <div className="absolute -top-1 -right-1 w-3 h-3 bg-led-green rounded-full animate-led-pulse" />
          </div>

          <div className="flex-1 min-w-0">
            <h3 className="font-display font-bold text-lg text-[var(--color-text)] truncate mb-1">
              {voice.name}
            </h3>
            <p className="text-sm text-[var(--color-text-secondary)] font-medium mb-2">
              {voice.provider_display}
            </p>

            {/* Voice characteristics */}
            <div className="flex items-center gap-2 flex-wrap">
              {voice.language && (
                <span className="px-3 py-1 rounded-full bg-primary-500/15 text-primary-600 dark:text-primary-400 text-xs font-medium border border-primary-500/20">
                  {languageLabel(voice.language)}
                </span>
              )}
              {gender && (
                <span className="px-3 py-1 rounded-full bg-secondary-400/15 text-secondary-600 dark:text-secondary-400 text-xs font-medium border border-secondary-400/20">
                  {gender}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Voice ID */}
        <div className="mb-4 p-2 rounded-lg bg-studio-charcoal/10 border border-studio-slate/10">
          <p className="text-xs font-mono text-[var(--color-text-secondary)] truncate">
            ID: {voice.voice_id}
          </p>
        </div>

        {/* Transport Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handlePreview();
            }}
            disabled={previewLoading}
            className={`flex items-center justify-center w-12 h-12 rounded-full transition-all duration-300 border-2 ${
              isThisPlaying
                ? "bg-gradient-to-br from-primary-500 to-primary-600 text-white border-primary-500 shadow-lg shadow-primary-500/30"
                : previewLoading
                ? "bg-studio-slate/20 text-studio-silver border-studio-slate/30"
                : "bg-gradient-to-br from-studio-silver/10 to-studio-slate/20 text-[var(--color-text-secondary)] border-studio-slate/20 hover:from-primary-500 hover:to-primary-600 hover:text-white hover:border-primary-500 hover:shadow-lg hover:shadow-primary-500/30"
            }`}
          >
            {previewLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : isThisPlaying ? (
              <Pause className="w-5 h-5" />
            ) : (
              <Play className="w-5 h-5 ml-0.5" />
            )}
          </button>

          <Button
            variant="electric"
            size="md"
            onClick={(e) => {
              e.stopPropagation();
              onUse();
            }}
            className="flex-1"
          >
            <UserPlus className="h-4 w-4" />
            Create Profile
          </Button>
        </div>

        {/* Active state spectrum line */}
        {(isHovered || isThisPlaying || isSelected) && (
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-primary-500 via-secondary-400 to-electric-500 opacity-80 animate-spectrum" />
        )}
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
