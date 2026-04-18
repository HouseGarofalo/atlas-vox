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
  detector?: {
    health_failure_threshold: number;
    error_rate_spike_multiplier: number;
    latency_p99_threshold_ms: number;
    errors_per_minute_threshold: number;
    celery_backlog_threshold: number;
    memory_threshold_mb: number;
    disk_usage_threshold_pct: number;
  };
  mcp?: {
    enabled: boolean;
    server_path: string;
    server_exists: boolean;
    project_root: string;
    project_root_exists: boolean;
    fixes_this_hour: number;
    max_fixes_per_hour: number;
    total_fixes: number;
    recent_fixes: McpFixEntry[];
  };
}

export interface McpFixEntry {
  timestamp: number;
  event_rule: string;
  event_title: string;
  task: string;
  result: string;
  success: boolean;
}

export interface McpTestResult {
  claude_cli_found: boolean;
  claude_cli_version: string | null;
  claude_cli_path?: string;
  server_path_valid: boolean;
  server_path: string;
  project_root_valid: boolean;
  project_root: string;
  enabled: boolean;
  ready: boolean;
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

// --- VQ-36 quality dashboard payload ---

export interface QualityWerPoint {
  history_id: string;
  created_at: string;
  quality_wer: number;
}

export interface QualityVersionMetric {
  version_id: string;
  version_number: number;
  created_at: string;
  quality_wer: number | null;
  mos: number | null;
  speaker_similarity: number | null;
  is_regression: boolean | null;
  method: string | null;
  is_active: boolean;
}

export interface QualityRatingDistribution {
  up: number;
  down: number;
  total: number;
  up_pct: number;
}

export interface QualitySampleHealth {
  total: number;
  passed: number;
  failed: number;
  unknown: number;
  pass_rate_pct: number;
}

export interface QualityDashboardResponse {
  profile_id: string;
  profile_name: string;
  generated_at: string;
  overall_score: number;
  recent_wer: number | null;
  active_version_id: string | null;
  wer_series: QualityWerPoint[];
  version_metrics: QualityVersionMetric[];
  rating_distribution: QualityRatingDistribution;
  sample_health: QualitySampleHealth;
  synthesis_count: number;
  warnings: string[];
}

export interface ModelVersion {
  id: string;
  profile_id: string;
  version_number: number;
  /** Optional — not returned by all backend endpoints. */
  provider_name?: string;
  /** Raw provider-specific model identifier. */
  provider_model_id?: string | null;
  /** Filesystem path for local model checkpoints. */
  model_path?: string | null;
  /** JSON-encoded training config snapshot at version creation. */
  config_json?: string | null;
  /**
   * JSON-encoded quality metrics (WER, MOS proxy, similarity, regression
   * flag, duration_s, etc.). Callers should JSON.parse safely — shape
   * varies by provider and whether SL-27 regression detector has run.
   */
  metrics_json?: string | null;
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

// --- Pronunciation Dictionary types ---

export interface PronunciationEntry {
  id: string;
  word: string;
  ipa: string;
  language: string;
  profile_id: string | null;
  created_at: string;
  updated_at: string;
}

// --- Usage Analytics types ---

export interface UsageAnalytics {
  period_days: number;
  total_characters: number;
  total_requests: number;
  total_estimated_cost_usd: number;
  by_provider: Record<string, { characters: number; requests: number; cost_usd: number; avg_latency_ms: number }>;
  daily: Record<string, { characters: number; requests: number; cost_usd: number }>;
}

// --- Voice Favorites types ---

export interface VoiceFavoriteItem {
  id: string;
  provider: string;
  voice_id: string;
  collection_name: string | null;
  created_at: string;
}

// ── Admin System Settings ───────────────────────────────────────────────

export interface SystemSetting {
  id: string;
  category: string;
  key: string;
  value: string;
  value_type: "string" | "int" | "float" | "bool" | "json";
  is_secret: boolean;
  description: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface SystemInfo {
  app_name: string;
  app_env: string;
  version: string;
  debug: boolean;
  uptime_seconds: number;
  database_type: string;
  provider_count: number;
  active_providers: number;
  profile_count: number;
  total_synthesis: number;
  redis_connected: boolean;
  celery_connected: boolean;
  healing_enabled: boolean;
  healing_running: boolean;
}

export interface BackupResponse {
  data: string;
  settings_count: number;
  created_at: string;
}

// --- Azure Login types ---

export interface AzureDeviceCodeResponse {
  user_code: string;
  verification_uri: string;
  message: string;
  expires_in_seconds: number;
}

export interface AzureAuthStatus {
  authenticated: boolean;
  auth_method: string | null;
  user_display_name: string | null;
  user_email: string | null;
  expires_at: number | null;
  expires_in_seconds: number | null;
  device_code_pending: boolean;
  device_code_info: AzureDeviceCodeResponse | null;
  error: string | null;
}
