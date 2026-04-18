import { Clock } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { CollapsiblePanel } from "../../components/ui/CollapsiblePanel";
import WaveformVisualizer from "../../components/audio/WaveformVisualizer";
import type { ActivityLogProps } from "./types";
import type { SynthesisHistoryItem } from "../../types";

export default function ActivityLog({ history }: ActivityLogProps) {
  if (history.length === 0) return null;

  return (
    <CollapsiblePanel
      title="Activity Log"
      icon={<Clock className="h-5 w-5 text-electric-400" />}
      defaultOpen={false}
    >
      <Card variant="console" className="max-h-64 overflow-y-auto">
        <div className="space-y-2">
          {history.slice(0, 8).map((h: SynthesisHistoryItem, index) => (
            <div
              key={h.id}
              className="flex items-center gap-3 p-2 rounded-lg bg-studio-charcoal/30 hover:bg-studio-charcoal/50 transition-all duration-200"
            >
              <div className="flex flex-col items-center">
                <div className="w-2 h-2 bg-led-green rounded-full" />
                <span className="text-xs font-mono text-studio-silver mt-1">
                  {(index + 1).toString().padStart(2, "0")}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-white truncate font-medium">
                  {h.text}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-studio-silver">
                    {h.provider_name}
                  </span>
                  <span className="text-xs text-secondary-400">
                    {h.latency_ms}ms
                  </span>
                </div>
              </div>
              <WaveformVisualizer
                source={h.audio_url}
                height={12}
                barCount={6}
                animated={false}
                color="electric"
                className="w-12"
              />
            </div>
          ))}
        </div>
      </Card>
    </CollapsiblePanel>
  );
}
