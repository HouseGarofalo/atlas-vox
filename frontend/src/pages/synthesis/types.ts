import type { RefObject } from "react";
import type { PersonaPreset, SynthesisHistoryItem } from "../../types";

/* ------------------------------------------------------------------ */
/*  Shared constants                                                   */
/* ------------------------------------------------------------------ */

export const AZURE_EMOTIONS = [
  { value: "", label: "None" },
  { value: "neutral", label: "Neutral" },
  { value: "cheerful", label: "Cheerful" },
  { value: "sad", label: "Sad" },
  { value: "angry", label: "Angry" },
  { value: "excited", label: "Excited" },
  { value: "friendly", label: "Friendly" },
  { value: "hopeful", label: "Hopeful" },
  { value: "whispering", label: "Whispering" },
  { value: "terrified", label: "Terrified" },
  { value: "unfriendly", label: "Unfriendly" },
  { value: "shouting", label: "Shouting" },
  { value: "empathetic", label: "Empathetic" },
  { value: "calm", label: "Calm" },
  { value: "gentle", label: "Gentle" },
  { value: "serious", label: "Serious" },
  { value: "depressed", label: "Depressed" },
  { value: "embarrassed", label: "Embarrassed" },
  { value: "envious", label: "Envious" },
  { value: "lyrical", label: "Lyrical" },
  { value: "poetry-reading", label: "Poetry Reading" },
  { value: "narration-professional", label: "Narration (Professional)" },
  { value: "newscast-casual", label: "Newscast (Casual)" },
  { value: "newscast-formal", label: "Newscast (Formal)" },
  { value: "documentary-narration", label: "Documentary Narration" },
  { value: "chat", label: "Chat" },
  { value: "customer-service", label: "Customer Service" },
  { value: "assistant", label: "Assistant" },
] as const;

export const OUTPUT_FORMATS = [
  { value: "wav", label: "WAV" },
  { value: "mp3", label: "MP3" },
  { value: "ogg", label: "OGG" },
] as const;

/* ------------------------------------------------------------------ */
/*  Shared types                                                       */
/* ------------------------------------------------------------------ */

export type SynthesisMode = "tts" | "sts";

export interface BatchLineResult {
  line: string;
  status: "pending" | "success" | "error";
  audio_url?: string;
  latency_ms?: number;
  error?: string;
}

/* ------------------------------------------------------------------ */
/*  Sub-component prop interfaces                                      */
/* ------------------------------------------------------------------ */

export interface ConsoleHeaderProps {
  consoleOn: boolean;
  onToggleConsole: () => void;
  batchMode: boolean;
  onSetBatchMode: (batch: boolean) => void;
  synthesisMode: SynthesisMode;
  onSetSynthesisMode: (mode: SynthesisMode) => void;
  /** Whether the preview button should be visible */
  canPreview: boolean;
  onPreview: () => void;
  loading: boolean;
  vuLevels: { input: number; output: number; master: number };
}

export interface BatchPanelProps {
  batchText: string;
  onSetBatchText: (text: string) => void;
  batchLoading: boolean;
  batchProgress: number;
  batchResults: BatchLineResult[];
}

export interface TextToSpeechPanelProps {
  text: string;
  onSetText: (text: string) => void;
  lastResult: {
    audio_url: string;
    provider_name: string;
    latency_ms: number;
    duration_seconds?: number | null;
  } | null;
}

export interface SpeechToSpeechPanelProps {
  stsFile: File | null;
  onSetStsFile: (file: File | null) => void;
  stsLoading: boolean;
  stsResult: { audio_url: string; duration_seconds: number | null } | null;
  stsInputRef: RefObject<HTMLInputElement>;
  stsBlobUrl: string | null;
}

export interface ActivityLogProps {
  history: SynthesisHistoryItem[];
}

export interface VoiceChannelCardProps {
  profileId: string;
  onProfileSelect: (id: string) => void;
  profileOptions: { value: string; label: string }[];
  presetId: string;
  onPresetSelect: (id: string) => void;
  presets: PersonaPreset[];
  outputFormat: string;
  onSetOutputFormat: (format: string) => void;
  synthesisMode: SynthesisMode;
}

export interface AudioControlPanelProps {
  synthesisMode: SynthesisMode;
  batchMode: boolean;
  batchText: string;
  // Audio knobs
  speed: number;
  onSetSpeed: (v: number) => void;
  pitch: number;
  onSetPitch: (v: number) => void;
  volume: number;
  onSetVolume: (v: number) => void;
  // ElevenLabs
  isElevenLabs: boolean;
  stability: number;
  onSetStability: (v: number) => void;
  similarityBoost: number;
  onSetSimilarityBoost: (v: number) => void;
  speakerBoost: boolean;
  onSetSpeakerBoost: (v: boolean) => void;
  // Azure
  isAzure: boolean;
  emotion: string;
  onSetEmotion: (v: string) => void;
  // Action button
  loading: boolean;
  batchLoading: boolean;
  stsLoading: boolean;
  stsFile: File | null;
  profileId: string;
  text: string;
  onSynthesize: () => void;
  onBatchSynthesize: () => void;
  onSpeechToSpeech: () => void;
}
