import { Mic, Upload, Play } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { CollapsiblePanel } from "../../components/ui/CollapsiblePanel";
import { AudioPlayer } from "../../components/audio/AudioPlayer";
import WaveformVisualizer from "../../components/audio/WaveformVisualizer";
import type { SpeechToSpeechPanelProps } from "./types";

export default function SpeechToSpeechPanel({
  stsFile,
  onSetStsFile,
  stsResult,
  stsInputRef,
  stsBlobUrl,
}: SpeechToSpeechPanelProps) {
  return (
    <>
      <CollapsiblePanel
        title="Source Audio Input"
        icon={<Mic className="h-5 w-5 text-primary-500" />}
      >
        <div className="space-y-6">
          <input
            ref={stsInputRef}
            type="file"
            accept="audio/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onSetStsFile(file);
            }}
          />
          <div
            onClick={() => stsInputRef.current?.click()}
            className="flex flex-col items-center gap-4 rounded-xl border-2 border-dashed border-[var(--color-border)] p-12 cursor-pointer transition-all duration-300 hover:border-primary-400 hover:bg-primary-50/50 dark:hover:bg-primary-950/20"
          >
            <div className="p-4 rounded-full bg-primary-500/10">
              <Upload className="h-8 w-8 text-primary-500" />
            </div>
            <div className="text-center">
              <p className="text-lg font-medium text-[var(--color-text)]">
                {stsFile ? stsFile.name : "Upload source audio file"}
              </p>
              <p className="text-sm text-[var(--color-text-secondary)] mt-2">
                {stsFile
                  ? `${(stsFile.size / 1024 / 1024).toFixed(1)} MB`
                  : "WAV, MP3, OGG supported \u2022 Max 50MB"}
              </p>
            </div>
          </div>
          {stsBlobUrl && (
            <Card>
              <audio src={stsBlobUrl} controls className="w-full" />
              <div className="mt-3">
                <WaveformVisualizer
                  height={24}
                  barCount={20}
                  animated={false}
                  color="electric"
                />
              </div>
            </Card>
          )}
        </div>
      </CollapsiblePanel>

      {stsResult && (
        <CollapsiblePanel
          title="Converted Result"
          icon={<Play className="h-5 w-5 text-green-500" />}
        >
          <Card className="space-y-4">
            <AudioPlayer src={stsResult.audio_url} />
            {stsResult.duration_seconds != null && (
              <div className="text-center">
                <div className="text-sm font-medium text-[var(--color-text)]">
                  Duration
                </div>
                <div className="text-xs text-[var(--color-text-secondary)]">
                  {stsResult.duration_seconds.toFixed(1)}s
                </div>
              </div>
            )}
            <WaveformVisualizer
              height={32}
              barCount={20}
              animated={false}
              color="secondary"
            />
          </Card>
        </CollapsiblePanel>
      )}
    </>
  );
}
