import { Settings } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { Select } from "../../components/ui/Select";
import { OUTPUT_FORMATS } from "./types";
import type { VoiceChannelCardProps } from "./types";

export default function VoiceChannelCard({
  profileId,
  onProfileSelect,
  profileOptions,
  presetId,
  onPresetSelect,
  presets,
  outputFormat,
  onSetOutputFormat,
  synthesisMode,
}: VoiceChannelCardProps) {
  return (
    <Card variant="console" className="p-6">
      <h3 className="text-lg font-display font-bold text-white mb-6 flex items-center gap-2">
        <Settings className="h-5 w-5 text-primary-400" />
        VOICE CHANNEL
      </h3>

      <div className="space-y-6">
        <Select
          label="Voice Profile"
          value={profileId}
          onChange={(e) => onProfileSelect(e.target.value)}
          options={[{ value: "", label: "Select profile..." }, ...profileOptions]}
          className="text-white"
        />

        {synthesisMode === "tts" && (
          <Select
            label="Persona Preset"
            value={presetId}
            onChange={(e) => onPresetSelect(e.target.value)}
            options={[
              { value: "", label: "None" },
              ...presets.map((p) => ({ value: p.id, label: p.name })),
            ]}
            className="text-white"
          />
        )}

        <Select
          label="Output Format"
          value={outputFormat}
          onChange={(e) => onSetOutputFormat(e.target.value)}
          options={OUTPUT_FORMATS.map((f) => ({
            value: f.value,
            label: f.label,
          }))}
          className="text-white"
        />
      </div>
    </Card>
  );
}
