# API Reference

Full Swagger UI and ReDoc are available from your running instance:

- **Swagger UI**: [http://localhost:8100/docs](http://localhost:8100/docs)
- **ReDoc**: [http://localhost:8100/redoc](http://localhost:8100/redoc)

---

## Base URL and Authentication

**Base URL:** `http://localhost:8100/api/v1`

**Authentication:** Bearer token via the `Authorization` header. When `AUTH_DISABLED=true` (default), no token is required.

```bash
curl -H "Authorization: Bearer avx_your_key_here" \
     http://localhost:8100/api/v1/profiles
```

---

## Endpoint Examples

### Health Check

**`GET /api/v1/health`**

Response:
```json
{
  "status": "healthy",
  "checks": { "database": "ok", "redis": "ok", "storage": "ok" },
  "version": "0.1.0"
}
```

### List Profiles

**`GET /api/v1/profiles`**

Response:
```json
{
  "profiles": [{ "id": "abc-123", "name": "My Voice", "status": "ready", ... }],
  "count": 5
}
```

### Create Profile

**`POST /api/v1/profiles`**

Request body:
```json
{
  "name": "My Voice",
  "provider_name": "kokoro",
  "language": "en"
}
```

Response:
```json
{
  "id": "abc-123",
  "name": "My Voice",
  "status": "pending",
  "provider_name": "kokoro"
}
```

### Get Profile

**`GET /api/v1/profiles/{id}`**

Response:
```json
{
  "id": "abc-123",
  "name": "My Voice",
  "status": "ready",
  "provider_name": "kokoro",
  "voice_id": "af_heart",
  "language": "en",
  "created_at": "2025-01-15T10:30:00Z"
}
```

### Synthesize

**`POST /api/v1/synthesize`**

Request body:
```json
{
  "text": "Hello world!",
  "profile_id": "abc-123",
  "output_format": "wav"
}
```

Response:
```json
{
  "audio_url": "/api/v1/audio/out_abc123.wav",
  "latency_ms": 89,
  "format": "wav"
}
```

### Stream Synthesis

**`POST /api/v1/synthesize/stream`**

Request body:
```json
{
  "text": "Streaming audio output...",
  "profile_id": "abc-123"
}
```

Response:
```
-- Binary audio stream (chunked transfer encoding)
-- Content-Type: audio/wav
```

### Batch Synthesis

**`POST /api/v1/synthesize/batch`**

Request body:
```json
{
  "items": [
    { "text": "First sentence.", "profile_id": "abc-123" },
    { "text": "Second sentence.", "profile_id": "abc-123" }
  ]
}
```

Response:
```json
{
  "results": [
    { "audio_url": "/api/v1/audio/batch_1.wav", "latency_ms": 85 },
    { "audio_url": "/api/v1/audio/batch_2.wav", "latency_ms": 91 }
  ]
}
```

### Compare Voices

**`POST /api/v1/compare`**

Request body:
```json
{
  "text": "Test phrase",
  "profile_ids": ["id1", "id2", "id3"]
}
```

Response:
```json
{
  "text": "Test phrase",
  "results": [
    { "profile_id": "id1", "audio_url": "...", "latency_ms": 80 },
    { "profile_id": "id2", "audio_url": "...", "latency_ms": 120 }
  ]
}
```

### List Providers

**`GET /api/v1/providers`**

Response:
```json
{
  "providers": [
    { "name": "kokoro", "status": "healthy", "capabilities": { ... } }
  ],
  "count": 9
}
```

### List Voices

**`GET /api/v1/voices?provider=kokoro`**

Response:
```json
{
  "voices": [{ "id": "af_heart", "name": "Heart", "language": "en", ... }],
  "count": 54
}
```

### List Presets

**`GET /api/v1/presets`**

Response:
```json
{
  "presets": [
    { "name": "Friendly", "speed": 1.0, "pitch": 2, "volume": 1.0 },
    { "name": "Professional", "speed": 0.95, "pitch": 0, "volume": 1.0 }
  ]
}
```

### Create API Key

**`POST /api/v1/api-keys`**

Request body:
```json
{
  "name": "CI Pipeline",
  "scopes": ["read", "synthesize"]
}
```

Response:
```json
{
  "id": "key-456",
  "name": "CI Pipeline",
  "key": "avx_abc123...",
  "scopes": ["read", "synthesize"],
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

## OpenAI-Compatible Endpoint

Atlas Vox exposes an OpenAI-compatible TTS endpoint at `/v1/audio/speech`. Point any OpenAI TTS client to your Atlas Vox server.

```bash
curl http://localhost:8100/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kokoro",
    "input": "Hello from Atlas Vox!",
    "voice": "af_heart",
    "response_format": "wav"
  }' \
  --output speech.wav
```

The `model` field maps to a provider name. The `voice` field maps to a voice ID. Supported response_format values: wav, mp3, opus, flac.

---

## Webhooks

Register webhook URLs to receive notifications for training job events and synthesis completions.

```json
POST /api/v1/webhooks
{
  "url": "https://your-server.com/hook",
  "events": ["training.completed", "training.failed", "synthesis.completed"],
  "secret": "your_webhook_secret"
}
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `POST /api/v1/synthesize` | 10 req/min |
| `POST /api/v1/synthesize/stream` | 10 req/min |
| `POST /api/v1/synthesize/batch` | 5 req/min |
| `POST /api/v1/compare` | 5 req/min |
| `POST /api/v1/training` | 5 req/min |
| `POST /v1/audio/speech (OpenAI)` | 20 req/min |
| `GET /api/v1/* (reads)` | 60 req/min |
| `POST /api/v1/* (writes)` | 30 req/min |
