import { Power, Play, Type, Mic, Layers } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import VUMeter from "../../components/audio/VUMeter";
import type { ConsoleHeaderProps } from "./types";

export default function ConsoleHeader({
  consoleOn,
  onToggleConsole,
  batchMode,
  onSetBatchMode,
  synthesisMode,
  onSetSynthesisMode,
  canPreview,
  onPreview,
  loading,
  vuLevels,
}: ConsoleHeaderProps) {
  return (
    <Card variant="console" className="p-6">
      <div className="flex items-center justify-between mb-6">
        {/* Console power and status */}
        <div className="flex items-center gap-6">
          <button
            onClick={onToggleConsole}
            className={`flex items-center gap-3 px-4 py-2 rounded-xl transition-all duration-300 ${
              consoleOn
                ? "bg-led-green/20 text-led-green border border-led-green/30"
                : "bg-studio-slate/20 text-studio-silver border border-studio-slate/30"
            }`}
          >
            <Power className="h-5 w-5" />
            <span className="font-mono text-sm">
              {consoleOn ? "ONLINE" : "STANDBY"}
            </span>
            {consoleOn && (
              <div className="w-2 h-2 bg-led-green rounded-full animate-led-pulse" />
            )}
          </button>

          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-display font-bold text-white">
              SYNTHESIS CONSOLE
            </h1>
            <div className="text-xs font-mono text-studio-silver bg-studio-obsidian/50 px-3 py-1 rounded border border-studio-slate/30">
              {new Date().toLocaleTimeString()}
            </div>
          </div>
        </div>

        {/* Master VU meters */}
        <div className="flex items-center gap-6">
          <div className="text-center">
            <div className="text-xs font-mono text-studio-silver mb-1">INPUT</div>
            <VUMeter level={vuLevels.input} barCount={6} height={20} />
          </div>
          <div className="text-center">
            <div className="text-xs font-mono text-studio-silver mb-1">OUTPUT</div>
            <VUMeter level={vuLevels.output} barCount={6} height={20} />
          </div>
          <div className="text-center">
            <div className="text-xs font-mono text-studio-silver mb-1">MASTER</div>
            <VUMeter level={vuLevels.master} barCount={8} height={24} />
          </div>
        </div>
      </div>

      {/* Mode Selection */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          {/* Single / Batch toggle */}
          <div className="inline-flex rounded-xl border border-studio-slate/30 p-1 bg-studio-obsidian/30">
            <button
              onClick={() => onSetBatchMode(false)}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200 ${
                !batchMode
                  ? "bg-gradient-studio text-white shadow-lg"
                  : "text-studio-silver hover:text-white hover:bg-white/5"
              }`}
            >
              Single
            </button>
            <button
              onClick={() => onSetBatchMode(true)}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200 ${
                batchMode
                  ? "bg-gradient-studio text-white shadow-lg"
                  : "text-studio-silver hover:text-white hover:bg-white/5"
              }`}
            >
              <Layers className="h-4 w-4" /> Batch
            </button>
          </div>

          {/* Mode toggle: TTS / STS (only shown in single mode) */}
          {!batchMode && (
            <div className="inline-flex rounded-xl border border-studio-slate/30 p-1 bg-studio-obsidian/30">
              <button
                onClick={() => onSetSynthesisMode("tts")}
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200 ${
                  synthesisMode === "tts"
                    ? "bg-gradient-studio text-white shadow-lg"
                    : "text-studio-silver hover:text-white hover:bg-white/5"
                }`}
              >
                <Type className="h-4 w-4" /> Text-to-Speech
              </button>
              <button
                onClick={() => onSetSynthesisMode("sts")}
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200 ${
                  synthesisMode === "sts"
                    ? "bg-gradient-studio text-white shadow-lg"
                    : "text-studio-silver hover:text-white hover:bg-white/5"
                }`}
              >
                <Mic className="h-4 w-4" /> Speech-to-Speech
              </button>
            </div>
          )}
        </div>

        {/* Quick actions */}
        <div className="flex items-center gap-3">
          {canPreview && (
            <Button
              size="sm"
              variant="electric"
              onClick={onPreview}
              disabled={loading}
              className="font-mono"
            >
              <Play className="h-3.5 w-3.5" /> PREVIEW
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}
