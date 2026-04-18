// API client — all backend calls go through this module.

import type {
  AudioDesignFile,
  AudioQualityBrief,
  AudioSample,
  ApiKeyResponse,
  AzureAuthStatus,
  AzureDeviceCodeResponse,
  BackupResponse,
  HealingIncident,
  HealingStatus,
  McpTestResult,
  PersonaPreset,
  PronunciationEntry,
  Provider,
  ProviderConfigResponse,
  ProviderHealth,
  ProviderTestResponse,
  SystemInfo,
  SystemSetting,
  TrainingJob,
  UsageAnalytics,
  Voice,
  VoiceFavoriteItem,
  VoiceProfile,
} from "../types";
import { createLogger } from "../utils/logger";
import { useAuthStore } from "../stores/authStore";

const logger = createLogger("ApiClient");

const API_BASE = "/api/v1";

/**
 * Structured API error that preserves HTTP status code and server detail.
 *
 * Usage in catch blocks:
 *   if (err instanceof ApiError && err.status === 401) { ... }
 *   if (err instanceof ApiError && err.isValidation) { ... }
 */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly requestId: string | null;

  constructor(status: number, detail: string, requestId: string | null = null) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.requestId = requestId;
  }

  get isUnauthorized() { return this.status === 401; }
  get isForbidden() { return this.status === 403; }
  get isNotFound() { return this.status === 404; }
  get isValidation() { return this.status === 422; }
  get isRateLimited() { return this.status === 429; }
  get isServerError() { return this.status >= 500; }
}

/**
 * Extra options recognised by ``request()`` that don't belong on the raw
 * ``RequestInit``. All optional — existing call sites continue to work.
 */
interface RequestOptions extends RequestInit {
  /**
   * Cancellation key. When set, any in-flight request registered under the
   * same key is aborted before the new one starts. Handy for:
   *   - search/autocomplete boxes where only the latest query matters
   *   - fetchProfiles() fired from several places without piling up
   * If omitted, requests default to keying on ``${method} ${path}``.
   */
  cancelKey?: string;
  /**
   * Explicit opt-out of cancellation (mostly used in tests).
   */
  noCancel?: boolean;
  /**
   * Caller-supplied AbortSignal. Composed with the internal signal so
   * cancelling EITHER aborts the request.
   */
  signal?: AbortSignal;
}

class ApiClient {
  private baseUrl: string;
  // Per-key registry of in-flight AbortControllers. A new request with the
  // same key aborts the prior one before starting, preventing duplicate
  // work and eliminating "zombie responses" that land after the user has
  // moved on to a different input.
  private inflight = new Map<string, AbortController>();

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  /**
   * Cancel every currently in-flight request. Call on logout or when
   * tearing down the app so lingering fetches don't leak auth-less state
   * into the next session.
   */
  abortAll(): void {
    for (const ctrl of this.inflight.values()) {
      try { ctrl.abort(); } catch { /* ignore */ }
    }
    this.inflight.clear();
  }

  /**
   * Cancel a specific in-flight request by its key (or method+path tuple
   * if the caller used the default key scheme).
   */
  cancel(key: string): void {
    const ctrl = this.inflight.get(key);
    if (ctrl) {
      try { ctrl.abort(); } catch { /* ignore */ }
      this.inflight.delete(key);
    }
  }

