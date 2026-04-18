/**
 * VoiceGrid — virtualised grid that renders filtered voices as StudioVoiceCard tiles.
 *
 * Extracted from VoiceLibraryPage.tsx as part of P2-20 (decompose large pages).
 */

import { VirtuosoGrid } from "react-virtuoso";
import { StudioVoiceCard } from "./StudioVoiceCard";
import type { Voice } from "../../types";

export interface VoiceGridProps {
  voices: Voice[];
  selectedVoices: Set<string>;
  onToggleSelect: (voiceKey: string) => void;
  onUseVoice: (voice: Voice) => void;
}

export function VoiceGrid({
  voices,
  selectedVoices,
  onToggleSelect,
  onUseVoice,
}: VoiceGridProps) {
  return (
    <div className="space-y-6">
      <VirtuosoGrid
        totalCount={voices.length}
        overscan={200}
        useWindowScroll
        listClassName="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
        itemContent={(index) => {
          const voice = voices[index];
          const voiceKey = `${voice.provider}-${voice.voice_id}`;
          return (
            <StudioVoiceCard
              key={voiceKey}
              voice={voice}
              onUse={() => onUseVoice(voice)}
              isSelected={selectedVoices.has(voiceKey)}
              onSelect={() => onToggleSelect(voiceKey)}
            />
          );
        }}
      />
    </div>
  );
}
