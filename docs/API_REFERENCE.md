# 📡 Atlas Vox API Reference

> Complete REST API reference for Atlas Vox v0.1.0. Base URL: `/api/v1`

---

## Table of Contents

- [Authentication](#-authentication)
- [Error Handling](#-error-handling)
- [Health](#health)
- [Profiles](#profiles)
- [Providers](#providers)
- [Voices](#voices)
- [Samples](#samples)
- [Training](#training)
- [Synthesis](#synthesis)
- [Comparison](#comparison)
- [Presets](#presets)
- [API Keys](#api-keys)
- [Webhooks](#webhooks)
- [Audio](#audio)
- [WebSocket Endpoints](#websocket-endpoints)
- [MCP Server](#mcp-server)

---

## 🔐 Authentication

Atlas Vox supports two authentication modes:

### Disabled Mode (Default)

When `AUTH_DISABLED=true`, all endpoints accept unauthenticated requests. This is the default for homelab and development use.

### API Key Mode

When `AUTH_DISABLED=false`, pass an API key via the `Authorization` header:

```
Authorization: Bearer avx_your_api_key_here
```

**Scopes:**
| Scope | Access |
|-------|--------|
| `read` | GET endpoints (list, view) |
| `write` | POST/PUT/DELETE for profiles, presets, webhooks |
| `synthesize` | Synthesis and comparison endpoints |
| `train` | Training job management |
| `admin` | Everything, including API key management |

---

## ⚠️ Error Handling

All errors return JSON with a `detail` field:

```json
{
  "detail": "Profile not found"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `202` | Accepted (async task queued) |
| `204` | No Content (successful delete) |
| `400` | Bad Request (validation error) |
| `401` | Unauthorized (missing/invalid auth) |
| `403` | Forbidden (insufficient scope) |
| `404` | Not Found |
| `413` | Payload Too Large (file upload) |
| `422` | Validation Error (Pydantic) |
| `500` | Internal Server Error |

### Validation Errors (422)

Pydantic validation errors return detailed field-level information:

```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "String should have at least 1 character",
      "type": "string_too_short"
    }
  ]
}
```

---

## Health

### GET /api/v1/health

System health check. Always returns 200 if the server is running.

**Response:**
```json
{
  "status": "healthy",
  "service": "atlas-vox",
  "version": "0.1.0"
}
```

---

## Profiles

Voice profile CRUD and model versioning.

### GET /api/v1/profiles

List all voice profiles.

**Response:**
```json
{
  "profiles": [
    {
      "id": "a1b2c3d4-...",
      "name": "Sarah - Customer Service",
      "description": "Friendly customer service voice",
      "language": "en",
      "provider_name": "kokoro",
      "status": "ready",
      "tags": ["customer-service", "en"],
      "active_version_id": "v1-...",
      "sample_count": 12,
      "version_count": 2,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z"
    }
  ],
  "count": 1
}
```

### POST /api/v1/profiles

Create a new voice profile.

**Request Body:**
```json
{
  "name": "Sarah - Customer Service",
  "description": "Friendly customer service voice",
  "language": "en",
  "provider_name": "kokoro",
  "tags": ["customer-service", "en"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Profile name (1-200 chars) |
| `description` | string | No | Optional description |
| `language` | string | No | Language code (default: `en`) |
| `provider_name` | string | Yes | TTS provider name |
| `tags` | string[] | No | Optional tags |

**Response:** `201 Created` — Returns the created `ProfileResponse`.

### GET /api/v1/profiles/{profile_id}

Get a specific profile by ID.

**Response:** `200 OK` — Returns `ProfileResponse`.

**Error:** `404 Not Found` — Profile does not exist.

### PUT /api/v1/profiles/{profile_id}

Update a voice profile.

**Request Body:**
```json
{
  "name": "Updated Name",
  "description": "New description",
  "tags": ["updated"]
}
```

All fields are optional. Only provided fields are updated.

**Response:** `200 OK` — Returns updated `ProfileResponse`.

### DELETE /api/v1/profiles/{profile_id}

Delete a voice profile and all associated data.

**Response:** `204 No Content`

### GET /api/v1/profiles/{profile_id}/versions

List all model versions for a profile.

**Response:**
```json
{
  "versions": [
    {
      "id": "v1-...",
      "profile_id": "a1b2c3d4-...",
      "version_number": 1,
      "provider_model_id": "model-xyz",
      "model_path": "/storage/models/...",
      "config_json": "{...}",
      "metrics_json": "{\"loss\": 0.05}",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

### POST /api/v1/profiles/{profile_id}/activate-version/{version_id}

Set a specific model version as the active version for synthesis.

**Response:** `200 OK` — Returns updated `ProfileResponse`.

---

## Providers

TTS provider management, health checks, and configuration.

### GET /api/v1/providers

List all 9 known TTS providers with capabilities.

**Response:**
```json
{
  "providers": [
    {
      "id": "kokoro",
      "name": "kokoro",
      "display_name": "Kokoro",
      "provider_type": "local",
      "enabled": true,
      "gpu_mode": "none",
      "capabilities": {
        "supports_cloning": false,
        "supports_fine_tuning": false,
        "supports_streaming": false,
        "supports_ssml": false,
        "supports_zero_shot": false,
        "supports_batch": false,
        "requires_gpu": false,
        "gpu_mode": "none",
        "min_samples_for_cloning": 0,
        "max_text_length": 5000,
        "supported_languages": ["en"],
        "supported_output_formats": ["wav"]
      },
      "health": null
    }
  ],
  "count": 9
}
```

### GET /api/v1/providers/{name}

Get details for a specific provider.

**Response:** `200 OK` — Returns `ProviderResponse`.

### POST /api/v1/providers/{name}/health

Run a health check on a provider.

**Response:**
```json
{
  "name": "kokoro",
  "healthy": true,
  "latency_ms": 45,
  "error": null
}
```

### GET /api/v1/providers/{name}/voices

List available voices for a specific provider.

**Response:**
```json
{
  "provider": "kokoro",
  "voices": [
    { "voice_id": "af_heart", "name": "Heart (American Female)", "language": "en" },
    { "voice_id": "am_michael", "name": "Michael (American Male)", "language": "en" }
  ],
  "count": 54
}
```

### GET /api/v1/providers/{name}/config

Get provider configuration including schema for UI rendering.

**Response:**
```json
{
  "enabled": true,
  "gpu_mode": "host_cpu",
  "config": {
    "api_key": "****aBcD",
    "model_id": "eleven_multilingual_v2"
  },
  "config_schema": [
    {
      "name": "api_key",
      "field_type": "password",
      "label": "API Key",
      "required": true,
      "is_secret": true
    },
    {
      "name": "model_id",
      "field_type": "select",
      "label": "Model",
      "required": false,
      "is_secret": false,
      "options": ["eleven_monolingual_v1", "eleven_multilingual_v2"],
      "default": "eleven_multilingual_v2"
    }
  ]
}
```

Secret fields are masked with `****` in the response.

### PUT /api/v1/providers/{name}/config

Update provider configuration.

**Request Body:**
```json
{
  "enabled": true,
  "gpu_mode": "docker_gpu",
  "config": {
    "api_key": "new-api-key-value"
  }
}
```

All fields are optional. When a secret field is sent back with the masked value (`****...`), the existing value is preserved.

### POST /api/v1/providers/{name}/test

Run a quick test synthesis.

**Request Body:**
```json
{
  "text": "Hello, this is a test.",
  "voice_id": "af_heart"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | No | Test text (default from provider) |
| `voice_id` | string | No | Voice to use (default: first available) |

**Response:**
```json
{
  "success": true,
  "audio_url": "/storage/output/test_abc123.wav",
  "duration_seconds": 1.5,
  "latency_ms": 234
}
```

---

## Voices

Aggregated voice library across all providers (290+ voices when all providers are active).

### GET /api/v1/voices

List all voices from all available providers, including GPU providers when the GPU service is running.

**Response:**
```json
{
  "voices": [
    {
      "voice_id": "af_heart",
      "name": "Heart",
      "language": "en",
      "gender": null,
      "provider": "kokoro",
      "provider_display": "Kokoro"
    },
    {
      "voice_id": "en-US-JennyNeural",
      "name": "Jenny",
      "language": "en-US",
      "gender": null,
      "provider": "azure_speech",
      "provider_display": "Azure Speech"
    }
  ],
  "count": 290
}
```

### POST /api/v1/voices/preview

Synthesize a short preview for a voice. Results are cached — subsequent requests for the same voice return the cached audio instantly.

**Request Body:**
```json
{
  "provider": "kokoro",
  "voice_id": "af_heart",
  "text": "Hello, this is a preview of my voice."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider` | string | Yes | Provider name |
| `voice_id` | string | Yes | Voice ID from the provider |
| `text` | string | No | Custom preview text (default: "Hello, this is a preview of my voice.") |

**Response:**
```json
{
  "audio_url": "/api/v1/audio/previews/kokoro_af_heart_a1b2c3d4.wav"
}
```

### GET /api/v1/audio/previews/{filename}

Serve a cached voice preview audio file.

**Response:** Audio file with `audio/wav` MIME type.

---

## Samples

Audio sample management for voice profiles.

### POST /api/v1/profiles/{profile_id}/samples

Upload audio samples for a profile.

**Content-Type:** `multipart/form-data`

**Form Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `files` | File[] | One or more audio files |

**Constraints:**
- Maximum 20 files per upload
- Maximum 50 MB per file
- Formats: wav, mp3, flac, ogg, m4a

**Example:**
```bash
curl -X POST http://localhost:8100/api/v1/profiles/abc123/samples \
  -F "files=@sample1.wav" \
  -F "files=@sample2.wav"
```

**Response:** `201 Created`
```json
[
  {
    "id": "s1-...",
    "profile_id": "abc123",
    "filename": "a1b2c3d4e5f6.wav",
    "original_filename": "sample1.wav",
    "format": "wav",
    "file_size_bytes": 1024000,
    "duration_seconds": null,
    "preprocessed": false,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### GET /api/v1/profiles/{profile_id}/samples

List all audio samples for a profile.

**Response:**
```json
{
  "samples": [...],
  "count": 5
}
```

### DELETE /api/v1/profiles/{profile_id}/samples/{sample_id}

Delete a sample and its file from disk.

**Response:** `204 No Content`

### GET /api/v1/profiles/{profile_id}/samples/{sample_id}/analysis

Get audio analysis for a sample (runs on demand, caches in DB).

**Response:**
```json
{
  "sample_id": "s1-...",
  "duration_seconds": 5.2,
  "sample_rate": 44100,
  "pitch_mean": 185.3,
  "pitch_std": 24.1,
  "energy_mean": 0.045,
  "energy_std": 0.012
}
```

### POST /api/v1/profiles/{profile_id}/samples/preprocess

Trigger async preprocessing of all unprocessed samples.

**Response:** `202 Accepted`
```json
{
  "message": "Preprocessing queued for 5 samples",
  "task_id": "celery-task-id-..."
}
```

---

## Training

Training job management with real-time progress.

### POST /api/v1/profiles/{profile_id}/train

Start a training job for a voice profile.

**Request Body:**
```json
{
  "provider_name": "coqui_xtts",
  "config": {
    "epochs": 10,
    "learning_rate": 1e-5
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider_name` | string | No | Override profile's provider |
| `config` | object | No | Provider-specific training config |

**Response:** `201 Created`
```json
{
  "id": "job-...",
  "profile_id": "abc123",
  "provider_name": "coqui_xtts",
  "status": "queued",
  "progress": 0.0,
  "error_message": null,
  "result_version_id": null,
  "started_at": null,
  "completed_at": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### GET /api/v1/training/jobs

List training jobs with optional filters.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `profile_id` | string | Filter by profile |
| `status` | string | Filter by status: `queued`, `preprocessing`, `training`, `completed`, `failed`, `cancelled` |

**Response:**
```json
{
  "jobs": [...],
  "count": 5
}
```

### GET /api/v1/training/jobs/{job_id}

Get detailed job status including Celery task progress.

**Response:**
```json
{
  "id": "job-...",
  "profile_id": "abc123",
  "provider_name": "coqui_xtts",
  "status": "training",
  "progress": 0.45,
  "celery_state": "PROGRESS",
  "celery_percent": 45,
  "error_message": null
}
```

### POST /api/v1/training/jobs/{job_id}/cancel

Cancel a running or queued training job.

**Response:** `200 OK` — Returns the updated `TrainingJobResponse` with status `cancelled`.

---

## Synthesis

Text-to-speech synthesis endpoints.

### POST /api/v1/synthesize

Synthesize text to speech.

**Request Body:**
```json
{
  "text": "Hello, welcome to Atlas Vox!",
  "profile_id": "abc123",
  "preset_id": "preset-456",
  "speed": 1.0,
  "pitch": 0.0,
  "volume": 1.0,
  "output_format": "wav",
  "ssml": false
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | Yes | — | Text to synthesize (1-10,000 chars) |
| `profile_id` | string | Yes | — | Voice profile ID |
| `preset_id` | string | No | `null` | Persona preset ID |
| `speed` | float | No | `1.0` | Speed (0.5-2.0) |
| `pitch` | float | No | `0.0` | Pitch shift (-50 to +50 semitones) |
| `volume` | float | No | `1.0` | Volume (0.0-2.0) |
| `output_format` | string | No | `wav` | Output format: `wav`, `mp3`, `ogg` |
| `ssml` | bool | No | `false` | Treat text as SSML (Azure only) |

**Response:**
```json
{
  "id": "synth-...",
  "audio_url": "/api/v1/audio/output_abc123.wav",
  "duration_seconds": 2.3,
  "latency_ms": 156,
  "profile_id": "abc123",
  "provider_name": "kokoro"
}
```

### POST /api/v1/synthesize/stream

Streaming synthesis — returns chunked transfer encoding.

Same request body as `/synthesize`.

**Response:** Streaming `audio/wav` with `Transfer-Encoding: chunked`.

Only works with streaming-capable providers: ElevenLabs, Azure, Coqui XTTS, CosyVoice, Dia2.

### POST /api/v1/synthesize/batch

Batch synthesize multiple lines.

**Request Body:**
```json
{
  "lines": [
    "First sentence.",
    "Second sentence.",
    "Third sentence."
  ],
  "profile_id": "abc123",
  "preset_id": "preset-456",
  "speed": 1.0,
  "output_format": "wav"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lines` | string[] | Yes | Lines to synthesize (max 100) |
| `profile_id` | string | Yes | Voice profile ID |
| `preset_id` | string | No | Persona preset ID |
| `speed` | float | No | Speed (default: 1.0) |
| `output_format` | string | No | Output format (default: wav) |

**Response:**
```json
[
  { "line": "First sentence.", "audio_url": "/api/v1/audio/out1.wav", "latency_ms": 120 },
  { "line": "Second sentence.", "audio_url": "/api/v1/audio/out2.wav", "latency_ms": 98 }
]
```

### GET /api/v1/synthesis/history

Get synthesis history.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | `50` | Max results to return |
| `profile_id` | string | — | Filter by profile |

**Response:**
```json
[
  {
    "id": "synth-...",
    "profile_id": "abc123",
    "provider_name": "kokoro",
    "text": "Hello, welcome!",
    "audio_url": "/api/v1/audio/output_abc123.wav",
    "output_format": "wav",
    "duration_seconds": 1.5,
    "latency_ms": 89,
    "created_at": "2024-01-01T12:00:00Z"
  }
]
```

---

## Comparison

Side-by-side voice synthesis comparison.

### POST /api/v1/compare

Compare the same text across multiple voice profiles.

**Request Body:**
```json
{
  "text": "The quick brown fox jumps over the lazy dog.",
  "profile_ids": ["profile-1", "profile-2", "profile-3"],
  "speed": 1.0,
  "pitch": 0.0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Text to compare (1-5,000 chars) |
| `profile_ids` | string[] | Yes | At least 2 profile IDs |
| `speed` | float | No | Speed (default: 1.0) |
| `pitch` | float | No | Pitch (default: 0.0) |

**Response:**
```json
{
  "text": "The quick brown fox jumps over the lazy dog.",
  "results": [
    {
      "profile_id": "profile-1",
      "profile_name": "Sarah",
      "provider_name": "kokoro",
      "audio_url": "/api/v1/audio/cmp_1.wav",
      "duration_seconds": 2.1,
      "latency_ms": 89
    },
    {
      "profile_id": "profile-2",
      "profile_name": "James",
      "provider_name": "elevenlabs",
      "audio_url": "/api/v1/audio/cmp_2.wav",
      "duration_seconds": 2.3,
      "latency_ms": 456
    }
  ]
}
```

---

## Presets

Persona preset management. System presets are auto-seeded on first list.

### GET /api/v1/presets

List all persona presets.

**Response:**
```json
{
  "presets": [
    {
      "id": "preset-...",
      "name": "Friendly",
      "description": "Warm and approachable",
      "speed": 1.0,
      "pitch": 2.0,
      "volume": 1.0,
      "is_system": true
    },
    {
      "id": "preset-...",
      "name": "Professional",
      "description": "Clear and authoritative",
      "speed": 0.95,
      "pitch": 0.0,
      "volume": 1.0,
      "is_system": true
    }
  ],
  "count": 6
}
```

### POST /api/v1/presets

Create a custom persona preset.

**Request Body:**
```json
{
  "name": "Narrator",
  "description": "Deep narrator voice",
  "speed": 0.9,
  "pitch": -8.0,
  "volume": 1.1
}
```

**Response:** `201 Created` — Returns `PresetResponse`.

### PUT /api/v1/presets/{preset_id}

Update a custom preset. System presets cannot be modified (returns `403`).

### DELETE /api/v1/presets/{preset_id}

Delete a custom preset. System presets cannot be deleted (returns `403`).

---

## API Keys

API key management for programmatic access.

### POST /api/v1/api-keys

Create a new API key.

**Request Body:**
```json
{
  "name": "Production App",
  "scopes": ["read", "synthesize"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Descriptive name |
| `scopes` | string[] | Yes | Permissions: `read`, `write`, `synthesize`, `train`, `admin` |

**Response:** `201 Created`
```json
{
  "id": "key-...",
  "name": "Production App",
  "key": "avx_Tz2Kx8wY4mPqR7vN3jL6...",
  "key_prefix": "avx_Tz2Kx8wY",
  "scopes": ["read", "synthesize"],
  "created_at": "2024-01-01T00:00:00Z"
}
```

> ⚠️ The full `key` value is returned only in this response. Store it securely.

### GET /api/v1/api-keys

List all API keys (only prefix shown, not full key).

**Response:**
```json
{
  "api_keys": [
    {
      "id": "key-...",
      "name": "Production App",
      "key_prefix": "avx_Tz2Kx8wY",
      "scopes": "read,synthesize",
      "active": true,
      "created_at": "2024-01-01T00:00:00Z",
      "last_used_at": null
    }
  ],
  "count": 1
}
```

### DELETE /api/v1/api-keys/{key_id}

Revoke (deactivate) an API key. The key immediately stops working.

**Response:** `204 No Content`

---

## Webhooks

Webhook subscriptions for event-driven integrations.

### Supported Events

| Event | Trigger |
|-------|---------|
| `training.completed` | Training job finishes successfully |
| `training.failed` | Training job fails |
| `*` | All events |

### GET /api/v1/webhooks

List all webhook subscriptions.

### POST /api/v1/webhooks

Create a webhook subscription.

**Request Body:**
```json
{
  "url": "https://your-server.com/webhooks/atlas-vox",
  "events": ["training.completed", "training.failed"],
  "secret": "your-hmac-secret"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | Webhook delivery URL |
| `events` | string[] | Yes | Events to subscribe to |
| `secret` | string | No | HMAC-SHA256 signing secret |

**Webhook Payload:**
```json
{
  "event": "training.completed",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "job_id": "job-...",
    "profile_id": "abc123",
    "version_id": "v1-..."
  }
}
```

**Signature Header:**
```
X-Atlas-Signature: sha256=<hmac-hex-digest>
```

### PUT /api/v1/webhooks/{webhook_id}

Update a webhook subscription.

### DELETE /api/v1/webhooks/{webhook_id}

Delete a webhook subscription.

### POST /api/v1/webhooks/{webhook_id}/test

Send a test payload to a webhook.

**Response:**
```json
{
  "deliveries": [
    { "url": "https://...", "status": 200, "success": true }
  ]
}
```

---

## Audio

Audio file serving.

### GET /api/v1/audio/{filename}

Serve a generated audio file from the output storage directory.

**Response:** Audio file with appropriate MIME type:
| Extension | MIME Type |
|-----------|-----------|
| `.wav` | `audio/wav` |
| `.mp3` | `audio/mpeg` |
| `.ogg` | `audio/ogg` |
| `.flac` | `audio/flac` |

---

## WebSocket Endpoints

### Training Progress

```
WS /api/v1/training/jobs/{job_id}/progress
```

**Authentication:** Pass API key as query parameter:
```
ws://localhost:8100/api/v1/training/jobs/JOB_ID/progress?token=avx_your_key
```

Authentication is skipped when `AUTH_DISABLED=true`.

**Frames sent by server:**
```json
{
  "job_id": "job-...",
  "state": "PROGRESS",
  "percent": 45,
  "status": "training"
}
```

**Terminal frame (on completion):**
```json
{
  "job_id": "job-...",
  "state": "DONE",
  "percent": 100,
  "status": "completed",
  "version_id": "v1-...",
  "error": null
}
```

**Connection lifecycle:**
1. Client connects to WebSocket URL
2. Server polls Celery task state every 1 second
3. Server sends JSON frames when state changes
4. Server sends final frame and closes on terminal state (`SUCCESS`, `FAILURE`, `REVOKED`)

---

## MCP Server

Atlas Vox includes an MCP (Model Context Protocol) server accessible via JSONRPC 2.0 over SSE transport.

**Endpoint:** `/mcp/sse`

The MCP server exposes TTS capabilities as tools for AI agent integration. See [MCP documentation](../docs/MCP.md) for the full specification.

---

## Interactive API Documentation

Atlas Vox serves auto-generated interactive docs:

| URL | Format |
|-----|--------|
| `/docs` | Swagger UI (interactive) |
| `/redoc` | ReDoc (reference) |
| `/openapi.json` | OpenAPI 3.x schema |

---

<div align="center">

[Back to User Guide](USER_GUIDE.md) | [Deployment Guide](DEPLOYMENT.md) | [Architecture](ARCHITECTURE.md)

</div>