  private async fetchWithRetry(url: string, options: RequestInit, maxRetries = 3): Promise<Response> {
    let lastError: Error | null = null;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const response = await fetch(url, options);
        if (response.status >= 500 && attempt < maxRetries) {
          const delay = Math.min(1000 * Math.pow(2, attempt), 8000) + Math.random() * 1000;
          logger.warn("API retry", { attempt: attempt + 1, status: response.status, delay: Math.round(delay) });
          await new Promise(r => setTimeout(r, delay));
          continue;
        }
        return response;
      } catch (err) {
        lastError = err as Error;
        // If the caller aborted, don't retry — bubble it up immediately.
        if ((err as Error).name === "AbortError") throw err;
        if (attempt < maxRetries) {
          const delay = Math.min(1000 * Math.pow(2, attempt), 8000) + Math.random() * 1000;
          logger.warn("API retry (network)", { attempt: attempt + 1, error: (err as Error).message, delay: Math.round(delay) });
          await new Promise(r => setTimeout(r, delay));
        }
      }
    }
    throw lastError ?? new Error("Request failed after retries");
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const method = (options.method as string) ?? "GET";
    const { cancelKey, noCancel, signal: callerSignal, ...fetchInit } = options;
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...fetchInit.headers,
    };
    // Remove Content-Type for FormData (browser sets multipart boundary)
    if (fetchInit.body instanceof FormData) {
      delete (headers as Record<string, string>)["Content-Type"];
    }

    // Inject auth header only for API key mode.
    // JWT auth uses httpOnly cookies sent automatically via credentials: 'include'.
    const { apiKey, authDisabled } = useAuthStore.getState();
    if (!authDisabled && apiKey) {
      (headers as Record<string, string>)["Authorization"] = `Bearer ${apiKey}`;
    }

    // Resolve the cancellation key. "noCancel" skips the registry so tests
    // and certain long-running uploads (batch synth) don't clobber each other.
    const effectiveKey = noCancel ? null : cancelKey ?? `${method} ${path}`;
    const controller = new AbortController();
    if (effectiveKey) {
      // Abort any previous in-flight call under the same key.
      const prior = this.inflight.get(effectiveKey);
      if (prior) {
        try { prior.abort(); } catch { /* ignore */ }
      }
      this.inflight.set(effectiveKey, controller);
    }

    // Compose signals: abort if EITHER the internal controller or the
    // caller-supplied signal fires.
    if (callerSignal) {
      if (callerSignal.aborted) controller.abort();
      else callerSignal.addEventListener("abort", () => controller.abort(), { once: true });
    }

    logger.info("API request", { method, url });

    let response: Response;
    try {
      // credentials: 'include' ensures httpOnly cookies (JWT) are sent with every request
      response = await this.fetchWithRetry(
        url,
        { ...fetchInit, headers, credentials: "include", signal: controller.signal },
      );
    } finally {
      if (effectiveKey && this.inflight.get(effectiveKey) === controller) {
        this.inflight.delete(effectiveKey);
      }
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      const requestId = response.headers.get("X-Request-ID");
      logger.error("API error", { method, url, status: response.status, detail: error.detail, requestId });

      // Auto-logout on 401 to force re-authentication
      if (response.status === 401) {
        const { authDisabled } = useAuthStore.getState();
        if (!authDisabled) {
          logger.warn("Session expired, logging out");
          useAuthStore.getState().logout();
        }
      }

      throw new ApiError(
        response.status,
        error.detail || `HTTP ${response.status}`,
        requestId,
      );
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
  synthesize(data: { text: string; profile_id: string; preset_id?: string; speed?: number; pitch?: number; volume?: number; output_format?: string; ssml?: boolean; include_word_boundaries?: boolean; voice_settings?: Record<string, unknown>; version_id?: string }) {
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
    return this.request<{ voices: Voice[]; count: number; total: number }>("/voices?limit=5000");
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

  // Azure Login (Device Code Flow)
  initiateAzureLogin(providerName = "azure_speech") {
    return this.request<AzureDeviceCodeResponse>(`/providers/${providerName}/azure-login/initiate`, { method: "POST" });
  }
  getAzureLoginStatus(providerName = "azure_speech") {
    return this.request<AzureAuthStatus>(`/providers/${providerName}/azure-login/status`);
  }
  azureLogout(providerName = "azure_speech") {
    return this.request<{ success: boolean; message: string }>(`/providers/${providerName}/azure-login/logout`, { method: "POST" });
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
    return this.request<HealingStatus>("/healing/status");
  }
  getHealingIncidents(limit = 50, severity?: string) {
    const qs = new URLSearchParams({ limit: String(limit) });
    if (severity) qs.set("severity", severity);
    return this.request<{ incidents: HealingIncident[]; count: number }>(`/healing/incidents?${qs}`);
  }
  forceHealthCheck() {
    return this.request<{ healthy: boolean; checks: Record<string, string>; consecutive_failures: number }>("/healing/check", { method: "POST" });
  }
  toggleHealing(enable: boolean) {
    return this.request<{ enabled: boolean; running: boolean }>(`/healing/toggle?enable=${enable}`, { method: "POST" });
  }

  // Sample Quality & Training Readiness
  getSampleQuality(profileId: string, sampleId: string) {
    return this.request<{ passed: boolean; score: number; issues: { code: string; severity: string; message: string }[]; metrics: Record<string, number> }>(`/profiles/${profileId}/samples/${sampleId}/quality`);
  }

  getTrainingReadiness(profileId: string) {
    return this.request<{ ready: boolean; score: number; sample_count: number; total_duration: number; issues: { code: string; severity: string; message: string }[]; recommendations: string[] }>(`/profiles/${profileId}/samples/readiness`);
  }

  /**
   * VQ-36 — per-profile quality dashboard. One aggregated payload with
   * WER time-series, per-version metrics, rating distribution, and
   * sample health so the page renders instantly.
   */
  getQualityDashboard(profileId: string, werLimit: number = 50) {
    return this.request<QualityDashboardResponse>(
      `/profiles/${profileId}/quality-dashboard?wer_limit=${werLimit}`,
    );
  }

  /**
   * SL-29 — active-learning sample recommender. Returns up to `count`
   * sentences selected by greedy set-cover over a curated bank to
   * maximally fill this profile's remaining phoneme gaps.
   */
  /**
   * SL-30 — context-adaptive voice routing. Classifies the given text
   * into a context (conversational/narrative/emotional/technical/
   * dialogue/long_form) and returns profile recommendations ranked by
   * provider affinity + preference bias.
   */
  recommendVoice(text: string, limit: number = 3) {
    return this.request<{
      text_excerpt: string;
      top_context: "conversational" | "narrative" | "emotional" | "technical" | "dialogue" | "long_form";
      context_scores: { context: string; score: number; signals: string[] }[];
      recommendations: {
        profile_id: string;
        profile_name: string;
        provider_name: string;
        voice_id: string | null;
        score: number;
        reasons: string[];
      }[];
    }>("/synthesis/recommend-voice", {
      method: "POST",
      body: JSON.stringify({ text, limit }),
      cancelKey: "recommendVoice",  // coalesce rapid typing
    });
  }

  getRecommendedSamples(profileId: string, count: number = 10) {
    return this.request<{
      profile_id: string;
      method: "phonemizer" | "bigram_approx";
      gap_count_before: number;
      gap_count_after: number;
      already_recorded_skipped: number;
      recommendations: {
        text: string;
        fills_gaps: string[];
        gap_fill_count: number;
        priority: number;
      }[];
    }>(`/profiles/${profileId}/recommended-samples?count=${count}`);
  }

  // Audio Tools
  enhanceSample(profileId: string, sampleId: string) {
    return this.request<{ output_filename: string; audio_url: string }>("/audio-tools/isolate", {
      method: "POST",
      body: JSON.stringify({ profile_id: profileId, sample_id: sampleId }),
    });
  }

  speechToSpeech(audio: File, voiceId: string, provider: string) {
    const form = new FormData();
    form.append("audio", audio);
    const qs = new URLSearchParams({
      voice_id: voiceId,
      provider_name: provider,
    });
    return this.request<{ output_filename: string; audio_url: string }>(
      `/audio-tools/speech-to-speech?${qs.toString()}`,
      { method: "POST", body: form },
    );
  }

  designVoice(description: string, text?: string) {
    return this.request<{ previews: { voice_id: string; audio_base64: string }[] }>(
      "/audio-tools/design-voice",
      { method: "POST", body: JSON.stringify({ description, text }) },
    );
  }

  generateSoundEffect(description: string, duration?: number) {
    return this.request<{ output_filename: string; audio_url: string }>("/audio-tools/sound-effect", {
      method: "POST",
      body: JSON.stringify({ description, duration_seconds: duration || 5.0 }),
    });
  }

  // Audio URL helpers
  audioUrl(filename: string) {
    return `${this.baseUrl}/audio/${filename}`;
  }

  /** Build a full URL from a relative API audio URL (e.g., /api/v1/audio/design/foo.wav). */
  fullAudioUrl(relativeUrl: string) {
    return `${this.baseUrl.replace("/api/v1", "")}${relativeUrl}`;
  }

  // ---------- Audio Design Studio ----------

  audioDesignUpload(file: File) {
    const form = new FormData();
    form.append("audio", file);
    return this.request<{ file: AudioDesignFile; quality: AudioQualityBrief | null }>(
      "/audio-tools/upload",
      { method: "POST", body: form },
    );
  }

  audioDesignListFiles(skip = 0, limit = 100) {
    return this.request<{ files: AudioDesignFile[]; count: number; total: number }>(`/audio-tools/files?skip=${skip}&limit=${limit}`);
  }

  audioDesignDeleteFile(fileId: string) {
    return this.request<void>(`/audio-tools/files/${fileId}`, { method: "DELETE" });
  }

  audioDesignTrim(fileId: string, start: number, end: number) {
    return this.request<{ file: AudioDesignFile }>("/audio-tools/trim", {
      method: "POST",
      body: JSON.stringify({ file_id: fileId, start_seconds: start, end_seconds: end }),
    });
  }

  audioDesignConcat(fileIds: string[], crossfadeMs = 0) {
    return this.request<{ file: AudioDesignFile }>("/audio-tools/concat", {
      method: "POST",
      body: JSON.stringify({ file_ids: fileIds, crossfade_ms: crossfadeMs }),
    });
  }

  audioDesignEffects(fileId: string, effects: { type: string; strength?: number; target_db?: number; threshold_db?: number; gain_db?: number }[]) {
    return this.request<{ file: AudioDesignFile }>("/audio-tools/effects", {
      method: "POST",
      body: JSON.stringify({ file_id: fileId, effects }),
    });
  }

  audioDesignExport(fileId: string, format: string, sampleRate: number | null) {
    return this.request<{ file_id: string; filename: string; audio_url: string; format: string; sample_rate: number; duration_seconds: number; file_size_bytes: number }>("/audio-tools/export", {
      method: "POST",
      body: JSON.stringify({ file_id: fileId, format, sample_rate: sampleRate }),
    });
  }

  audioDesignAnalyze(fileId: string) {
    return this.request<{ file_id: string; duration_seconds: number; sample_rate: number; quality: AudioQualityBrief; pitch_mean: number | null; pitch_std: number | null; energy_mean: number | null; energy_std: number | null; spectral_centroid_mean: number | null; rms_db: number | null }>("/audio-tools/analyze", {
      method: "POST",
      body: JSON.stringify({ file_id: fileId }),
    });
  }

  audioDesignIsolate(fileId: string) {
    return this.request<{ file: AudioDesignFile }>("/audio-tools/isolate-file", {
      method: "POST",
      body: JSON.stringify({ file_id: fileId }),
    });
  }

  // Pronunciation Dictionary (E1)
  listPronunciation(params?: { language?: string; profile_id?: string; search?: string }) {
    const qs = new URLSearchParams();
    if (params?.language) qs.set("language", params.language);
    if (params?.profile_id) qs.set("profile_id", params.profile_id);
    if (params?.search) qs.set("search", params.search);
    return this.request<{ entries: PronunciationEntry[]; count: number }>(`/pronunciation?${qs}`);
  }
  createPronunciation(data: { word: string; ipa: string; language?: string; profile_id?: string }) {
    return this.request<PronunciationEntry>("/pronunciation", { method: "POST", body: JSON.stringify(data) });
  }
  updatePronunciation(id: string, data: { word?: string; ipa?: string; language?: string }) {
    return this.request<PronunciationEntry>(`/pronunciation/${id}`, { method: "PUT", body: JSON.stringify(data) });
  }
  deletePronunciation(id: string) {
    return this.request<void>(`/pronunciation/${id}`, { method: "DELETE" });
  }

  // Usage Analytics (E2)
  getUsage(params?: { days?: number; provider?: string }) {
    const qs = new URLSearchParams();
    if (params?.days) qs.set("days", String(params.days));
    if (params?.provider) qs.set("provider", params.provider);
    return this.request<UsageAnalytics>(`/usage?${qs}`);
  }

  // Voice Favorites (E7)
  listFavorites(collection?: string) {
    const qs = collection ? `?collection=${encodeURIComponent(collection)}` : "";
    return this.request<{ favorites: VoiceFavoriteItem[]; count: number }>(`/favorites${qs}`);
  }
  addFavorite(data: { provider: string; voice_id: string; collection_name?: string }) {
    return this.request<VoiceFavoriteItem>("/favorites", { method: "POST", body: JSON.stringify(data) });
  }
  removeFavorite(id: string) {
    return this.request<void>(`/favorites/${id}`, { method: "DELETE" });
  }
  listCollections() {
    return this.request<{ collections: string[] }>("/favorites/collections");
  }

  // ── Admin System Settings ─────────────────────────────────────────────

  listSettings(category?: string) {
    const path = category ? `/admin/settings/${category}` : "/admin/settings";
    return this.request<SystemSetting[]>(path);
  }
  getSetting(category: string, key: string) {
    return this.request<SystemSetting>(`/admin/settings/${category}/${key}`);
  }
  updateSetting(category: string, key: string, data: { value: string; value_type?: string; is_secret?: boolean; description?: string }) {
    return this.request<SystemSetting>(`/admin/settings/${category}/${key}`, { method: "PUT", body: JSON.stringify(data) });
  }
  bulkUpdateSettings(category: string, settings: Array<{ key: string; value: string; value_type?: string; is_secret?: boolean; description?: string }>) {
    return this.request<SystemSetting[]>("/admin/settings", { method: "PUT", body: JSON.stringify({ category, settings }) });
  }
  deleteSetting(category: string, key: string) {
    return this.request<{ deleted: boolean }>(`/admin/settings/${category}/${key}`, { method: "DELETE" });
  }
  seedSettings() {
    return this.request<{ seeded: number; message: string }>("/admin/settings/seed", { method: "POST" });
  }
  getSystemInfo() {
    return this.request<SystemInfo>("/admin/system-info");
  }
  backupSettings() {
    return this.request<BackupResponse>("/admin/backup", { method: "POST" });
  }
  restoreSettings(data: string) {
    return this.request<{ restored: number; message: string }>("/admin/restore", { method: "POST", body: JSON.stringify({ data }) });
  }

  // ── Healing (additional) ──────────────────────────────────────────────

  testMcpBridge() {
    return this.request<McpTestResult>("/healing/mcp/test", { method: "POST" });
  }
  reconfigureHealing() {
    return this.request<{ reconfigured: boolean }>("/healing/reconfigure", { method: "POST" });
  }
}

export const api = new ApiClient();

// Default export for call sites that prefer it (hooks, tests). Points at
// the same singleton instance.
export default api;
