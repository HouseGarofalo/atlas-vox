import { Sparkles, Smile, Play, Mic, Layers, Loader2 } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { CollapsiblePanel } from "../../components/ui/CollapsiblePanel";
import RotaryKnob from "../../components/audio/RotaryKnob";
import { AZURE_EMOTIONS } from "./types";
import type { AudioControlPanelProps } from "./types";

export default function AudioControlPanel({
  synthesisMode,
  batchMode,
  batchText,
  speed,
  onSetSpeed,
  pitch,
  onSetPitch,
  volume,
  onSetVolume,
  isElevenLabs,
  stability,
  onSetStability,
  similarityBoost,
  onSetSimilarityBoost,
  speakerBoost,
  onSetSpeakerBoost,
  isAzure,
  emotion,
  onSetEmotion,
  loading,
  batchLoading,
  stsLoading,
  stsFile,
  profileId,
  text,
  onSynthesize,
  onBatchSynthesize,
  onSpeechToSpeech,
}: AudioControlPanelProps) {
  const batchLineCount = batchText
    .split("\n")
    .filter((l) => l.trim().length > 0).length;

  return (
    <>
      {/* Rotary Control Section */}
      {synthesisMode === "tts" && (
        <Card variant="console" className="p-6">
          <h3 className="text-lg font-display font-bold text-white mb-6 flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-secondary-400" />
            AUDIO PROCESSING
          </h3>

          <div className="grid grid-cols-2 gap-6">
            <RotaryKnob
              value={speed}
              onChange={onSetSpeed}
              min={0.5}
              max={2}
              step={0.05}
              label="Speed"
              colorFrom="hsl(var(--electric-500))"
              colorTo="hsl(var(--electric-600))"
              size="md"
            />
            <RotaryKnob
              value={pitch}
              onChange={onSetPitch}
              min={-50}
              max={50}
              step={1}
              label="Pitch"
              colorFrom="hsl(var(--primary-500))"
              colorTo="hsl(var(--primary-600))"
              size="md"
            />
            <RotaryKnob
              value={volume}
              onChange={onSetVolume}
              min={0}
              max={2}
              step={0.05}
              label="Volume"
              colorFrom="hsl(var(--secondary-400))"
              colorTo="hsl(var(--secondary-500))"
              size="md"
            />
            {batchMode && (
              <div className="flex flex-col items-center justify-center">
                <div className="text-center">
                  <div className="text-xs font-mono text-studio-silver mb-2">
                    BATCH COUNT
                  </div>
                  <div className="text-2xl font-bold text-white">
                    {batchLineCount}
                  </div>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* ElevenLabs Voice Settings */}
      {isElevenLabs && synthesisMode === "tts" && (
        <CollapsiblePanel
          title="Voice Settings"
          icon={<Sparkles className="h-5 w-5 text-violet-400" />}
          defaultOpen={false}
        >
          <Card variant="console" className="p-4 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <RotaryKnob
                value={stability}
                onChange={onSetStability}
                min={0}
                max={1}
                step={0.05}
                label="Stability"
                colorFrom="hsl(260, 85%, 55%)"
                colorTo="hsl(280, 85%, 55%)"
                size="sm"
              />
              <RotaryKnob
                value={similarityBoost}
                onChange={onSetSimilarityBoost}
                min={0}
                max={1}
                step={0.05}
                label="Similarity"
                colorFrom="hsl(310, 85%, 55%)"
                colorTo="hsl(330, 85%, 55%)"
                size="sm"
              />
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-studio-silver">
                Speaker Boost
              </span>
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={speakerBoost}
                  onChange={(e) => onSetSpeakerBoost(e.target.checked)}
                  className="sr-only"
                />
                <div
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    speakerBoost ? "bg-primary-500" : "bg-studio-slate"
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      speakerBoost ? "translate-x-6" : "translate-x-1"
                    }`}
                  />
                </div>
              </label>
            </div>
          </Card>
        </CollapsiblePanel>
      )}

      {/* Azure Emotion Controls */}
      {isAzure && synthesisMode === "tts" && (
        <CollapsiblePanel
          title="Expression Style"
          icon={<Smile className="h-5 w-5 text-amber-400" />}
          defaultOpen={false}
        >
          <div className="grid grid-cols-2 gap-2">
            {AZURE_EMOTIONS.slice(0, 12).map((em) => (
              <button
                key={em.value}
                onClick={() => onSetEmotion(em.value)}
                className={`rounded-lg px-3 py-2 text-xs font-medium transition-all duration-200 ${
                  emotion === em.value
                    ? "bg-gradient-studio text-white"
                    : "bg-studio-charcoal/30 text-studio-silver hover:bg-studio-charcoal/50 hover:text-white"
                }`}
              >
                {em.label}
              </button>
            ))}
          </div>
        </CollapsiblePanel>
      )}

      {/* Main Action Button */}
      <Card variant="console" className="p-6">
        {batchMode ? (
          <Button
            className="w-full text-lg py-4"
            variant="primary"
            audioReactive
            onClick={onBatchSynthesize}
            disabled={batchLoading || !profileId || batchLineCount === 0}
          >
            {batchLoading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                PROCESSING BATCH...
              </>
            ) : (
              <>
                <Layers className="h-5 w-5" />
                SYNTHESIZE BATCH
              </>
            )}
          </Button>
        ) : synthesisMode === "tts" ? (
          <Button
            className="w-full text-lg py-4"
            variant="primary"
            audioReactive
            onClick={onSynthesize}
            disabled={loading || !text.trim() || !profileId}
          >
            {loading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                SYNTHESIZING...
              </>
            ) : (
              <>
                <Play className="h-5 w-5" />
                SYNTHESIZE AUDIO
              </>
            )}
          </Button>
        ) : (
          <Button
            className="w-full text-lg py-4"
            variant="electric"
            audioReactive
            onClick={onSpeechToSpeech}
            disabled={stsLoading || !stsFile || !profileId}
          >
            {stsLoading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                CONVERTING...
              </>
            ) : (
              <>
                <Mic className="h-5 w-5" />
                CONVERT VOICE
              </>
            )}
          </Button>
        )}
      </Card>
    </>
  );
}
