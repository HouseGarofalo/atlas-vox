export interface VoiceProfile {
  id: string;
  name: string;
  description: string | null;
  language: string;
  provider_name: string;
  voice_id: string | null;
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
  provider_type: "cloud" | "local" | "gpu";
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
  supports_word_boundaries: boolean;
  supports_pronunciation_assessment: boolean;
  supports_transcription: boolean;
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

export interface ProviderFieldSchema {
  name: string;
  field_type: "text" | "password" | "select";
  label: string;
  required: boolean;
  is_secret: boolean;
  options?: string[];
  default?: string;
}

export interface ProviderConfigResponse {
  enabled: boolean;
  gpu_mode: string;
  config: Record<string, string>;
  config_schema: ProviderFieldSchema[];
}

export interface ProviderTestResponse {
  success: boolean;
  audio_url: string | null;
  duration_seconds: number | null;
  latency_ms: number;
  error: string | null;
}

export interface Voice {
  voice_id: string;
  name: string;
  language: string;
  provider: string;
  provider_display: string;
  gender?: string;
  preview_url?: string;
  tags?: string[];
}

export interface AudioSample {
  id: string;
  profile_id: string;
  filename: string;
  original_filename: string;
  format: string;
  duration_seconds: number | null;
  sample_rate: number | null;
  file_size_bytes: number | null;
  preprocessed: boolean;
  transcript: string | null;
  transcript_source: string | null;
  created_at: string;
}

export interface ApiKeyResponse {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

export interface SynthesisResult {
  id: string;
  audio_url: string;
  duration_seconds: number | null;
  latency_ms: number;
  profile_id: string;
  provider_name: string;
}

export interface SynthesisHistoryItem {
  id: string;
  text: string;
  audio_url: string;
  profile_id: string;
  provider_name: string;
  latency_ms?: number;
  created_at: string;
}

export interface ComparisonResult {
  profile_id: string;
  profile_name?: string;
  audio_url: string | null;
  duration_seconds: number | null;
  latency_ms: number;
  provider_name: string;
  error: string | null;
}

// --- Healing types (previously local to HealingPage) ---

export interface HealingStatus {
  enabled: boolean;
  running: boolean;
  uptime_seconds: number;
  incidents_handled: number;
  health: { healthy: boolean; consecutive_failures: number; checks_count: number };
  telemetry: { current_error_rate: number; avg_error_rate: number; snapshots_count: number };
  logs: { errors_last_minute: number; errors_last_5_minutes: number; total_tracked: number };
  mcp?: { enabled: boolean; fixes_this_hour: number; max_fixes_per_hour: number; total_fixes: number };
}

export interface HealingIncident {
  id: string;
  severity: string;
  category: string;
  title: string;
  description: string | null;
  action_taken: string | null;
  action_detail: string | null;
  outcome: string;
  resolved_at?: string | null;
  created_at?: string | null;
}

// --- Model Version (previously local to ProfilesPage) ---

export interface ModelVersion {
  id: string;
  profile_id: string;
  version_number: number;
  provider_name: string;
  created_at: string;
}

// --- Training quality types (previously local to TrainingStudioPage) ---

export interface QualityIssue {
  code: string;
  severity: string;
  message: string;
}

export interface QualityResult {
  passed: boolean;
  score: number;
  issues: QualityIssue[];
  metrics: Record<string, number>;
}

export interface ReadinessResult {
  ready: boolean;
  score: number;
  sample_count: number;
  total_duration: number;
  issues: QualityIssue[];
  recommendations: string[];
}

// --- Audio Design types (previously local to audioDesignStore) ---

export interface AudioDesignFile {
  file_id: string;
  filename: string;
  original_filename: string;
  duration_seconds: number;
  sample_rate: number;
  channels: number;
  format: string;
  file_size_bytes: number;
  audio_url: string;
}

export interface AudioQualityBrief {
  passed: boolean;
  score: number;
  snr_db: number | null;
  rms_db: number | null;
  issues: QualityIssue[];
}
