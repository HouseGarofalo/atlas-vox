const API_BASE = "/api/v1";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...options.headers,
    };
    // Remove Content-Type for FormData (browser sets multipart boundary)
    if (options.body instanceof FormData) {
      delete (headers as Record<string, string>)["Content-Type"];
    }

    const response = await fetch(url, { ...options, headers });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    if (response.status === 204) return undefined as T;
    return response.json();
  }

  // Health
  health() {
    return this.request<{ status: string; service: string; version: string }>("/health");
  }

  // Profiles
  listProfiles() {
    return this.request<{ profiles: any[]; count: number }>("/profiles");
  }
  getProfile(id: string) {
    return this.request<any>(`/profiles/${id}`);
  }
  createProfile(data: { name: string; description?: string; language?: string; provider_name: string; tags?: string[] }) {
    return this.request<any>("/profiles", { method: "POST", body: JSON.stringify(data) });
  }
  updateProfile(id: string, data: Record<string, any>) {
    return this.request<any>(`/profiles/${id}`, { method: "PUT", body: JSON.stringify(data) });
  }
  deleteProfile(id: string) {
    return this.request<void>(`/profiles/${id}`, { method: "DELETE" });
  }

  // Versions
  listVersions(profileId: string) {
    return this.request<{ versions: any[]; count: number }>(`/profiles/${profileId}/versions`);
  }
  activateVersion(profileId: string, versionId: string) {
    return this.request<any>(`/profiles/${profileId}/activate-version/${versionId}`, { method: "POST" });
  }

  // Samples
  uploadSamples(profileId: string, files: File[]) {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return this.request<any[]>(`/profiles/${profileId}/samples`, { method: "POST", body: form });
  }
  listSamples(profileId: string) {
    return this.request<{ samples: any[]; count: number }>(`/profiles/${profileId}/samples`);
  }
  deleteSample(profileId: string, sampleId: string) {
    return this.request<void>(`/profiles/${profileId}/samples/${sampleId}`, { method: "DELETE" });
  }
  getSampleAnalysis(profileId: string, sampleId: string) {
    return this.request<any>(`/profiles/${profileId}/samples/${sampleId}/analysis`);
  }
  preprocessSamples(profileId: string) {
    return this.request<any>(`/profiles/${profileId}/samples/preprocess`, { method: "POST" });
  }

  // Training
  startTraining(profileId: string, data: { provider_name?: string; config?: Record<string, any> }) {
    return this.request<any>(`/profiles/${profileId}/train`, { method: "POST", body: JSON.stringify(data) });
  }
  listTrainingJobs(params?: { profile_id?: string; status?: string }) {
    const qs = new URLSearchParams();
    if (params?.profile_id) qs.set("profile_id", params.profile_id);
    if (params?.status) qs.set("status", params.status);
    const q = qs.toString();
    return this.request<{ jobs: any[]; count: number }>(`/training/jobs${q ? `?${q}` : ""}`);
  }
  getTrainingJob(jobId: string) {
    return this.request<any>(`/training/jobs/${jobId}`);
  }
  cancelTrainingJob(jobId: string) {
    return this.request<any>(`/training/jobs/${jobId}/cancel`, { method: "POST" });
  }

  // Synthesis
  synthesize(data: { text: string; profile_id: string; preset_id?: string; speed?: number; pitch?: number; volume?: number; output_format?: string; ssml?: boolean }) {
    return this.request<{ id: string; audio_url: string; duration_seconds: number | null; latency_ms: number; profile_id: string; provider_name: string }>("/synthesize", { method: "POST", body: JSON.stringify(data) });
  }
  batchSynthesize(data: { lines: string[]; profile_id: string; preset_id?: string; speed?: number }) {
    return this.request<any[]>("/synthesize/batch", { method: "POST", body: JSON.stringify(data) });
  }
  getSynthesisHistory(limit = 50, profileId?: string) {
    const qs = new URLSearchParams({ limit: String(limit) });
    if (profileId) qs.set("profile_id", profileId);
    return this.request<any[]>(`/synthesis/history?${qs}`);
  }

  // Comparison
  compare(data: { text: string; profile_ids: string[]; speed?: number; pitch?: number }) {
    return this.request<{ text: string; results: any[] }>("/compare", { method: "POST", body: JSON.stringify(data) });
  }

  // Providers
  listProviders() {
    return this.request<{ providers: any[]; count: number }>("/providers");
  }
  getProvider(name: string) {
    return this.request<any>(`/providers/${name}`);
  }
  checkProviderHealth(name: string) {
    return this.request<any>(`/providers/${name}/health`, { method: "POST" });
  }
  listProviderVoices(name: string) {
    return this.request<any>(`/providers/${name}/voices`);
  }

  // Presets
  listPresets() {
    return this.request<{ presets: any[]; count: number }>("/presets");
  }
  createPreset(data: { name: string; description?: string; speed?: number; pitch?: number; volume?: number }) {
    return this.request<any>("/presets", { method: "POST", body: JSON.stringify(data) });
  }
  updatePreset(id: string, data: Record<string, any>) {
    return this.request<any>(`/presets/${id}`, { method: "PUT", body: JSON.stringify(data) });
  }
  deletePreset(id: string) {
    return this.request<void>(`/presets/${id}`, { method: "DELETE" });
  }

  // API Keys
  listApiKeys() {
    return this.request<{ api_keys: any[]; count: number }>("/api-keys");
  }
  createApiKey(data: { name: string; scopes: string[] }) {
    return this.request<{ id: string; name: string; key: string; key_prefix: string; scopes: string[]; created_at: string }>("/api-keys", { method: "POST", body: JSON.stringify(data) });
  }
  revokeApiKey(id: string) {
    return this.request<void>(`/api-keys/${id}`, { method: "DELETE" });
  }

  // Audio URL helper
  audioUrl(filename: string) {
    return `${this.baseUrl}/audio/${filename}`;
  }
}

export const api = new ApiClient();
