import type {
  AudioSample,
  ApiKeyResponse,
  PersonaPreset,
  Provider,
  ProviderConfigResponse,
  ProviderHealth,
  ProviderTestResponse,
  TrainingJob,
  Voice,
  VoiceProfile,
} from "../types";
import { createLogger } from "../utils/logger";

const logger = createLogger("ApiClient");

const API_BASE = "/api/v1";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const method = (options.method as string) ?? "GET";
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...options.headers,
    };
    // Remove Content-Type for FormData (browser sets multipart boundary)
    if (options.body instanceof FormData) {
      delete (headers as Record<string, string>)["Content-Type"];
    }

    logger.info("API request", { method, url });

    const response = await fetch(url, { ...options, headers });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      logger.error("API error", { method, url, status: response.status, detail: error.detail });
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    logger.info("API response", { method, url, status: response.status });

    if (response.status === 204) return undefined as T;
    return response.json();
  }

  // Health
  health() {
    return this.request<{ status: string; service: string; version: string }>("/health");
  }

  // Profiles
  listProfiles() {
    return this.request<{ profiles: VoiceProfile[]; count: number }>("/profiles");
  }
  getProfile(id: string) {
    return this.request<VoiceProfile>(`/profiles/${id}`);
  }
  createProfile(data: { name: string; description?: string; language?: string; provider_name: string; voice_id?: string; tags?: string[] }) {
    return this.request<VoiceProfile>("/profiles", { method: "POST", body: JSON.stringify(data) });
  }
  updateProfile(id: string, data: Record<string, unknown>) {
    return this.request<VoiceProfile>(`/profiles/${id}`, { method: "PUT", body: JSON.stringify(data) });
  }
  deleteProfile(id: string) {
    return this.request<void>(`/profiles/${id}`, { method: "DELETE" });
  }

  // Versions
  listVersions(profileId: string) {
    return this.request<{ versions: { id: string; profile_id: string; version_number: number; provider_name: string; created_at: string }[]; count: number }>(`/profiles/${profileId}/versions`);
  }
  activateVersion(profileId: string, versionId: string) {
    return this.request<VoiceProfile>(`/profiles/${profileId}/activate-version/${versionId}`, { method: "POST" });
  }

  // Samples
  uploadSamples(profileId: string, files: File[]) {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return this.request<AudioSample[]>(`/profiles/${profileId}/samples`, { method: "POST", body: form });
  }
  listSamples(profileId: string) {
    return this.request<{ samples: AudioSample[]; count: number }>(`/profiles/${profileId}/samples`);
  }
  deleteSample(profileId: string, sampleId: string) {
    return this.request<void>(`/profiles/${profileId}/samples/${sampleId}`, { method: "DELETE" });
  }
  getSampleAnalysis(profileId: string, sampleId: string) {
    return this.request<{ sample_id: string; duration_seconds: number; sample_rate: number; channels: number; rms_db: number; snr_db: number | null }>(`/profiles/${profileId}/samples/${sampleId}/analysis`);
  }
  preprocessSamples(profileId: string) {
    return this.request<{ profile_id: string; processed: number; skipped: number; message?: string; task_id?: string }>(`/profiles/${profileId}/samples/preprocess`, { method: "POST" });
  }
  transcribeSample(profileId: string, sampleId: string, locale = "en-US") {
    return this.request<{ sample_id: string; transcript: string; source: string }>(`/profiles/${profileId}/samples/${sampleId}/transcribe`, { method: "POST", body: JSON.stringify({ locale }) });
  }
  assessSample(profileId: string, sampleId: string, referenceText?: string, locale = "en-US") {
    const qs = new URLSearchParams({ locale });
    if (referenceText) qs.set("reference_text", referenceText);
    return this.request<{ sample_id: string; accuracy_score: number; fluency_score: number; completeness_score: number; pronunciation_score: number; word_scores?: { word: string; accuracy_score: number; error_type?: string }[] }>(`/profiles/${profileId}/samples/${sampleId}/assess?${qs}`, { method: "POST" });
  }

  // Training
  startTraining(profileId: string, data: { provider_name?: string; config?: Record<string, unknown> }) {
    return this.request<TrainingJob>(`/profiles/${profileId}/train`, { method: "POST", body: JSON.stringify(data) });
  }
  listTrainingJobs(params?: { profile_id?: string; status?: string }) {
    const qs = new URLSearchParams();
    if (params?.profile_id) qs.set("profile_id", params.profile_id);
    if (params?.status) qs.set("status", params.status);
    const q = qs.toString();
    return this.request<{ jobs: TrainingJob[]; count: number }>(`/training/jobs${q ? `?${q}` : ""}`);
  }
  getTrainingJob(jobId: string) {
    return this.request<TrainingJob>(`/training/jobs/${jobId}`);
  }
  cancelTrainingJob(jobId: string) {
    return this.request<TrainingJob>(`/training/jobs/${jobId}/cancel`, { method: "POST" });
  }

  // Synthesis
  synthesize(data: { text: string; profile_id: string; preset_id?: string; speed?: number; pitch?: number; volume?: number; output_format?: string; ssml?: boolean; include_word_boundaries?: boolean }) {
    return this.request<{ id: string; audio_url: string; duration_seconds: number | null; latency_ms: number; profile_id: string; provider_name: string; word_boundaries?: { text: string; offset_ms: number; duration_ms: number; word_index: number }[] }>("/synthesize", { method: "POST", body: JSON.stringify(data) });
  }
  batchSynthesize(data: { lines: string[]; profile_id: string; preset_id?: string; speed?: number }) {
    return this.request<{ id: string; audio_url: string; duration_seconds: number | null; latency_ms: number; profile_id: string; provider_name: string }[]>("/synthesize/batch", { method: "POST", body: JSON.stringify(data) });
  }
  getSynthesisHistory(limit = 50, profileId?: string) {
    const qs = new URLSearchParams({ limit: String(limit) });
    if (profileId) qs.set("profile_id", profileId);
    return this.request<{ id: string; text: string; audio_url: string; profile_id: string; provider_name: string; created_at: string }[]>(`/synthesis/history?${qs}`);
  }

  // Comparison
  compare(data: { text: string; profile_ids: string[]; speed?: number; pitch?: number }) {
    return this.request<{ text: string; results: { profile_id: string; audio_url: string; duration_seconds: number | null; latency_ms: number; provider_name: string; error: string | null }[] }>("/compare", { method: "POST", body: JSON.stringify(data) });
  }

  // Providers
  listProviders() {
    return this.request<{ providers: Provider[]; count: number }>("/providers");
  }
  getProvider(name: string) {
    return this.request<Provider>(`/providers/${name}`);
  }
  checkProviderHealth(name: string) {
    return this.request<ProviderHealth>(`/providers/${name}/health`, { method: "POST" });
  }
  listProviderVoices(name: string) {
    return this.request<{ voices: Voice[]; count: number }>(`/providers/${name}/voices`);
  }
  listAllVoices() {
    return this.request<{ voices: Voice[]; count: number }>("/voices");
  }
  previewVoice(data: { provider: string; voice_id: string; text?: string }) {
    return this.request<{ audio_url: string }>("/voices/preview", { method: "POST", body: JSON.stringify(data) });
  }

  // Provider Config (Admin)
  getProviderConfig(name: string) {
    return this.request<ProviderConfigResponse>(`/providers/${name}/config`);
  }
  updateProviderConfig(name: string, data: { enabled?: boolean; gpu_mode?: string; config?: Record<string, string> }) {
    return this.request<ProviderConfigResponse>(`/providers/${name}/config`, { method: "PUT", body: JSON.stringify(data) });
  }
  testProvider(name: string, data?: { text?: string; voice_id?: string }) {
    return this.request<ProviderTestResponse>(`/providers/${name}/test`, { method: "POST", body: JSON.stringify(data ?? {}) });
  }

  // Presets
  listPresets() {
    return this.request<{ presets: PersonaPreset[]; count: number }>("/presets");
  }
  createPreset(data: { name: string; description?: string; speed?: number; pitch?: number; volume?: number }) {
    return this.request<PersonaPreset>("/presets", { method: "POST", body: JSON.stringify(data) });
  }
  updatePreset(id: string, data: Record<string, unknown>) {
    return this.request<PersonaPreset>(`/presets/${id}`, { method: "PUT", body: JSON.stringify(data) });
  }
  deletePreset(id: string) {
    return this.request<void>(`/presets/${id}`, { method: "DELETE" });
  }

  // API Keys
  listApiKeys() {
    return this.request<{ api_keys: ApiKeyResponse[]; count: number }>("/api-keys");
  }
  createApiKey(data: { name: string; scopes: string[] }) {
    return this.request<{ id: string; name: string; key: string; key_prefix: string; scopes: string[]; created_at: string }>("/api-keys", { method: "POST", body: JSON.stringify(data) });
  }
  revokeApiKey(id: string) {
    return this.request<void>(`/api-keys/${id}`, { method: "DELETE" });
  }

  // Self-Healing
  getHealingStatus() {
    return this.request<{
      enabled: boolean;
      running: boolean;
      uptime_seconds: number;
      incidents_handled: number;
      health: { healthy: boolean; consecutive_failures: number; checks_count: number };
      telemetry: { current_error_rate: number; avg_error_rate: number; snapshots_count: number };
      logs: { errors_last_minute: number; errors_last_5_minutes: number; total_tracked: number };
      mcp?: { enabled: boolean; fixes_this_hour: number; max_fixes_per_hour: number; total_fixes: number };
    }>("/healing/status");
  }
  getHealingIncidents(limit = 50, severity?: string) {
    const qs = new URLSearchParams({ limit: String(limit) });
    if (severity) qs.set("severity", severity);
    return this.request<{ incidents: { id: string; severity: string; category: string; title: string; description: string | null; action_taken: string | null; action_detail: string | null; outcome: string; created_at: string }[]; count: number }>(`/healing/incidents?${qs}`);
  }
  forceHealthCheck() {
    return this.request<{ healthy: boolean; checks: Record<string, string>; consecutive_failures: number }>("/healing/check", { method: "POST" });
  }
  toggleHealing(enable: boolean) {
    return this.request<{ enabled: boolean; running: boolean }>(`/healing/toggle?enable=${enable}`, { method: "POST" });
  }

  // Audio URL helper
  audioUrl(filename: string) {
    return `${this.baseUrl}/audio/${filename}`;
  }
}

export const api = new ApiClient();
