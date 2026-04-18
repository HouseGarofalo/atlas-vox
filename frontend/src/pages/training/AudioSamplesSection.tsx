/**
 * AudioSamplesSection — uploader + recorder + SampleList + preprocess button.
 *
 * Extracted from TrainingStudioPage.tsx as part of P2-20 (decompose large pages).
 */

import { Button } from "../../components/ui/Button";
import { AudioRecorder, FileUploader } from "../../components/audio/AudioRecorder";
import { SampleList } from "./SampleList";
import type { AudioSample, QualityResult } from "../../types";

export interface AudioSamplesSectionProps {
  samples: AudioSample[];
  sampleQualities: Record<string, QualityResult>;
  playingSampleId: string | null;
  enhancing: string | null;
  enhancingAll: boolean;
  checkingQuality: string | null;
  uploading: boolean;
  preprocessing: boolean;
  onUpload: (files: File[]) => void;
  onRecord: (blob: Blob, filename: string) => void;
  onPlaySample: (sampleId: string, filename: string) => void;
  onPlaybackEnded: () => void;
  onEnhance: (sampleId: string) => void;
  onCheckQuality: (sampleId: string) => void;
  onEnhanceAll: () => void;
  onPreprocess: () => void;
}

export function AudioSamplesSection({
  samples,
  sampleQualities,
  playingSampleId,
  enhancing,
  enhancingAll,
  checkingQuality,
  uploading,
  preprocessing,
  onUpload,
  onRecord,
  onPlaySample,
  onPlaybackEnded,
  onEnhance,
  onCheckQuality,
  onEnhanceAll,
  onPreprocess,
}: AudioSamplesSectionProps) {
  return (
    <div className="space-y-4">
      <FileUploader onFiles={onUpload} />
      <AudioRecorder onRecorded={onRecord} />
      {uploading && (
        <p className="text-sm text-[var(--color-text-secondary)]">
          Uploading and analyzing files...
        </p>
      )}
      {samples.length > 0 && (
        <SampleList
          samples={samples}
          sampleQualities={sampleQualities}
          playingSampleId={playingSampleId}
          enhancing={enhancing}
          enhancingAll={enhancingAll}
          checkingQuality={checkingQuality}
          onPlaySample={onPlaySample}
          onEnhance={onEnhance}
          onCheckQuality={onCheckQuality}
          onEnhanceAll={onEnhanceAll}
          onPlaybackEnded={onPlaybackEnded}
        />
      )}
      {samples.some((s) => !s.preprocessed) && (
        <Button variant="secondary" onClick={onPreprocess} loading={preprocessing}>
          Preprocess Samples
        </Button>
      )}
    </div>
  );
}
