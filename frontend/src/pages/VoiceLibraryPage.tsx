/**
 * VoiceLibraryPage — catalog of all provider voices with filtering & preview.
 *
 * P2-20: decomposed from a 628-line mega-file. Sub-components live in
 * ./voice-library/*. This file keeps only page-level state, data derivations
 * and the overall layout.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getErrorMessage } from "../utils/errors";
import { Filter, Radio, RefreshCw, Search } from "lucide-react";
import { toast } from "sonner";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import AudioReactiveBackground from "../components/audio/AudioReactiveBackground";
import { useVoiceLibraryStore } from "../stores/voiceLibraryStore";
import { useProfileStore } from "../stores/profileStore";
import { createLogger } from "../utils/logger";
import type { Voice } from "../types";
import { FilterPanel } from "./voice-library/FilterPanel";
import { VoiceGrid } from "./voice-library/VoiceGrid";
import { languageLabel } from "./voice-library/languageLabel";

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

  const toggleSelectVoice = (voiceKey: string) => {
    setSelectedVoices((prev) => {
      const next = new Set(prev);
      if (next.has(voiceKey)) next.delete(voiceKey);
      else next.add(voiceKey);
      return next;
    });
  };

  const setProvider = (value: string | null) => {
    logger.info("filter_change", { filter: "provider", value: value ?? "all" });
    setFilter("provider", value);
  };
  const setLanguage = (value: string | null) => {
    logger.info("filter_change", { filter: "language", value: value ?? "all" });
    setFilter("language", value);
  };
  const setGender = (value: string | null) => {
    logger.info("filter_change", { filter: "gender", value: value ?? "all" });
    setFilter("gender", value);
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
                onClick={() => {
                  logger.info("refresh");
                  fetchAllVoices();
                }}
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
          <FilterPanel
            searchInput={searchInput}
            onSearchChange={handleSearch}
            providerValue={filters.provider ?? ""}
            onProviderChange={setProvider}
            languageValue={filters.language ?? ""}
            onLanguageChange={setLanguage}
            genderValue={filters.gender ?? ""}
            onGenderChange={setGender}
            providerOptions={providerOptions}
            languageOptions={languageOptions}
            genderOptions={genderOptions}
            totalVoices={voices.length}
            filteredCount={displayed.length}
          />
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
          <VoiceGrid
            voices={displayed}
            selectedVoices={selectedVoices}
            onToggleSelect={toggleSelectVoice}
            onUseVoice={handleUseVoice}
          />
        )}
      </div>
    </div>
  );
}
