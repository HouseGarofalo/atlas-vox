/**
 * SampleRow — a single audio-sample row with play/enhance/quality-check buttons.
 *
 * Extracted from TrainingStudioPage.tsx as part of P2-20 (decompose large pages).
 */

import React from "react";
import { Pause, Play, Search, Wand2 } from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { api } from "../../services/api";
import type { AudioSample, QualityResult } from "../../types";

export interface SampleRowProps {
  sample: AudioSample;
  isPlaying: boolean;
  quality: QualityResult | undefined;
  isEnhancing: boolean;
  isCheckingQuality: boolean;
  onPlay: () => void;
  onEnhance: () => void;
  onCheckQuality: () => void;
  onPlaybackEnded: () => void;
}

export const SampleRow = React.memo(function SampleRow({
  sample,
  isPlaying,
  quality,
  isEnhancing,
  isCheckingQuality,
  onPlay,
  onEnhance,
  onCheckQuality,
  onPlaybackEnded,
}: SampleRowProps) {
  return (
    <div className="rounded border border-[var(--color-border)]">
      <div className="flex items-center gap-3 p-2">
        <button
          onClick={onPlay}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary-500 text-white hover:bg-primary-600 transition-colors"
          aria-label={isPlaying ? "Stop" : "Play"}
        >
          {isPlaying ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3 ml-0.5" />}
        </button>
        <span className="flex-1 text-sm truncate">{sample.original_filename}</span>
        {quality && (
          <span
            className={`inline-block h-2.5 w-2.5 rounded-full ${
              quality.score >= 80
                ? "bg-green-500"
                : quality.score >= 50
                  ? "bg-yellow-500"
                  : "bg-red-500"
            }`}
            title={`Quality: ${quality.score.toFixed(0)}%`}
          />
        )}
        <span className="text-xs text-[var(--color-text-secondary)] uppercase hidden sm:inline">
          {sample.format}
        </span>
        <span className="text-xs text-[var(--color-text-secondary)]">
          {sample.duration_seconds ? `${sample.duration_seconds.toFixed(1)}s` : "Pending"}
        </span>
        <Badge status={sample.preprocessed ? "ready" : "pending"} />
        <Button
          variant="ghost"
          size="sm"
          onClick={onEnhance}
          disabled={isEnhancing}
          aria-label="Enhance sample"
          title="Enhance (audio isolation)"
        >
          {isEnhancing ? <span className="text-xs">...</span> : <Wand2 className="h-3 w-3" />}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onCheckQuality}
          disabled={isCheckingQuality}
          aria-label="Check quality"
        >
          {isCheckingQuality ? (
            <span className="text-xs">...</span>
          ) : (
            <Search className="h-3 w-3" />
          )}
        </Button>
      </div>
      {isPlaying && (
        <div className="px-2 pb-2">
          <audio
            src={api.audioUrl(sample.filename)}
            autoPlay
            controls
            onEnded={onPlaybackEnded}
            className="w-full h-8"
          />
        </div>
      )}
      {quality && quality.issues.length > 0 && (
        <div className="px-2 pb-2 space-y-1">
          {quality.issues.map((issue, i) => (
            <p
              key={i}
              className={`text-xs ${
                issue.severity === "error"
                  ? "text-red-500"
                  : "text-yellow-600 dark:text-yellow-400"
              }`}
            >
              {issue.message}
            </p>
          ))}
        </div>
      )}
    </div>
  );
});
