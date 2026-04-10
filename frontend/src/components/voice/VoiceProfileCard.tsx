import { Play, Pause, Volume2 } from "lucide-react";
import { useState } from "react";
import { clsx } from "clsx";
import Card from "../ui/Card";
import WaveformVisualizer from "../audio/WaveformVisualizer";
import VUMeter from "../audio/VUMeter";
import type { Voice } from "../../types";

interface VoiceProfileCardProps {
  profile: Voice;
  onPlay?: () => void;
  onSelect?: () => void;
  isPlaying?: boolean;
  isSelected?: boolean;
  className?: string;
}

// Provider color mapping for distinctive visual identity
const getProviderColor = (provider: string): [string, string] => {
  const colors: Record<string, [string, string]> = {
    elevenlabs: ["hsl(74, 85%, 55%)", "hsl(60, 90%, 45%)"],
    azure_speech: ["hsl(210, 100%, 55%)", "hsl(200, 90%, 45%)"],
    kokoro: ["hsl(315, 85%, 55%)", "hsl(300, 90%, 45%)"],
    piper: ["hsl(150, 85%, 55%)", "hsl(140, 90%, 45%)"],
    coqui_xtts: ["hsl(25, 85%, 55%)", "hsl(15, 90%, 45%)"],
    styletts2: ["hsl(260, 85%, 55%)", "hsl(250, 90%, 45%)"],
    cosyvoice: ["hsl(180, 85%, 55%)", "hsl(170, 90%, 45%)"],
    dia: ["hsl(45, 85%, 55%)", "hsl(35, 90%, 45%)"],
    dia2: ["hsl(285, 85%, 55%)", "hsl(275, 90%, 45%)"],
  };
  return colors[provider] || ["hsl(var(--studio-primary))", "hsl(var(--studio-accent))"];
};

export function VoiceProfileCard({
  profile,
  onPlay,
  onSelect,
  isPlaying = false,
  isSelected = false,
  className
}: VoiceProfileCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [colorFrom, colorTo] = getProviderColor(profile.provider);

  // Generate sample waveform data based on profile characteristics
  const waveformData = Array.from({ length: 20 }, (_, i) => {
    const base = Math.sin(i * 0.4) * 0.5 + 0.5;
    // Add some variation based on profile name hash
    const hash = profile.name.split('').reduce((a, b) => a + b.charCodeAt(0), 0);
    return base + (Math.sin(i * 0.2 + hash) * 0.3);
  });

  return (
    <Card
      variant="studio"
      waveform
      className={clsx(
        "group relative overflow-hidden cursor-pointer transition-all duration-500",
        "hover:-translate-y-1 hover:shadow-studio",
        isSelected && "ring-2 ring-primary-500 shadow-studio",
        className
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onSelect}
    >
      {/* Provider gradient background */}
      <div
        className="absolute inset-0 opacity-5 group-hover:opacity-10 transition-opacity duration-500"
        style={{
          background: `linear-gradient(135deg, ${colorFrom} 0%, ${colorTo} 100%)`
        }}
      />

      {/* Microphone-inspired circular element */}
      <div
        className="absolute -top-6 -right-6 w-28 h-28 rounded-full opacity-20 group-hover:scale-110 transition-transform duration-700"
        style={{
          background: `linear-gradient(135deg, ${colorFrom}40, ${colorTo}40)`
        }}
      />

      <div className="relative z-10">
        {/* Voice Waveform Preview */}
        <div className="mb-4 h-12 flex items-center">
          <WaveformVisualizer
            data={waveformData}
            height={48}
            barCount={20}
            animated={isHovered || isPlaying}
            color="primary"
            className="w-full"
          />
        </div>

        {/* Profile Info */}
        <div className="space-y-2 mb-4">
          <div className="flex items-start justify-between">
            <div className="min-w-0 flex-1">
              <h3 className="font-display font-bold text-lg text-[var(--color-text)] truncate">
                {profile.name}
              </h3>
              <p className="text-sm text-[var(--color-text-secondary)] font-medium">
                {profile.provider_display || profile.provider}
              </p>
            </div>

            {/* VU Meter for voice activity */}
            <div className="ml-3">
              <VUMeter
                level={isPlaying ? 75 : isHovered ? 45 : 0}
                barCount={4}
                height={16}
                animated={isPlaying || isHovered}
              />
            </div>
          </div>

          {/* Voice characteristics */}
          <div className="flex items-center gap-3 text-xs">
            {profile.language && (
              <span className="px-2 py-1 rounded-full bg-primary-500/10 text-primary-600 font-medium">
                {profile.language}
              </span>
            )}
            {profile.gender && (
              <span className="px-2 py-1 rounded-full bg-secondary-400/10 text-secondary-600 font-medium">
                {profile.gender}
              </span>
            )}
          </div>
        </div>

        {/* Control Strip */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {/* Channel LED indicator */}
            <div
              className={clsx(
                "w-2 h-2 rounded-full transition-all duration-300",
                isSelected
                  ? "bg-primary-500 shadow-lg shadow-primary-500/50 animate-led-pulse"
                  : isHovered
                  ? "bg-secondary-400 animate-led-pulse"
                  : "bg-studio-slate/50"
              )}
            />

            <span className="text-xs font-mono text-[var(--color-text-secondary)]">
              CH {profile.voice_id.slice(-2)}
            </span>
          </div>

          {/* Transport Controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onPlay?.();
              }}
              className={clsx(
                "w-10 h-10 rounded-full transition-all duration-300 flex items-center justify-center",
                "border-2 border-transparent",
                isPlaying
                  ? "bg-gradient-to-br from-primary-500 to-primary-600 text-white shadow-lg"
                  : "bg-gradient-to-br from-studio-silver/20 to-studio-slate/30 text-[var(--color-text-secondary)] hover:from-primary-500 hover:to-primary-600 hover:text-white hover:shadow-lg"
              )}
              aria-label={isPlaying ? "Pause preview" : "Play preview"}
            >
              {isPlaying ? (
                <Pause className="w-4 h-4 ml-0" />
              ) : (
                <Play className="w-4 h-4 ml-0.5" />
              )}
            </button>

            {/* Volume/Gain indicator */}
            <div className="flex items-center gap-1">
              <Volume2 className="w-3 h-3 text-[var(--color-text-tertiary)]" />
              <div className="text-xs font-mono text-[var(--color-text-tertiary)]">
                {Math.round(Math.random() * 40 + 50)}%
              </div>
            </div>
          </div>
        </div>

        {/* Hover state audio spectrum */}
        {(isHovered || isPlaying) && (
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-primary-500 via-secondary-400 to-electric-500 opacity-60 animate-spectrum" />
        )}
      </div>
    </Card>
  );
}

export default VoiceProfileCard;