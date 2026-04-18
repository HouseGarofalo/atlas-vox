/**
 * SampleList — the list of AudioSample rows plus the "Enhance All" header.
 *
 * Extracted from TrainingStudioPage.tsx as part of P2-20 (decompose large pages).
 */

import { Wand2 } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { SampleRow } from "./SampleRow";
import type { AudioSample, QualityResult } from "../../types";

export interface SampleListProps {
  samples: AudioSample[];
  sampleQualities: Record<string, QualityResult>;
  playingSampleId: string | null;
  enhancing: string | null;
  enhancingAll: boolean;
  checkingQuality: string | null;
  onPlaySample: (sampleId: string, filename: string) => void;
  onEnhance: (sampleId: string) => void;
  onCheckQuality: (sampleId: string) => void;
  onEnhanceAll: () => void;
  onPlaybackEnded: () => void;
}

export function SampleList({
  samples,
  sampleQualities,
  playingSampleId,
  enhancing,
  enhancingAll,
  checkingQuality,
  onPlaySample,
  onEnhance,
  onCheckQuality,
  onEnhanceAll,
  onPlaybackEnded,
}: SampleListProps) {
  const totalDuration = samples
    .reduce((sum, s) => sum + (s.duration_seconds || 0), 0)
    .toFixed(1);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] px-2">
        <span>
          Total: {totalDuration}s across {samples.length} file(s)
        </span>
        <Button
          variant="secondary"
          size="sm"
          onClick={onEnhanceAll}
          loading={enhancingAll}
        >
          <Wand2 className="h-3.5 w-3.5" /> Enhance All
        </Button>
      </div>
      {samples.map((s) => (
        <SampleRow
          key={s.id}
          sample={s}
          isPlaying={playingSampleId === s.id}
          quality={sampleQualities[s.id]}
          isEnhancing={enhancing === s.id}
          isCheckingQuality={checkingQuality === s.id}
          onPlay={() => onPlaySample(s.id, s.filename)}
          onEnhance={() => onEnhance(s.id)}
          onCheckQuality={() => onCheckQuality(s.id)}
          onPlaybackEnded={onPlaybackEnded}
        />
      ))}
    </div>
  );
}
