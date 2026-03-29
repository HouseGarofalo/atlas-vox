# Atlas Vox API Reference

> **Version:** 0.1.0 | **Base URL:** `http://localhost:8100/api/v1` | **Transport:** HTTP/1.1 + WebSocket

---

## Table of Contents

- [Overview](#overview)
  - [Base URL](#base-url)
  - [Authentication](#authentication)
  - [Error Format](#error-format)
  - [Pagination & Filtering](#pagination--filtering)
- [Health](#health)
  - [GET /health -- System Health Check](#get-health)
- [Profiles](#profiles)
  - [GET /profiles -- List Profiles](#get-profiles)
  - [POST /profiles -- Create Profile](#post-profiles)
  - [GET /profiles/:id -- Get Profile](#get-profilesid)
  - [PUT /profiles/:id -- Update Profile](#put-profilesid)
  - [DELETE /profiles/:id -- Delete Profile](#delete-profilesid)
  - [GET /profiles/:id/versions -- List Model Versions](#get-profilesidversions)
  - [POST /profiles/:id/activate-version/:vid -- Activate Version](#post-profilesidactivate-versionvid)
- [Samples](#samples)
  - [POST /profiles/:id/samples -- Upload Samples](#post-profilesidsamples)
  - [GET /profiles/:id/samples -- List Samples](#get-profilesidsamples)
  - [DELETE /profiles/:id/samples/:sid -- Delete Sample](#delete-profilesidsamplessid)
  - [GET /profiles/:id/samples/:sid/analysis -- Sample Analysis](#get-profilesidsamplessidanalysis)
  - [POST /profiles/:id/samples/preprocess -- Trigger Preprocessing](#post-profilesidsamplespreprocess)
- [Training](#training)
  - [POST /profiles/:id/train -- Start Training](#post-profilesidtrain)
  - [GET /training/jobs -- List Training Jobs](#get-trainingjobs)
  - [GET /training/jobs/:id -- Get Job Status](#get-trainingjobsid)
  - [POST /training/jobs/:id/cancel -- Cancel Job](#post-trainingjobsidcancel)
  - [WS /training/jobs/:id/progress -- Training Progress WebSocket](#ws-trainingjobsidprogress)
- [Synthesis](#synthesis)
  - [POST /synthesize -- Synthesize Text](#post-synthesize)
  - [POST /synthesize/stream -- Stream Synthesis](#post-synthesizestream)
  - [POST /synthesize/batch -- Batch Synthesis](#post-synthesizebatch)
  - [GET /synthesis/history -- Synthesis History](#get-synthesishistory)
- [Comparison](#comparison)
  - [POST /compare -- Compare Voices](#post-compare)
- [Providers](#providers)
  - [GET /providers -- List Providers](#get-providers)
  - [GET /providers/:name -- Get Provider](#get-providersname)
  - [POST /providers/:name/health -- Provider Health Check](#post-providersnamehealth)
  - [GET /providers/:name/voices -- List Provider Voices](#get-providersnamevoices)
- [Presets](#presets)
  - [GET /presets -- List Presets](#get-presets)
  - [POST /presets -- Create Preset](#post-presets)
  - [PUT /presets/:id -- Update Preset](#put-presetsid)
  - [DELETE /presets/:id -- Delete Preset](#delete-presetsid)
- [API Keys](#api-keys)
  - [POST /api-keys -- Create API Key](#post-api-keys)
  - [GET /api-keys -- List API Keys](#get-api-keys)
  - [DELETE /api-keys/:id -- Revoke API Key](#delete-api-keysid)
- [Webhooks](#webhooks)
  - [GET /webhooks -- List Webhooks](#get-webhooks)
  - [POST /webhooks -- Create Webhook](#post-webhooks)
  - [PUT /webhooks/:id -- Update Webhook](#put-webhooksid)
  - [DELETE /webhooks/:id -- Delete Webhook](#delete-webhooksid)
  - [POST /webhooks/:id/test -- Test Webhook](#post-webhooksidtest)
- [Audio](#audio)
  - [GET /audio/:filename -- Serve Audio File](#get-audiofilename)
- [curl Examples](#curl-examples)

---

## Overview

### Base URL

All endpoints are prefixed with `/api/v1`. In local development the full base URL is:

```
http://localhost:8100/api/v1
```

For production deployments, replace with your domain:

```
https://your-domain.com/api/v1
```

### Authentication

Atlas Vox supports two authentication modes. The active mode is controlled by the `AUTH_DISABLED` environment variable.

#### Single-User Mode (default)

When `AUTH_DISABLED=true` (the default), all requests are automatically authenticated as a local admin user. No `Authorization` header is required.

#### Multi-User Mode

When `AUTH_DISABLED=false`, every request must include an `Authorization` header:

| Method | Header Format | Description |
|--------|--------------|-------------|
| **JWT Bearer Token** | `Authorization: Bearer <jwt_token>` | Obtained via login. Expires after 1440 minutes (24 hours) by default. |
| **API Key** | `Authorization: Bearer <avx_...>` | Created via the `/api-keys` endpoint. Scoped permissions. |

**API Key Format:** Keys are prefixed with `avx_` followed by 48 URL-safe random characters (e.g., `avx_AbCdEf123456...`). The full key is shown **only once** at creation time.

**Scopes:** API keys can be scoped to specific permissions:

| Scope | Description |
|-------|-------------|
| `read` | Read-only access to profiles, samples, presets, providers |
| `write` | Create, update, and delete profiles, samples, presets |
| `synthesize` | Access to synthesis and comparison endpoints |
| `train` | Start, cancel, and monitor training jobs |
| `admin` | Full administrative access including API key and webhook management |

#### WebSocket Authentication

WebSocket endpoints use query-parameter authentication:

```
ws://localhost:8100/api/v1/training/jobs/{job_id}/progress?token=<api_key>
```

When `AUTH_DISABLED=true`, the `token` parameter is not required.

### Error Format

All error responses follow a consistent JSON structure:

```json
{
  "detail": "Human-readable error message"
}
```

**Standard HTTP Status Codes:**

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Resource created |
| `202` | Accepted (async processing started) |
| `204` | No content (successful deletion) |
| `400` | Bad request -- validation error or invalid parameters |
| `401` | Unauthorized -- missing or invalid credentials |
| `403` | Forbidden -- insufficient permissions |
| `404` | Not found -- resource does not exist |
| `413` | Payload too large -- file exceeds size limit |
| `422` | Unprocessable entity -- Pydantic validation failure |
| `500` | Internal server error |

### Pagination & Filtering

List endpoints return all results with a `count` field. Some endpoints support query-parameter filtering (documented per endpoint). Cursor-based pagination is planned for a future release.

---

## Health

<a id="get-health"></a>

### `GET` /health

System health check. Returns service status, name, and version. Does **not** require authentication.

**Response `200 OK`**

```json
{
  "status": "healthy",
  "service": "atlas-vox",
  "version": "0.1.0"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | Always `"healthy"` when the service is up |
| `service` | `string` | Service name |
| `version` | `string` | Current API version |

---

## Profiles

Voice profiles are the central resource in Atlas Vox. Each profile represents a voice identity tied to a specific TTS provider, with associated audio samples, trained model versions, and synthesis settings.

<a id="get-profiles"></a>

### `GET` /profiles

List all voice profiles.

**Response `200 OK`**

```json
{
  "profiles": [
    {
      "id": "prof_a1b2c3d4",
      "name": "Corporate Narrator",
      "description": "Professional male voice for training videos",
      "language": "en",
      "provider_name": "kokoro",
      "status": "ready",
      "tags": ["corporate", "male"],
      "active_version_id": "ver_x1y2z3",
      "sample_count": 12,
      "version_count": 2,
      "created_at": "2026-03-20T14:30:00Z",
      "updated_at": "2026-03-22T09:15:00Z"
    }
  ],
  "count": 1
}
```

| Field | Type | Description |
|-------|------|-------------|
| `profiles` | `ProfileResponse[]` | Array of profile objects |
| `count` | `integer` | Total number of profiles |

**ProfileResponse Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Unique profile identifier |
| `name` | `string` | Display name |
| `description` | `string \| null` | Optional description |
| `language` | `string` | Language code (e.g., `"en"`) |
| `provider_name` | `string` | TTS provider key (e.g., `"kokoro"`, `"elevenlabs"`) |
| `status` | `string` | Profile status: `"created"`, `"training"`, `"ready"`, `"error"` |
| `tags` | `string[] \| null` | Optional tags for organization |
| `active_version_id` | `string \| null` | Currently active model version ID |
| `sample_count` | `integer` | Number of uploaded audio samples |
| `version_count` | `integer` | Number of trained model versions |
| `created_at` | `datetime` | ISO 8601 creation timestamp |
| `updated_at` | `datetime` | ISO 8601 last update timestamp |

---

<a id="post-profiles"></a>

### `POST` /profiles

Create a new voice profile.

**Request Body**

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `name` | `string` | Yes | -- | 1-200 characters | Display name for the profile |
| `description` | `string` | No | `null` | -- | Optional description |
| `language` | `string` | No | `"en"` | -- | Language code |
| `provider_name` | `string` | Yes | -- | Must be a valid provider name | TTS provider to use |
| `tags` | `string[]` | No | `null` | -- | Optional tags for organization |

```json
{
  "name": "Corporate Narrator",
  "description": "Professional male voice for training videos",
  "language": "en",
  "provider_name": "kokoro",
  "tags": ["corporate", "male"]
}
```

**Response `201 Created`**

Returns a full `ProfileResponse` object (see [ProfileResponse Fields](#get-profiles) above).

**Error Responses**

| Status | Condition |
|--------|-----------|
| `422` | Validation error (e.g., empty name, name too long) |

---

<a id="get-profilesid"></a>

### `GET` /profiles/{profile_id}

Get a specific voice profile by ID.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `profile_id` | `string` | Profile UUID |

**Response `200 OK`**

Returns a full `ProfileResponse` object.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | Profile not found |

---

<a id="put-profilesid"></a>

### `PUT` /profiles/{profile_id}

Update an existing voice profile. All fields are optional -- only provided fields are updated.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `profile_id` | `string` | Profile UUID |

**Request Body**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `name` | `string` | No | 1-200 characters | Display name |
| `description` | `string` | No | -- | Description |
| `language` | `string` | No | -- | Language code |
| `tags` | `string[]` | No | -- | Tags |
| `status` | `string` | No | -- | Profile status |

```json
{
  "name": "Updated Narrator",
  "tags": ["corporate", "male", "v2"]
}
```

**Response `200 OK`**

Returns the updated `ProfileResponse` object.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | Profile not found |
| `422` | Validation error |

---

<a id="delete-profilesid"></a>

### `DELETE` /profiles/{profile_id}

Delete a voice profile and all associated data.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `profile_id` | `string` | Profile UUID |

**Response `204 No Content`**

Empty response body on success.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | Profile not found |

---

<a id="get-profilesidversions"></a>

### `GET` /profiles/{profile_id}/versions

List all trained model versions for a profile.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `profile_id` | `string` | Profile UUID |

**Response `200 OK`**

```json
{
  "versions": [
    {
      "id": "ver_x1y2z3",
      "profile_id": "prof_a1b2c3d4",
      "version_number": 2,
      "provider_model_id": "model-abc-123",
      "model_path": "/storage/models/prof_a1b2c3d4/v2",
      "config_json": "{\"epochs\": 100}",
      "metrics_json": "{\"loss\": 0.023}",
      "created_at": "2026-03-22T09:15:00Z"
    }
  ],
  "count": 1
}
```

**ModelVersionResponse Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Version UUID |
| `profile_id` | `string` | Parent profile ID |
| `version_number` | `integer` | Sequential version number |
| `provider_model_id` | `string \| null` | Provider-specific model identifier |
| `model_path` | `string \| null` | Local path to model artifacts |
| `config_json` | `string \| null` | Training configuration as JSON string |
| `metrics_json` | `string \| null` | Training metrics as JSON string |
| `created_at` | `datetime` | ISO 8601 creation timestamp |

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | Profile not found |

---

<a id="post-profilesidactivate-versionvid"></a>

### `POST` /profiles/{profile_id}/activate-version/{version_id}

Set the active model version for a profile. Subsequent synthesis calls will use this version.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `profile_id` | `string` | Profile UUID |
| `version_id` | `string` | Version UUID to activate |

**Response `200 OK`**

Returns the updated `ProfileResponse` with `active_version_id` set to the new version.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `400` | Invalid version ID or version does not belong to profile |

---

## Samples

Audio samples are uploaded to a profile and used for voice cloning and training. Samples are stored on disk and referenced in the database with analysis metadata.

<a id="post-profilesidsamples"></a>

### `POST` /profiles/{profile_id}/samples

Upload one or more audio sample files via `multipart/form-data`.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `profile_id` | `string` | Profile UUID |

**Request Body** (`multipart/form-data`)

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `files` | `File[]` | Yes | Max 20 files, 50 MB each | Audio files to upload |

**Supported Audio Formats:**

| Format | Extension | MIME Type |
|--------|-----------|-----------|
| WAV | `.wav` | `audio/wav` |
| MP3 | `.mp3` | `audio/mpeg` |
| FLAC | `.flac` | `audio/flac` |
| OGG | `.ogg` | `audio/ogg` |
| M4A | `.m4a` | `audio/mp4` |

**Response `201 Created`**

Returns an array of `SampleResponse` objects:

```json
[
  {
    "id": "samp_f1g2h3",
    "profile_id": "prof_a1b2c3d4",
    "filename": "3a8b1cf2e4d1.wav",
    "original_filename": "recording_001.wav",
    "format": "wav",
    "duration_seconds": null,
    "sample_rate": null,
    "file_size_bytes": 1234567,
    "preprocessed": false,
    "created_at": "2026-03-20T15:00:00Z"
  }
]
```

**SampleResponse Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Sample UUID |
| `profile_id` | `string` | Parent profile ID |
| `filename` | `string` | Internal storage filename |
| `original_filename` | `string` | Original upload filename |
| `format` | `string` | Audio format extension |
| `duration_seconds` | `float \| null` | Duration (populated after analysis) |
| `sample_rate` | `integer \| null` | Sample rate in Hz (populated after analysis) |
| `file_size_bytes` | `integer \| null` | File size in bytes |
| `preprocessed` | `boolean` | Whether preprocessing has been applied |
| `created_at` | `datetime` | ISO 8601 creation timestamp |

**Error Responses**

| Status | Condition |
|--------|-----------|
| `400` | Too many files (>20) or unsupported format |
| `404` | Profile not found |
| `413` | File exceeds 50 MB size limit |

---

<a id="get-profilesidsamples"></a>

### `GET` /profiles/{profile_id}/samples

List all audio samples for a profile, ordered by creation date (newest first).

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `profile_id` | `string` | Profile UUID |

**Response `200 OK`**

```json
{
  "samples": [
    {
      "id": "samp_f1g2h3",
      "profile_id": "prof_a1b2c3d4",
      "filename": "3a8b1cf2e4d1.wav",
      "original_filename": "recording_001.wav",
      "format": "wav",
      "duration_seconds": 4.52,
      "sample_rate": 44100,
      "file_size_bytes": 1234567,
      "preprocessed": true,
      "created_at": "2026-03-20T15:00:00Z"
    }
  ],
  "count": 1
}
```

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | Profile not found |

---

<a id="delete-profilesidsamplessid"></a>

### `DELETE` /profiles/{profile_id}/samples/{sample_id}

Delete an audio sample and its associated files from disk (both original and preprocessed).

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `profile_id` | `string` | Profile UUID |
| `sample_id` | `string` | Sample UUID |

**Response `204 No Content`**

Empty response body on success.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | Sample not found |

---

<a id="get-profilesidsamplessidanalysis"></a>

### `GET` /profiles/{profile_id}/samples/{sample_id}/analysis

Return audio analysis metrics for a sample. Analysis is computed on-demand and cached in the database for subsequent requests.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `profile_id` | `string` | Profile UUID |
| `sample_id` | `string` | Sample UUID |

**Response `200 OK`**

```json
{
  "sample_id": "samp_f1g2h3",
  "duration_seconds": 4.52,
  "sample_rate": 44100,
  "pitch_mean": 182.5,
  "pitch_std": 24.3,
  "energy_mean": 0.045,
  "energy_std": 0.012
}
```

**SampleAnalysis Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `sample_id` | `string` | Sample UUID |
| `duration_seconds` | `float` | Audio duration in seconds |
| `sample_rate` | `integer` | Sample rate in Hz |
| `pitch_mean` | `float \| null` | Mean fundamental frequency (F0) in Hz |
| `pitch_std` | `float \| null` | Standard deviation of F0 |
| `energy_mean` | `float \| null` | Mean RMS energy |
| `energy_std` | `float \| null` | Standard deviation of RMS energy |

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | Sample not found |

---

<a id="post-profilesidsamplespreprocess"></a>

### `POST` /profiles/{profile_id}/samples/preprocess

Trigger asynchronous preprocessing of all unprocessed samples for a profile. Preprocessing normalizes audio, removes silence, and prepares samples for training. The work is dispatched to a Celery worker.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `profile_id` | `string` | Profile UUID |

**Response `202 Accepted`**

```json
{
  "message": "Preprocessing queued for 5 samples",
  "task_id": "celery-task-abc123"
}
```

If all samples are already preprocessed:

```json
{
  "message": "All samples already preprocessed",
  "task_id": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `message` | `string` | Status message |
| `task_id` | `string \| null` | Celery task ID for tracking (null if nothing to process) |

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | Profile not found |

---

## Training

Training jobs take a profile's audio samples and fine-tune or clone a voice model using the profile's configured TTS provider. Jobs run asynchronously via Celery workers. Real-time progress is available via WebSocket.

<a id="post-profilesidtrain"></a>

### `POST` /profiles/{profile_id}/train

Start a new training job for a voice profile.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `profile_id` | `string` | Profile UUID |

**Request Body**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `provider_name` | `string` | No | Profile's default provider | Override the TTS provider for this training run |
| `config` | `object` | No | `null` | Provider-specific training configuration (epochs, learning rate, etc.) |

```json
{
  "provider_name": "coqui_xtts",
  "config": {
    "epochs": 100,
    "learning_rate": 0.0001
  }
}
```

**Response `201 Created`**

```json
{
  "id": "job_m1n2o3p4",
  "profile_id": "prof_a1b2c3d4",
  "provider_name": "coqui_xtts",
  "status": "queued",
  "progress": 0.0,
  "error_message": null,
  "result_version_id": null,
  "started_at": null,
  "completed_at": null,
  "created_at": "2026-03-22T10:00:00Z",
  "updated_at": "2026-03-22T10:00:00Z"
}
```

**TrainingJobResponse Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Job UUID |
| `profile_id` | `string` | Parent profile ID |
| `provider_name` | `string` | TTS provider used for training |
| `status` | `string` | Job status: `"queued"`, `"running"`, `"completed"`, `"failed"`, `"cancelled"` |
| `progress` | `float` | Progress percentage (0.0 to 100.0) |
| `error_message` | `string \| null` | Error details if status is `"failed"` |
| `result_version_id` | `string \| null` | Model version ID created on success |
| `started_at` | `datetime \| null` | When the job began processing |
| `completed_at` | `datetime \| null` | When the job finished |
| `created_at` | `datetime` | ISO 8601 creation timestamp |
| `updated_at` | `datetime` | ISO 8601 last update timestamp |

**Error Responses**

| Status | Condition |
|--------|-----------|
| `400` | Invalid profile, no samples, or provider error |

---

<a id="get-trainingjobs"></a>

### `GET` /training/jobs

List all training jobs with optional filtering.

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `profile_id` | `string` | No | Filter by profile ID |
| `status` | `string` | No | Filter by job status (`queued`, `running`, `completed`, `failed`, `cancelled`) |

**Response `200 OK`**

```json
{
  "jobs": [
    {
      "id": "job_m1n2o3p4",
      "profile_id": "prof_a1b2c3d4",
      "provider_name": "coqui_xtts",
      "status": "running",
      "progress": 45.0,
      "error_message": null,
      "result_version_id": null,
      "started_at": "2026-03-22T10:00:30Z",
      "completed_at": null,
      "created_at": "2026-03-22T10:00:00Z",
      "updated_at": "2026-03-22T10:05:00Z"
    }
  ],
  "count": 1
}
```

---

<a id="get-trainingjobsid"></a>

### `GET` /training/jobs/{job_id}

Get detailed status for a specific training job, including live Celery task progress.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | `string` | Job UUID |

**Response `200 OK`**

Returns a dictionary with full job details and real-time Celery state:

```json
{
  "id": "job_m1n2o3p4",
  "profile_id": "prof_a1b2c3d4",
  "provider_name": "coqui_xtts",
  "status": "running",
  "progress": 67.5,
  "celery_state": "PROGRESS",
  "error_message": null,
  "result_version_id": null,
  "started_at": "2026-03-22T10:00:30Z",
  "completed_at": null,
  "created_at": "2026-03-22T10:00:00Z",
  "updated_at": "2026-03-22T10:10:00Z"
}
```

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | Job not found |

---

<a id="post-trainingjobsidcancel"></a>

### `POST` /training/jobs/{job_id}/cancel

Cancel a running or queued training job. Sends a revoke signal to the Celery worker.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | `string` | Job UUID |

**Response `200 OK`**

Returns the updated `TrainingJobResponse` with `status` set to `"cancelled"`.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `400` | Job cannot be cancelled (already completed or failed) |

---

<a id="ws-trainingjobsidprogress"></a>

### `WS` /training/jobs/{job_id}/progress

WebSocket endpoint that streams real-time training progress for a specific job. The server polls Celery task state every second and pushes JSON frames when the state changes.

**Connection URL**

```
ws://localhost:8100/api/v1/training/jobs/{job_id}/progress?token=<api_key>
```

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | `string` | When auth enabled | API key for WebSocket authentication |

**Connection Flow**

1. Client connects with optional `?token=` parameter
2. Server validates authentication (if enabled)
3. Server accepts the WebSocket connection
4. Server sends JSON frames as training state changes
5. Server sends a final frame and closes on terminal state

**Progress Frame**

```json
{
  "job_id": "job_m1n2o3p4",
  "state": "PROGRESS",
  "percent": 45,
  "status": "Training epoch 45/100"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | `string` | Job UUID |
| `state` | `string` | Celery state: `PENDING`, `STARTED`, `PROGRESS`, `SUCCESS`, `FAILURE`, `REVOKED` |
| `percent` | `integer` | Progress percentage (0-100) |
| `status` | `string` | Human-readable status message |

**Final Frame (on completion)**

```json
{
  "job_id": "job_m1n2o3p4",
  "state": "DONE",
  "percent": 100,
  "status": "completed",
  "version_id": "ver_x1y2z3",
  "error": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `version_id` | `string \| null` | Model version created (on success) |
| `error` | `string \| null` | Error message (on failure) |

**Close Codes**

| Code | Reason |
|------|--------|
| `1000` | Normal closure (terminal state reached) |
| `4001` | Authentication required |
| `4003` | Invalid API key |

---

## Synthesis

Synthesis endpoints convert text to speech using a trained voice profile. Three modes are available: standard (returns an audio URL), streaming (chunked transfer), and batch (multiple lines at once).

<a id="post-synthesize"></a>

### `POST` /synthesize

Synthesize text to speech. Returns a URL to the generated audio file.

**Request Body**

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `text` | `string` | Yes | -- | 1-10,000 characters | Text to synthesize (or SSML if `ssml=true`) |
| `profile_id` | `string` | Yes | -- | -- | Voice profile to use |
| `preset_id` | `string` | No | `null` | -- | Persona preset to apply (overrides speed/pitch/volume) |
| `speed` | `float` | No | `1.0` | 0.5 -- 2.0 | Speaking rate multiplier |
| `pitch` | `float` | No | `0.0` | -50.0 -- 50.0 | Pitch shift in semitones |
| `volume` | `float` | No | `1.0` | 0.0 -- 2.0 | Volume multiplier |
| `output_format` | `string` | No | `"wav"` | `wav`, `mp3`, `ogg` | Output audio format |
| `ssml` | `boolean` | No | `false` | -- | Treat `text` field as SSML markup |

```json
{
  "text": "Welcome to Atlas Vox, your intelligent voice platform.",
  "profile_id": "prof_a1b2c3d4",
  "speed": 1.0,
  "pitch": 0.0,
  "volume": 1.0,
  "output_format": "wav",
  "ssml": false
}
```

**Response `200 OK`**

```json
{
  "id": "synth_q1r2s3t4",
  "audio_url": "/api/v1/audio/synth_q1r2s3t4.wav",
  "duration_seconds": 3.2,
  "latency_ms": 450,
  "profile_id": "prof_a1b2c3d4",
  "provider_name": "kokoro"
}
```

**SynthesisResponse Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Synthesis record UUID |
| `audio_url` | `string` | Relative URL to retrieve the audio file |
| `duration_seconds` | `float \| null` | Audio duration in seconds |
| `latency_ms` | `integer` | Time to generate in milliseconds |
| `profile_id` | `string` | Profile used for synthesis |
| `provider_name` | `string` | Provider that performed synthesis |

**Error Responses**

| Status | Condition |
|--------|-----------|
| `400` | Invalid profile, provider error, or unsupported configuration |
| `422` | Text validation failure (empty, too long) |

---

<a id="post-synthesizestream"></a>

### `POST` /synthesize/stream

Stream synthesis with chunked transfer encoding. Ideal for providers that support streaming output (e.g., ElevenLabs, CosyVoice).

**Request Body**

Same as [POST /synthesize](#post-synthesize).

**Response `200 OK`**

Returns a `StreamingResponse` with:

| Header | Value |
|--------|-------|
| `Content-Type` | `audio/wav` |
| `Transfer-Encoding` | `chunked` |

The response body is raw audio data streamed in chunks. Connect with a streaming HTTP client or pipe directly to an audio player.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `400` | Invalid profile or provider does not support streaming |

---

<a id="post-synthesizebatch"></a>

### `POST` /synthesize/batch

Synthesize multiple lines of text in a single request.

**Request Body**

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `lines` | `string[]` | Yes | -- | Max 100 items | Array of text lines to synthesize |
| `profile_id` | `string` | Yes | -- | -- | Voice profile to use |
| `preset_id` | `string` | No | `null` | -- | Persona preset to apply |
| `speed` | `float` | No | `1.0` | -- | Speaking rate multiplier |
| `pitch` | `float` | No | `0.0` | -- | Pitch shift |
| `output_format` | `string` | No | `"wav"` | `wav`, `mp3`, `ogg` | Output audio format |

```json
{
  "lines": [
    "Chapter one: The Beginning.",
    "It was a dark and stormy night.",
    "The end."
  ],
  "profile_id": "prof_a1b2c3d4",
  "speed": 0.95,
  "output_format": "mp3"
}
```

**Response `200 OK`**

Returns an array of result objects, one per line:

```json
[
  {
    "line_index": 0,
    "audio_url": "/api/v1/audio/batch_001.mp3",
    "duration_seconds": 1.8,
    "latency_ms": 320
  },
  {
    "line_index": 1,
    "audio_url": "/api/v1/audio/batch_002.mp3",
    "duration_seconds": 2.1,
    "latency_ms": 380
  },
  {
    "line_index": 2,
    "audio_url": "/api/v1/audio/batch_003.mp3",
    "duration_seconds": 0.9,
    "latency_ms": 210
  }
]
```

**Error Responses**

| Status | Condition |
|--------|-----------|
| `400` | Invalid profile or provider error |

---

<a id="get-synthesishistory"></a>

### `GET` /synthesis/history

Retrieve recent synthesis history.

**Query Parameters**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | `integer` | No | `50` | Maximum number of records to return |
| `profile_id` | `string` | No | `null` | Filter by profile ID |

**Response `200 OK`**

```json
[
  {
    "id": "synth_q1r2s3t4",
    "profile_id": "prof_a1b2c3d4",
    "provider_name": "kokoro",
    "text": "Welcome to Atlas Vox.",
    "audio_url": "/api/v1/audio/synth_q1r2s3t4.wav",
    "output_format": "wav",
    "duration_seconds": 3.2,
    "latency_ms": 450,
    "created_at": "2026-03-22T11:00:00Z"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Synthesis record UUID |
| `profile_id` | `string` | Profile used |
| `provider_name` | `string` | Provider used |
| `text` | `string` | Input text |
| `audio_url` | `string \| null` | URL to audio file |
| `output_format` | `string` | Audio format |
| `duration_seconds` | `float \| null` | Audio duration |
| `latency_ms` | `integer \| null` | Generation latency |
| `created_at` | `string` | ISO 8601 timestamp |

---

## Comparison

<a id="post-compare"></a>

### `POST` /compare

Synthesize the same text across multiple voice profiles for side-by-side comparison.

**Request Body**

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `text` | `string` | Yes | -- | 1-5,000 characters | Text to synthesize |
| `profile_ids` | `string[]` | Yes | -- | Minimum 2 profiles | Profile IDs to compare |
| `speed` | `float` | No | `1.0` | -- | Speaking rate multiplier |
| `pitch` | `float` | No | `0.0` | -- | Pitch shift |

```json
{
  "text": "The quick brown fox jumps over the lazy dog.",
  "profile_ids": ["prof_a1b2c3d4", "prof_e5f6g7h8"],
  "speed": 1.0,
  "pitch": 0.0
}
```

**Response `200 OK`**

```json
{
  "text": "The quick brown fox jumps over the lazy dog.",
  "results": [
    {
      "profile_id": "prof_a1b2c3d4",
      "profile_name": "Corporate Narrator",
      "provider_name": "kokoro",
      "audio_url": "/api/v1/audio/cmp_001.wav",
      "duration_seconds": 2.8,
      "latency_ms": 420
    },
    {
      "profile_id": "prof_e5f6g7h8",
      "profile_name": "Friendly Assistant",
      "provider_name": "elevenlabs",
      "audio_url": "/api/v1/audio/cmp_002.wav",
      "duration_seconds": 3.1,
      "latency_ms": 850
    }
  ]
}
```

**CompareResponse Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `text` | `string` | The input text that was synthesized |
| `results` | `CompareResult[]` | One result per profile (profiles with errors are excluded) |

**CompareResult Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `profile_id` | `string` | Profile ID |
| `profile_name` | `string` | Profile display name |
| `provider_name` | `string` | Provider used for this profile |
| `audio_url` | `string` | URL to the generated audio |
| `duration_seconds` | `float \| null` | Audio duration |
| `latency_ms` | `integer` | Generation latency in milliseconds |

**Error Responses**

| Status | Condition |
|--------|-----------|
| `400` | Fewer than 2 profiles, invalid profile IDs |

---

## Providers

Providers are the TTS engines that power voice synthesis and training. Atlas Vox ships with 9 providers ranging from lightweight CPU-only engines to GPU-accelerated models.

<a id="get-providers"></a>

### `GET` /providers

List all known TTS providers with their implementation status and capabilities. Does **not** require authentication.

**Response `200 OK`**

```json
{
  "providers": [
    {
      "id": "kokoro",
      "name": "kokoro",
      "display_name": "Kokoro TTS",
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
      "health": null,
      "created_at": "2026-03-20T00:00:00Z",
      "updated_at": "2026-03-20T00:00:00Z"
    }
  ],
  "count": 9
}
```

**ProviderResponse Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Provider identifier |
| `name` | `string` | Provider name (used in API calls) |
| `display_name` | `string` | Human-readable provider name |
| `provider_type` | `string` | `"local"`, `"cloud"`, or `"hybrid"` |
| `enabled` | `boolean` | Whether the provider implementation is available |
| `gpu_mode` | `string` | GPU configuration: `"none"`, `"host_cpu"`, `"docker_gpu"` |
| `capabilities` | `object \| null` | Provider capability details (see below) |
| `health` | `object \| null` | Last health check result |
| `created_at` | `datetime` | ISO 8601 timestamp |
| `updated_at` | `datetime` | ISO 8601 timestamp |

**ProviderCapabilities Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `supports_cloning` | `boolean` | Can clone voices from audio samples |
| `supports_fine_tuning` | `boolean` | Supports model fine-tuning |
| `supports_streaming` | `boolean` | Can stream audio output |
| `supports_ssml` | `boolean` | Accepts SSML input |
| `supports_zero_shot` | `boolean` | Zero-shot voice generation |
| `supports_batch` | `boolean` | Batch synthesis support |
| `requires_gpu` | `boolean` | Requires GPU for operation |
| `gpu_mode` | `string` | GPU mode setting |
| `min_samples_for_cloning` | `integer` | Minimum audio samples needed for cloning |
| `max_text_length` | `integer` | Maximum input text length |
| `supported_languages` | `string[]` | Supported language codes |
| `supported_output_formats` | `string[]` | Supported output formats |

---

<a id="get-providersname"></a>

### `GET` /providers/{name}

Get detailed information for a specific provider.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `string` | Provider name (e.g., `kokoro`, `elevenlabs`, `coqui_xtts`) |

**Response `200 OK`**

Returns a single `ProviderResponse` object.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | Provider not found |

**Available Provider Names:**

| Name | Display Name | Type | GPU |
|------|-------------|------|-----|
| `elevenlabs` | ElevenLabs | Cloud | No |
| `azure_speech` | Azure AI Speech | Cloud | No |
| `coqui_xtts` | Coqui XTTS v2 | Local | Configurable |
| `styletts2` | StyleTTS2 | Local | Configurable |
| `cosyvoice` | CosyVoice | Local | Configurable |
| `kokoro` | Kokoro TTS | Local | No (CPU) |
| `piper` | Piper TTS | Local | No (CPU) |
| `dia` | Dia | Local | Configurable |
| `dia2` | Dia2 | Local | Configurable |

---

<a id="post-providersnamehealth"></a>

### `POST` /providers/{name}/health

Run a live health check on a provider. Tests connectivity, model loading, and basic functionality.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `string` | Provider name |

**Response `200 OK`**

```json
{
  "name": "kokoro",
  "healthy": true,
  "latency_ms": 12,
  "error": null
}
```

**ProviderHealthSchema Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | `string` | Provider name |
| `healthy` | `boolean` | Whether the provider is operational |
| `latency_ms` | `integer \| null` | Health check latency |
| `error` | `string \| null` | Error message if unhealthy |

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | Provider not available (not implemented or not loaded) |

---

<a id="get-providersnamevoices"></a>

### `GET` /providers/{name}/voices

List available built-in voices for a provider.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `string` | Provider name |

**Response `200 OK`**

```json
{
  "provider": "kokoro",
  "voices": [
    {
      "voice_id": "af_bella",
      "name": "Bella",
      "language": "en"
    },
    {
      "voice_id": "am_adam",
      "name": "Adam",
      "language": "en"
    }
  ],
  "count": 2
}
```

| Field | Type | Description |
|-------|------|-------------|
| `provider` | `string` | Provider name |
| `voices` | `object[]` | Array of available voices |
| `voices[].voice_id` | `string` | Voice identifier (provider-specific) |
| `voices[].name` | `string` | Human-readable voice name |
| `voices[].language` | `string` | Voice language code |
| `count` | `integer` | Total number of voices |

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | Provider not available |

---

## Presets

Persona presets store reusable synthesis parameter configurations (speed, pitch, volume). Atlas Vox ships with 6 system presets that are automatically seeded on first access. Users can create custom presets. System presets cannot be modified or deleted.

**System Presets (auto-seeded):**

| Name | Speed | Pitch | Volume | Description |
|------|-------|-------|--------|-------------|
| Friendly | 1.0 | 2.0 | 1.0 | Warm and approachable |
| Professional | 0.95 | 0.0 | 1.0 | Clear and authoritative |
| Energetic | 1.15 | 5.0 | 1.1 | Upbeat and enthusiastic |
| Calm | 0.85 | -3.0 | 0.9 | Soothing and relaxed |
| Authoritative | 0.9 | -5.0 | 1.15 | Commanding and confident |
| Soothing | 0.8 | -2.0 | 0.85 | Gentle and comforting |

<a id="get-presets"></a>

### `GET` /presets

List all persona presets (system + custom). System presets are seeded automatically on first call.

**Response `200 OK`**

```json
{
  "presets": [
    {
      "id": "pre_u1v2w3x4",
      "name": "Friendly",
      "description": "Warm and approachable",
      "speed": 1.0,
      "pitch": 2.0,
      "volume": 1.0,
      "is_system": true,
      "created_at": "2026-03-20T00:00:00Z",
      "updated_at": "2026-03-20T00:00:00Z"
    }
  ],
  "count": 6
}
```

**PresetResponse Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Preset UUID |
| `name` | `string` | Display name |
| `description` | `string \| null` | Description of the preset character |
| `speed` | `float` | Speaking rate (0.5-2.0) |
| `pitch` | `float` | Pitch offset (-50.0 to 50.0) |
| `volume` | `float` | Volume level (0.0-2.0) |
| `is_system` | `boolean` | Whether this is a built-in system preset |
| `created_at` | `datetime` | ISO 8601 creation timestamp |
| `updated_at` | `datetime` | ISO 8601 last update timestamp |

---

<a id="post-presets"></a>

### `POST` /presets

Create a custom persona preset.

**Request Body**

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `name` | `string` | Yes | -- | 1-100 characters | Preset name |
| `description` | `string` | No | `null` | -- | Description |
| `speed` | `float` | No | `1.0` | 0.5 -- 2.0 | Speaking rate |
| `pitch` | `float` | No | `0.0` | -50.0 -- 50.0 | Pitch offset |
| `volume` | `float` | No | `1.0` | 0.0 -- 2.0 | Volume level |

```json
{
  "name": "Narrator",
  "description": "Slow and deliberate for audiobook narration",
  "speed": 0.85,
  "pitch": -1.0,
  "volume": 1.0
}
```

**Response `201 Created`**

Returns a `PresetResponse` object with `is_system: false`.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `422` | Validation error (empty name, out-of-range values) |

---

<a id="put-presetsid"></a>

### `PUT` /presets/{preset_id}

Update a custom preset. System presets cannot be modified.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `preset_id` | `string` | Preset UUID |

**Request Body**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `name` | `string` | No | 1-100 characters | Preset name |
| `description` | `string` | No | -- | Description |
| `speed` | `float` | No | 0.5 -- 2.0 | Speaking rate |
| `pitch` | `float` | No | -50.0 -- 50.0 | Pitch offset |
| `volume` | `float` | No | 0.0 -- 2.0 | Volume level |

**Response `200 OK`**

Returns the updated `PresetResponse` object.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `403` | Cannot modify system presets |
| `404` | Preset not found |

---

<a id="delete-presetsid"></a>

### `DELETE` /presets/{preset_id}

Delete a custom preset. System presets cannot be deleted.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `preset_id` | `string` | Preset UUID |

**Response `204 No Content`**

Empty response body on success.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `403` | Cannot delete system presets |
| `404` | Preset not found |

---

## API Keys

API keys provide programmatic access to Atlas Vox when authentication is enabled. Keys use the `avx_` prefix and are stored as salted hashes -- the full key is displayed **only once** at creation time.

<a id="post-api-keys"></a>

### `POST` /api-keys

Create a new API key. **The full key value is returned only in this response.**

**Request Body**

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `name` | `string` | Yes | -- | 1-200 characters | Descriptive name for the key |
| `scopes` | `string[]` | No | `["read", "synthesize"]` | Valid values: `read`, `write`, `synthesize`, `train`, `admin` | Permission scopes |

```json
{
  "name": "CI/CD Pipeline Key",
  "scopes": ["read", "synthesize"]
}
```

**Response `201 Created`**

```json
{
  "id": "key_y1z2a3b4",
  "name": "CI/CD Pipeline Key",
  "key": "avx_AbCdEfGhIjKlMnOpQrStUvWxYz0123456789abcdefgh",
  "key_prefix": "avx_AbCdEfGh",
  "scopes": ["read", "synthesize"],
  "created_at": "2026-03-22T12:00:00Z"
}
```

> **Warning:** The `key` field contains the full API key. Store it securely -- it will never be shown again.

**ApiKeyCreateResponse Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Key UUID |
| `name` | `string` | Descriptive name |
| `key` | `string` | Full API key (shown once) |
| `key_prefix` | `string` | First 12 characters for identification |
| `scopes` | `string[]` | Granted permission scopes |
| `created_at` | `datetime` | ISO 8601 creation timestamp |

**Error Responses**

| Status | Condition |
|--------|-----------|
| `400` | Invalid scope values |

---

<a id="get-api-keys"></a>

### `GET` /api-keys

List all API keys. Keys are masked -- only the prefix is shown.

**Response `200 OK`**

```json
{
  "api_keys": [
    {
      "id": "key_y1z2a3b4",
      "name": "CI/CD Pipeline Key",
      "key_prefix": "avx_AbCdEfGh",
      "scopes": "read,synthesize",
      "active": true,
      "last_used_at": "2026-03-22T14:30:00Z",
      "created_at": "2026-03-22T12:00:00Z"
    }
  ],
  "count": 1
}
```

**ApiKeyResponse Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Key UUID |
| `name` | `string` | Descriptive name |
| `key_prefix` | `string` | First 12 characters of the key |
| `scopes` | `string` | Comma-separated scope string |
| `active` | `boolean` | Whether the key is active |
| `last_used_at` | `datetime \| null` | Last usage timestamp |
| `created_at` | `datetime` | ISO 8601 creation timestamp |

---

<a id="delete-api-keysid"></a>

### `DELETE` /api-keys/{key_id}

Revoke an API key. The key is deactivated (not deleted) -- it will no longer authenticate requests.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `key_id` | `string` | Key UUID |

**Response `204 No Content`**

Empty response body on success.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | API key not found |

---

## Webhooks

Webhooks deliver HTTP POST notifications when specific events occur in Atlas Vox. They are useful for integrating training completion into CI/CD pipelines or notification systems.

**Supported Events:**

| Event | Description |
|-------|-------------|
| `training.completed` | Fired when a training job finishes successfully |
| `training.failed` | Fired when a training job fails |
| `*` | Wildcard -- receive all events |

<a id="get-webhooks"></a>

### `GET` /webhooks

List all webhook subscriptions.

**Response `200 OK`**

```json
{
  "webhooks": [
    {
      "id": "wh_c1d2e3f4",
      "url": "https://example.com/hooks/atlas-vox",
      "events": "training.completed,training.failed",
      "active": true,
      "created_at": "2026-03-20T10:00:00Z",
      "updated_at": "2026-03-20T10:00:00Z"
    }
  ],
  "count": 1
}
```

**WebhookResponse Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Webhook UUID |
| `url` | `string` | Delivery URL |
| `events` | `string` | Comma-separated event names |
| `active` | `boolean` | Whether the webhook is active |
| `created_at` | `datetime` | ISO 8601 creation timestamp |
| `updated_at` | `datetime` | ISO 8601 last update timestamp |

---

<a id="post-webhooks"></a>

### `POST` /webhooks

Create a webhook subscription.

**Request Body**

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `url` | `string` | Yes | -- | Max 1,000 characters | Delivery URL (must be HTTPS in production) |
| `events` | `string[]` | Yes | -- | Min 1 item; valid: `training.completed`, `training.failed`, `*` | Events to subscribe to |
| `secret` | `string` | No | `null` | -- | HMAC secret for signature verification |

```json
{
  "url": "https://example.com/hooks/atlas-vox",
  "events": ["training.completed", "training.failed"],
  "secret": "my-webhook-secret"
}
```

**Response `201 Created`**

Returns a `WebhookResponse` object.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `400` | Invalid event names |

---

<a id="put-webhooksid"></a>

### `PUT` /webhooks/{webhook_id}

Update a webhook subscription. All fields are optional.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `webhook_id` | `string` | Webhook UUID |

**Request Body**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `url` | `string` | No | Max 1,000 characters | Delivery URL |
| `events` | `string[]` | No | Valid event names | Events to subscribe to |
| `secret` | `string` | No | -- | HMAC secret |
| `active` | `boolean` | No | -- | Enable/disable the webhook |

**Response `200 OK`**

Returns the updated `WebhookResponse` object.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | Webhook not found |

---

<a id="delete-webhooksid"></a>

### `DELETE` /webhooks/{webhook_id}

Delete a webhook subscription permanently.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `webhook_id` | `string` | Webhook UUID |

**Response `204 No Content`**

Empty response body on success.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | Webhook not found |

---

<a id="post-webhooksidtest"></a>

### `POST` /webhooks/{webhook_id}/test

Send a test payload to a webhook endpoint to verify connectivity.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `webhook_id` | `string` | Webhook UUID |

**Response `200 OK`**

```json
{
  "deliveries": [
    {
      "webhook_id": "wh_c1d2e3f4",
      "status_code": 200,
      "success": true
    }
  ]
}
```

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | Webhook not found |

---

## Audio

<a id="get-audiofilename"></a>

### `GET` /audio/{filename}

Serve a generated audio file from the output storage directory. Audio files are created by synthesis and comparison endpoints.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `filename` | `string` | Audio filename (e.g., `synth_q1r2s3t4.wav`) |

**Response `200 OK`**

Returns the audio file as a binary download.

| Format | Content-Type |
|--------|-------------|
| WAV | `audio/wav` |
| MP3 | `audio/mpeg` |
| OGG | `audio/ogg` |
| FLAC | `audio/flac` |
| Other | `application/octet-stream` |

The response includes a `Content-Disposition` header with the filename.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `404` | Audio file not found |

---

## curl Examples

### Create a Voice Profile

```bash
curl -X POST http://localhost:8100/api/v1/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Corporate Narrator",
    "description": "Professional male voice for training videos",
    "language": "en",
    "provider_name": "kokoro",
    "tags": ["corporate", "male"]
  }'
```

### Upload Audio Samples

```bash
curl -X POST http://localhost:8100/api/v1/profiles/prof_a1b2c3d4/samples \
  -F "files=@recording_001.wav" \
  -F "files=@recording_002.wav" \
  -F "files=@recording_003.wav"
```

### Trigger Sample Preprocessing

```bash
curl -X POST http://localhost:8100/api/v1/profiles/prof_a1b2c3d4/samples/preprocess
```

### Start a Training Job

```bash
curl -X POST http://localhost:8100/api/v1/profiles/prof_a1b2c3d4/train \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "epochs": 100,
      "learning_rate": 0.0001
    }
  }'
```

### Monitor Training Progress (WebSocket)

```bash
# Using websocat (https://github.com/vi/websocat)
websocat ws://localhost:8100/api/v1/training/jobs/job_m1n2o3p4/progress

# With authentication:
websocat "ws://localhost:8100/api/v1/training/jobs/job_m1n2o3p4/progress?token=avx_..."
```

### Synthesize Text to Speech

```bash
curl -X POST http://localhost:8100/api/v1/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Welcome to Atlas Vox, your intelligent voice platform.",
    "profile_id": "prof_a1b2c3d4",
    "speed": 1.0,
    "output_format": "wav"
  }'
```

### Stream Synthesis

```bash
curl -X POST http://localhost:8100/api/v1/synthesize/stream \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This audio will be streamed in chunks.",
    "profile_id": "prof_a1b2c3d4"
  }' \
  --output streamed_audio.wav
```

### Batch Synthesis

```bash
curl -X POST http://localhost:8100/api/v1/synthesize/batch \
  -H "Content-Type: application/json" \
  -d '{
    "lines": [
      "Chapter one: The Beginning.",
      "It was a dark and stormy night.",
      "The end."
    ],
    "profile_id": "prof_a1b2c3d4",
    "output_format": "mp3"
  }'
```

### Compare Voices

```bash
curl -X POST http://localhost:8100/api/v1/compare \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The quick brown fox jumps over the lazy dog.",
    "profile_ids": ["prof_a1b2c3d4", "prof_e5f6g7h8"]
  }'
```

### Download Generated Audio

```bash
curl -O http://localhost:8100/api/v1/audio/synth_q1r2s3t4.wav
```

### Create an API Key (when auth is enabled)

```bash
curl -X POST http://localhost:8100/api/v1/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -d '{
    "name": "CI/CD Pipeline Key",
    "scopes": ["read", "synthesize"]
  }'
```

### Use an API Key for Authentication

```bash
curl http://localhost:8100/api/v1/profiles \
  -H "Authorization: Bearer avx_AbCdEfGhIjKlMnOpQrStUvWxYz0123456789abcdefgh"
```

### Register a Webhook

```bash
curl -X POST http://localhost:8100/api/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/hooks/atlas-vox",
    "events": ["training.completed", "training.failed"],
    "secret": "my-webhook-secret"
  }'
```

### Check Provider Health

```bash
curl -X POST http://localhost:8100/api/v1/providers/kokoro/health
```

### List Provider Voices

```bash
curl http://localhost:8100/api/v1/providers/kokoro/voices
```

---

<sub>Generated from source code at `backend/app/api/v1/` and `backend/app/schemas/`. Last updated: 2026-03-25.</sub>
