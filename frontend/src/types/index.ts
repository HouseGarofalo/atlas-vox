export interface VoiceProfile {
  id: string;
  name: string;
  description: string | null;
  language: string;
  provider_name: string;
  status: "pending" | "training" | "ready" | "error" | "archived";
  tags: string[] | null;
  active_version_id: string | null;
  sample_count: number;
  version_count: number;
  created_at: string;
  updated_at: string;
}

export interface Provider {
  id: string;
  name: string;
  display_name: string;
  provider_type: "cloud" | "local";
  enabled: boolean;
  gpu_mode: string;
  capabilities: ProviderCapabilities | null;
  health: ProviderHealth | null;
}

export interface ProviderCapabilities {
  supports_cloning: boolean;
  supports_fine_tuning: boolean;
  supports_streaming: boolean;
  supports_ssml: boolean;
  supports_zero_shot: boolean;
  supports_batch: boolean;
  requires_gpu: boolean;
  gpu_mode: string;
  min_samples_for_cloning: number;
  max_text_length: number;
  supported_languages: string[];
  supported_output_formats: string[];
}

export interface ProviderHealth {
  name: string;
  healthy: boolean;
  latency_ms: number | null;
  error: string | null;
}

export interface TrainingJob {
  id: string;
  profile_id: string;
  provider_name: string;
  status: "queued" | "preprocessing" | "training" | "completed" | "failed" | "cancelled";
  progress: number;
  error_message: string | null;
  result_version_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface PersonaPreset {
  id: string;
  name: string;
  description: string | null;
  speed: number;
  pitch: number;
  volume: number;
  is_system: boolean;
}
