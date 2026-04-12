import { Type, Play } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { CollapsiblePanel } from "../../components/ui/CollapsiblePanel";
import { SSMLEditor } from "../../components/audio/SSMLEditor";
import { AudioPlayer } from "../../components/audio/AudioPlayer";
import WaveformVisualizer from "../../components/audio/WaveformVisualizer";
import type { TextToSpeechPanelProps } from "./types";

export default function TextToSpeechPanel({
  text,
  onSetText,
  lastResult,
}: TextToSpeechPanelProps) {
  return (
    <>
      <CollapsiblePanel
        title="Text Input"
        icon={<Type className="h-5 w-5 text-primary-500" />}
      >
        <SSMLEditor value={text} onChange={onSetText} minHeight={200} />
        <div className="flex items-center justify-between mt-3">
          <p className="text-sm text-[var(--color-text-secondary)]">
            {text.length} / 10,000 characters
          </p>
          <WaveformVisualizer
            height={20}
            barCount={15}
            animated={text.length > 0}
            color="primary"
            className="w-32"
          />
        </div>
      </CollapsiblePanel>

      {lastResult && (
        <CollapsiblePanel
          title="Synthesis Result"
          icon={<Play className="h-5 w-5 text-green-500" />}
        >
          <Card className="space-y-4">
            <AudioPlayer src={lastResult.audio_url} />
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-sm font-medium text-[var(--color-text)]">
                  Provider
                </div>
                <div className="text-xs text-[var(--color-text-secondary)]">
                  {lastResult.provider_name}
                </div>
              </div>
              <div>
                <div className="text-sm font-medium text-[var(--color-text)]">
                  Latency
                </div>
                <div className="text-xs text-[var(--color-text-secondary)]">
                  {lastResult.latency_ms}ms
                </div>
              </div>
              {lastResult.duration_seconds && (
                <div>
                  <div className="text-sm font-medium text-[var(--color-text)]">
                    Duration
                  </div>
                  <div className="text-xs text-[var(--color-text-secondary)]">
                    {lastResult.duration_seconds.toFixed(1)}s
                  </div>
                </div>
              )}
            </div>
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
