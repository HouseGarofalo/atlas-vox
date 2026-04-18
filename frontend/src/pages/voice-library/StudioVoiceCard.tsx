/**
 * StudioVoiceCard — one voice tile in the VoiceLibrary grid.
 *
 * Extracted from VoiceLibraryPage.tsx as part of P2-20 (decompose large pages).
 * Behaviour (preview streaming, hover states, selection) is preserved exactly.
 */

import React, { useState } from "react";
import { Loader2, Pause, Play, UserPlus } from "lucide-react";
import { toast } from "sonner";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import ProviderLogo from "../../components/providers/ProviderLogo";
import WaveformVisualizer from "../../components/audio/WaveformVisualizer";
import { useAudioPlayer } from "../../hooks/useAudioPlayer";
import { api } from "../../services/api";
import { createLogger } from "../../utils/logger";
import { getErrorMessage } from "../../utils/errors";
import type { Voice } from "../../types";
import { inferGender, languageLabel } from "./languageLabel";

const logger = createLogger("StudioVoiceCard");

// Provider-specific gradient colors for the card accents
const PROVIDER_COLORS: Record<string, [string, string]> = {
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

export interface StudioVoiceCardProps {
  voice: Voice;
  onUse: () => void;
  isSelected?: boolean;
  onSelect?: () => void;
}

export const StudioVoiceCard = React.memo(function StudioVoiceCard({
  voice,
  onUse,
  isSelected,
  onSelect,
}: StudioVoiceCardProps) {
  const gender = voice.gender || inferGender(voice);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isHovered, setIsHovered] = useState(false);
  const { isPlaying, currentUrl, toggle, stop } = useAudioPlayer();
  const isThisPlaying = isPlaying && currentUrl === previewUrl;

  const [colorFrom, colorTo] =
    PROVIDER_COLORS[voice.provider] ??
    ["hsl(var(--studio-primary))", "hsl(var(--studio-accent))"];

  const handlePreview = async () => {
    if (isThisPlaying) {
      stop();
      return;
    }

    if (previewUrl) {
      toggle(previewUrl);
      return;
    }

    logger.info("voice_preview_start", {
      provider: voice.provider,
      voice_id: voice.voice_id,
    });
    setPreviewLoading(true);
    try {
      const result = await api.previewVoice({
        provider: voice.provider,
        voice_id: voice.voice_id,
      });
      logger.info("voice_preview_complete", {
        provider: voice.provider,
        voice_id: voice.voice_id,
      });
      setPreviewUrl(result.audio_url);
      toggle(result.audio_url);
    } catch (e: unknown) {
      logger.error("voice_preview_error", {
        provider: voice.provider,
        voice_id: voice.voice_id,
        error: getErrorMessage(e),
      });
      toast.error(`Preview failed: ${getErrorMessage(e)}`);
    } finally {
      setPreviewLoading(false);
    }
  };

  // Generate sample waveform based on voice characteristics
  const waveformData = Array.from({ length: 20 }, (_, i) => {
    const base = Math.sin(i * 0.4) * 0.5 + 0.5;
    const hash = voice.voice_id.split("").reduce((a, b) => a + b.charCodeAt(0), 0);
    return base + Math.sin(i * 0.2 + hash) * 0.3;
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
          background: `linear-gradient(135deg, ${colorFrom}20 0%, ${colorTo}20 100%)`,
        }}
      />

      {/* Floating orb element */}
      <div
        className="absolute -top-8 -right-8 w-32 h-32 rounded-full opacity-15 group-hover:scale-110 transition-transform duration-700 blur-xl"
        style={{
          background: `linear-gradient(135deg, ${colorFrom}60, ${colorTo}60)`,
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
