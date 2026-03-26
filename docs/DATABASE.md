# Atlas Vox Database Schema Reference

> **Version**: 1.0 | **Last updated**: 2026-03-25 | **Engine**: SQLAlchemy 2.x (async) with Alembic migrations

---

## Table of Contents

- [1. Database Overview](#1-database-overview)
- [2. Entity-Relationship Diagram](#2-entity-relationship-diagram)
- [3. Table Definitions](#3-table-definitions)
  - [3.1 providers](#31-providers)
  - [3.2 voice_profiles](#32-voice_profiles)
  - [3.3 audio_samples](#33-audio_samples)
  - [3.4 training_jobs](#34-training_jobs)
  - [3.5 model_versions](#35-model_versions)
  - [3.6 synthesis_history](#36-synthesis_history)
  - [3.7 persona_presets](#37-persona_presets)
  - [3.8 api_keys](#38-api_keys)
  - [3.9 webhooks](#39-webhooks)
- [4. Relationships and Cascade Behavior](#4-relationships-and-cascade-behavior)
- [5. Status Enums and State Machines](#5-status-enums-and-state-machines)
- [6. JSON Field Schemas](#6-json-field-schemas)
- [7. Data Flow Diagrams](#7-data-flow-diagrams)
- [8. Migration Guide](#8-migration-guide)
- [9. Design Decisions and Rationale](#9-design-decisions-and-rationale)

---

## 1. Database Overview

Atlas Vox uses a relational database to persist voice profiles, audio samples, training job state, model versions, synthesis history, persona presets, API keys, and webhook subscriptions. The schema is designed around the **voice profile lifecycle**: create a profile, upload audio samples, train a model, and synthesize speech.

### Supported Engines

| Engine | Connection URL | Use Case |
|:---|:---|:---|
| **SQLite** (default) | `sqlite+aiosqlite:///./atlas_vox.db` | Local development, single-user mode |
| **PostgreSQL** (optional) | `postgresql+asyncpg://user:pass@host/db` | Production, multi-user, concurrent workloads |

### Engine Configuration

The database URL is set via the `DATABASE_URL` environment variable or the `database_url` field in `backend/app/core/config.py`. SQLite is the out-of-the-box default; switching to PostgreSQL requires only changing the connection string.

```bash
# SQLite (default)
DATABASE_URL=sqlite+aiosqlite:///./atlas_vox.db

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://atlas:secret@localhost:5432/atlas_vox
```

### Async Architecture

All database access is fully asynchronous via SQLAlchemy's `AsyncSession`:

- **Engine**: `create_async_engine` with `aiosqlite` (SQLite) or `asyncpg` (PostgreSQL)
- **Sessions**: `async_sessionmaker` with `expire_on_commit=False`
- **Transaction model**: Each request gets a session, auto-commits on success, rolls back on exception
- **SQLite safety**: `check_same_thread=False` is set automatically for SQLite connections

### Key Conventions

| Convention | Detail |
|:---|:---|
| **Primary keys** | `VARCHAR(36)` UUIDs generated at the application layer via `uuid.uuid4()` |
| **Timestamps** | `DateTime` (UTC), set via `datetime.now(UTC)` lambdas |
| **Auto-update** | `updated_at` columns use SQLAlchemy's `onupdate` trigger |
| **JSON storage** | Complex data stored as `Text` columns containing JSON strings |
| **ORM base** | All models extend `app.core.database.Base` (`DeclarativeBase`) |
| **Mapped columns** | SQLAlchemy 2.x `Mapped[T]` / `mapped_column()` syntax throughout |

---

## 2. Entity-Relationship Diagram

```mermaid
erDiagram
    providers ||--o{ voice_profiles : "hosts profiles"
    providers ||--o{ training_jobs : "runs training"
    voice_profiles ||--o{ audio_samples : "has samples"
    voice_profiles ||--o{ training_jobs : "has jobs"
    voice_profiles ||--o{ model_versions : "has versions"
    voice_profiles ||--o| model_versions : "active version"

    providers {
        VARCHAR_36 id PK
        VARCHAR_50 name UK "unique slug"
        VARCHAR_100 display_name
        VARCHAR_20 provider_type "cloud | local"
        BOOLEAN enabled
        VARCHAR_20 gpu_mode "none | docker_gpu | host_cpu | auto"
        TEXT config_json "JSON provider config"
        DATETIME created_at
        DATETIME updated_at
    }

    voice_profiles {
        VARCHAR_36 id PK
        VARCHAR_200 name "indexed"
        TEXT description
        VARCHAR_10 language "default: en"
        VARCHAR_50 provider_name FK "providers.name"
        VARCHAR_20 status "pending | training | ready | error | archived"
        TEXT tags "JSON array of strings"
        VARCHAR_36 active_version_id FK "model_versions.id (nullable)"
        DATETIME created_at
        DATETIME updated_at
    }

    audio_samples {
        VARCHAR_36 id PK
        VARCHAR_36 profile_id FK "voice_profiles.id"
        VARCHAR_500 filename
        VARCHAR_500 original_filename
        VARCHAR_1000 file_path
        VARCHAR_10 format "wav | mp3 | flac"
        FLOAT duration_seconds
        INTEGER sample_rate
        INTEGER file_size_bytes
        BOOLEAN preprocessed "default: false"
        VARCHAR_1000 preprocessed_path
        TEXT analysis_json "JSON pitch/energy/spectral"
        DATETIME created_at
    }

    training_jobs {
        VARCHAR_36 id PK
        VARCHAR_36 profile_id FK "voice_profiles.id"
        VARCHAR_50 provider_name FK "providers.name"
        VARCHAR_20 status "queued | preprocessing | training | completed | failed | cancelled"
        FLOAT progress "0.0 to 1.0"
        VARCHAR_100 celery_task_id
        TEXT config_json "JSON training config"
        TEXT error_message
        VARCHAR_36 result_version_id FK "model_versions.id (nullable)"
        DATETIME started_at
        DATETIME completed_at
        DATETIME created_at
        DATETIME updated_at
    }

    model_versions {
        VARCHAR_36 id PK
        VARCHAR_36 profile_id FK "voice_profiles.id"
        INTEGER version_number
        VARCHAR_500 provider_model_id "provider-specific ID"
        VARCHAR_1000 model_path "local file path"
        TEXT config_json "training config snapshot"
        TEXT metrics_json "quality metrics"
        DATETIME created_at
    }

    synthesis_history {
        VARCHAR_36 id PK
        VARCHAR_36 profile_id "NO FK - audit trail"
        VARCHAR_50 provider_name
        TEXT text
        VARCHAR_1000 output_path
        VARCHAR_10 output_format "default: wav"
        FLOAT duration_seconds
        INTEGER latency_ms
        TEXT settings_json "JSON speed/pitch/volume/persona"
        DATETIME created_at
    }

    persona_presets {
        VARCHAR_36 id PK
        VARCHAR_100 name UK
        TEXT description
        FLOAT speed "default: 1.0 (range 0.5-2.0)"
        FLOAT pitch "default: 0.0 (range -50 to +50)"
        FLOAT volume "default: 1.0 (range 0.0-2.0)"
        BOOLEAN is_system "default: false"
        TEXT settings_json "extra provider-specific"
        DATETIME created_at
        DATETIME updated_at
    }

    api_keys {
        VARCHAR_36 id PK
        VARCHAR_200 name
        VARCHAR_500 key_hash "Argon2id hash"
        VARCHAR_10 key_prefix "first 8 chars"
        TEXT scopes "CSV: read write synthesize train admin"
        BOOLEAN active "default: true"
        DATETIME last_used_at
        DATETIME created_at
    }

    webhooks {
        VARCHAR_36 id PK
        VARCHAR_1000 url
        TEXT events "CSV: training.completed training.failed"
        VARCHAR_500 secret "HMAC-SHA256 signing key"
        BOOLEAN active "default: true"
        DATETIME created_at
        DATETIME updated_at
    }
```

---

## 3. Table Definitions

### 3.1 `providers`

> **Source**: `backend/app/models/provider.py`
>
> Stores registered TTS provider configurations. Each provider has a unique slug name used as the foreign key target by `voice_profiles` and `training_jobs`.

| Column | Type | Constraints | Default | Description |
|:---|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | `PRIMARY KEY` | `uuid4()` | Unique identifier |
| `name` | `VARCHAR(50)` | `UNIQUE`, `NOT NULL`, `INDEX` | -- | Provider slug (e.g., `kokoro`, `elevenlabs`) |
| `display_name` | `VARCHAR(100)` | `NOT NULL` | -- | Human-readable name (e.g., "Kokoro TTS") |
| `provider_type` | `VARCHAR(20)` | `NOT NULL` | -- | `cloud` or `local` |
| `enabled` | `BOOLEAN` | | `False` | Whether the provider is activated |
| `gpu_mode` | `VARCHAR(20)` | | `"none"` | GPU configuration: `none`, `docker_gpu`, `host_cpu`, `auto` |
| `config_json` | `TEXT` | `NULLABLE` | `NULL` | JSON string of provider-specific configuration |
| `created_at` | `DATETIME` | | `now(UTC)` | Record creation timestamp |
| `updated_at` | `DATETIME` | | `now(UTC)` | Last modification timestamp (auto-updated) |

**Indexes**: `name` (unique index)

---

### 3.2 `voice_profiles`

> **Source**: `backend/app/models/voice_profile.py`
>
> The central entity in Atlas Vox. A voice profile aggregates audio samples, training jobs, and model versions for a single voice identity.

| Column | Type | Constraints | Default | Description |
|:---|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | `PRIMARY KEY` | `uuid4()` | Unique identifier |
| `name` | `VARCHAR(200)` | `NOT NULL`, `INDEX` | -- | Display name for the profile |
| `description` | `TEXT` | `NULLABLE` | `NULL` | Optional long description |
| `language` | `VARCHAR(10)` | | `"en"` | BCP-47 language tag |
| `provider_name` | `VARCHAR(50)` | `NOT NULL`, `FK -> providers.name` | -- | TTS provider backing this profile |
| `status` | `VARCHAR(20)` | | `"pending"` | Lifecycle status (see [State Machines](#5-status-enums-and-state-machines)) |
| `tags` | `TEXT` | `NULLABLE` | `NULL` | JSON-encoded array of string tags |
| `active_version_id` | `VARCHAR(36)` | `NULLABLE`, `FK -> model_versions.id` | `NULL` | Currently active model version |
| `created_at` | `DATETIME` | | `now(UTC)` | Record creation timestamp |
| `updated_at` | `DATETIME` | | `now(UTC)` | Last modification timestamp (auto-updated) |

**Indexes**: `name` (non-unique index)

**Relationships**:
- `samples` -> `audio_samples[]` (cascade: all, delete-orphan)
- `versions` -> `model_versions[]` (cascade: all, delete-orphan)
- `training_jobs` -> `training_jobs[]` (cascade: all, delete-orphan)

---

### 3.3 `audio_samples`

> **Source**: `backend/app/models/audio_sample.py`
>
> Audio files uploaded as training data for a voice profile. Each sample tracks both the original and preprocessed file paths, along with audio analysis metadata.

| Column | Type | Constraints | Default | Description |
|:---|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | `PRIMARY KEY` | `uuid4()` | Unique identifier |
| `profile_id` | `VARCHAR(36)` | `NOT NULL`, `FK -> voice_profiles.id` | -- | Parent voice profile |
| `filename` | `VARCHAR(500)` | `NOT NULL` | -- | Server-side filename (renamed on upload) |
| `original_filename` | `VARCHAR(500)` | `NOT NULL` | -- | Original filename from the client |
| `file_path` | `VARCHAR(1000)` | `NOT NULL` | -- | Full path to the stored audio file |
| `format` | `VARCHAR(10)` | `NOT NULL` | -- | Audio format: `wav`, `mp3`, `flac`, etc. |
| `duration_seconds` | `FLOAT` | `NULLABLE` | `NULL` | Audio duration in seconds |
| `sample_rate` | `INTEGER` | `NULLABLE` | `NULL` | Audio sample rate in Hz |
| `file_size_bytes` | `INTEGER` | `NULLABLE` | `NULL` | File size in bytes |
| `preprocessed` | `BOOLEAN` | | `False` | Whether preprocessing has been applied |
| `preprocessed_path` | `VARCHAR(1000)` | `NULLABLE` | `NULL` | Path to preprocessed audio file |
| `analysis_json` | `TEXT` | `NULLABLE` | `NULL` | JSON object with pitch, energy, and spectral analysis |
| `created_at` | `DATETIME` | | `now(UTC)` | Record creation timestamp |

**Relationships**:
- `profile` -> `voice_profiles` (many-to-one, back-populates `samples`)

---

### 3.4 `training_jobs`

> **Source**: `backend/app/models/training_job.py`
>
> Tracks the lifecycle of an asynchronous training task. Each job is executed by a Celery worker and produces a `model_version` on success.

| Column | Type | Constraints | Default | Description |
|:---|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | `PRIMARY KEY` | `uuid4()` | Unique identifier |
| `profile_id` | `VARCHAR(36)` | `NOT NULL`, `FK -> voice_profiles.id` | -- | Voice profile being trained |
| `provider_name` | `VARCHAR(50)` | `NOT NULL`, `FK -> providers.name` | -- | TTS provider running the training |
| `status` | `VARCHAR(20)` | | `"queued"` | Job status (see [State Machines](#5-status-enums-and-state-machines)) |
| `progress` | `FLOAT` | | `0.0` | Progress percentage (0.0 to 1.0) |
| `celery_task_id` | `VARCHAR(100)` | `NULLABLE` | `NULL` | Celery async task ID for status polling |
| `config_json` | `TEXT` | `NULLABLE` | `NULL` | JSON training configuration (epochs, lr, etc.) |
| `error_message` | `TEXT` | `NULLABLE` | `NULL` | Error details if job failed |
| `result_version_id` | `VARCHAR(36)` | `NULLABLE`, `FK -> model_versions.id` | `NULL` | Model version produced on successful completion |
| `started_at` | `DATETIME` | `NULLABLE` | `NULL` | Timestamp when training actually began |
| `completed_at` | `DATETIME` | `NULLABLE` | `NULL` | Timestamp when training finished (success or failure) |
| `created_at` | `DATETIME` | | `now(UTC)` | Record creation timestamp |
| `updated_at` | `DATETIME` | | `now(UTC)` | Last modification timestamp (auto-updated) |

**Relationships**:
- `profile` -> `voice_profiles` (many-to-one, back-populates `training_jobs`)

---

### 3.5 `model_versions`

> **Source**: `backend/app/models/model_version.py`
>
> An immutable snapshot of a trained model. Each successful training job creates exactly one model version. A profile's `active_version_id` points to the version used for synthesis.

| Column | Type | Constraints | Default | Description |
|:---|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | `PRIMARY KEY` | `uuid4()` | Unique identifier |
| `profile_id` | `VARCHAR(36)` | `NOT NULL`, `FK -> voice_profiles.id` | -- | Parent voice profile |
| `version_number` | `INTEGER` | `NOT NULL` | -- | Monotonically increasing version within the profile |
| `provider_model_id` | `VARCHAR(500)` | `NULLABLE` | `NULL` | Provider-specific model identifier (e.g., ElevenLabs voice ID) |
| `model_path` | `VARCHAR(1000)` | `NULLABLE` | `NULL` | Local filesystem path to model artifacts |
| `config_json` | `TEXT` | `NULLABLE` | `NULL` | Snapshot of the training configuration used |
| `metrics_json` | `TEXT` | `NULLABLE` | `NULL` | Quality metrics (loss, MOS score, etc.) |
| `created_at` | `DATETIME` | | `now(UTC)` | Record creation timestamp |

**Relationships**:
- `profile` -> `voice_profiles` (many-to-one, back-populates `versions`)

---

### 3.6 `synthesis_history`

> **Source**: `backend/app/models/synthesis_history.py`
>
> An append-only audit log of every synthesis request. Intentionally has **no foreign key** on `profile_id` so that records survive profile deletion, preserving usage analytics.

| Column | Type | Constraints | Default | Description |
|:---|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | `PRIMARY KEY` | `uuid4()` | Unique identifier |
| `profile_id` | `VARCHAR(36)` | `NOT NULL` | -- | Voice profile used (no FK -- audit trail) |
| `provider_name` | `VARCHAR(50)` | `NOT NULL` | -- | TTS provider used (no FK -- audit trail) |
| `text` | `TEXT` | `NOT NULL` | -- | Input text that was synthesized |
| `output_path` | `VARCHAR(1000)` | `NULLABLE` | `NULL` | Path to the generated audio file |
| `output_format` | `VARCHAR(10)` | | `"wav"` | Audio output format |
| `duration_seconds` | `FLOAT` | `NULLABLE` | `NULL` | Duration of the generated audio |
| `latency_ms` | `INTEGER` | `NULLABLE` | `NULL` | Time taken to generate the audio |
| `settings_json` | `TEXT` | `NULLABLE` | `NULL` | JSON snapshot of synthesis settings (speed, pitch, volume, persona) |
| `created_at` | `DATETIME` | | `now(UTC)` | Record creation timestamp |

> **Design note**: This table has no `updated_at` column because records are immutable once written.

---

### 3.7 `persona_presets`

> **Source**: `backend/app/models/persona_preset.py`
>
> Reusable synthesis parameter bundles. Six system presets are auto-seeded on the first API call to `GET /api/v1/presets`. System presets cannot be modified or deleted.

| Column | Type | Constraints | Default | Description |
|:---|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | `PRIMARY KEY` | `uuid4()` | Unique identifier |
| `name` | `VARCHAR(100)` | `UNIQUE`, `NOT NULL` | -- | Preset name |
| `description` | `TEXT` | `NULLABLE` | `NULL` | What this persona sounds like |
| `speed` | `FLOAT` | | `1.0` | Speech rate multiplier (range: 0.5 -- 2.0) |
| `pitch` | `FLOAT` | | `0.0` | Pitch shift in semitones (range: -50 -- +50) |
| `volume` | `FLOAT` | | `1.0` | Volume multiplier (range: 0.0 -- 2.0) |
| `is_system` | `BOOLEAN` | | `False` | `True` for built-in presets (immutable) |
| `settings_json` | `TEXT` | `NULLABLE` | `NULL` | Extra provider-specific settings |
| `created_at` | `DATETIME` | | `now(UTC)` | Record creation timestamp |
| `updated_at` | `DATETIME` | | `now(UTC)` | Last modification timestamp (auto-updated) |

**Indexes**: `name` (unique index)

#### System Presets (Auto-Seeded)

| Name | Description | Speed | Pitch | Volume |
|:---|:---|---:|---:|---:|
| Friendly | Warm and approachable | 1.00 | +2.0 | 1.00 |
| Professional | Clear and authoritative | 0.95 | 0.0 | 1.00 |
| Energetic | Upbeat and enthusiastic | 1.15 | +5.0 | 1.10 |
| Calm | Soothing and relaxed | 0.85 | -3.0 | 0.90 |
| Authoritative | Commanding and confident | 0.90 | -5.0 | 1.15 |
| Soothing | Gentle and comforting | 0.80 | -2.0 | 0.85 |

---

### 3.8 `api_keys`

> **Source**: `backend/app/models/api_key.py`
>
> Stores hashed API keys for programmatic access. The raw key is shown to the user exactly once at creation time; only the Argon2id hash is persisted.

| Column | Type | Constraints | Default | Description |
|:---|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | `PRIMARY KEY` | `uuid4()` | Unique identifier |
| `name` | `VARCHAR(200)` | `NOT NULL` | -- | Human-readable key label |
| `key_hash` | `VARCHAR(500)` | `NOT NULL` | -- | Argon2id hash of the raw API key |
| `key_prefix` | `VARCHAR(10)` | `NOT NULL` | -- | First 8 characters of the raw key (for identification) |
| `scopes` | `TEXT` | | `"read,synthesize"` | Comma-separated permission scopes |
| `active` | `BOOLEAN` | | `True` | Whether the key is currently valid |
| `last_used_at` | `DATETIME` | `NULLABLE` | `NULL` | Timestamp of last successful authentication |
| `created_at` | `DATETIME` | | `now(UTC)` | Record creation timestamp |

#### Available Scopes

| Scope | Grants |
|:---|:---|
| `read` | Read voice profiles, samples, presets, providers |
| `write` | Create/update/delete profiles, samples, presets |
| `synthesize` | Generate speech via synthesis endpoints |
| `train` | Submit and manage training jobs |
| `admin` | Full access including API key and webhook management |

---

### 3.9 `webhooks`

> **Source**: `backend/app/models/webhook.py`
>
> Webhook subscriptions for event-driven notifications. When a subscribed event fires, Atlas Vox sends an HTTP POST to the registered URL, signed with HMAC-SHA256 if a secret is configured.

| Column | Type | Constraints | Default | Description |
|:---|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | `PRIMARY KEY` | `uuid4()` | Unique identifier |
| `url` | `VARCHAR(1000)` | `NOT NULL` | -- | Target URL for webhook delivery |
| `events` | `TEXT` | `NOT NULL` | -- | Comma-separated event types to subscribe to |
| `secret` | `VARCHAR(500)` | `NULLABLE` | `NULL` | Shared secret for HMAC-SHA256 payload signing |
| `active` | `BOOLEAN` | | `True` | Whether the webhook is enabled |
| `created_at` | `DATETIME` | | `now(UTC)` | Record creation timestamp |
| `updated_at` | `DATETIME` | | `now(UTC)` | Last modification timestamp (auto-updated) |

#### Available Events

| Event | Trigger |
|:---|:---|
| `training.completed` | A training job finishes successfully |
| `training.failed` | A training job fails |
| `training.started` | A training job begins processing |
| `synthesis.completed` | A synthesis request finishes |

---

## 4. Relationships and Cascade Behavior

### Foreign Key Map

```
providers.name  <----  voice_profiles.provider_name
providers.name  <----  training_jobs.provider_name

voice_profiles.id  <----  audio_samples.profile_id       (CASCADE DELETE)
voice_profiles.id  <----  training_jobs.profile_id        (CASCADE DELETE)
voice_profiles.id  <----  model_versions.profile_id       (CASCADE DELETE)

model_versions.id  <----  voice_profiles.active_version_id  (NULLABLE, SET NULL on delete)
model_versions.id  <----  training_jobs.result_version_id   (NULLABLE)
```

### Cascade Behavior

| Parent | Child | On Delete | Behavior |
|:---|:---|:---|:---|
| `voice_profiles` | `audio_samples` | **CASCADE** | All samples deleted with their profile |
| `voice_profiles` | `training_jobs` | **CASCADE** | All jobs deleted with their profile |
| `voice_profiles` | `model_versions` | **CASCADE** | All versions deleted with their profile |
| `providers` | `voice_profiles` | **RESTRICT** | Cannot delete a provider with existing profiles |
| `providers` | `training_jobs` | **RESTRICT** | Cannot delete a provider with existing jobs |

### Intentionally Unlinked

| Table | Column | Why No FK |
|:---|:---|:---|
| `synthesis_history` | `profile_id` | Audit trail must survive profile deletion. A profile deleted 6 months ago should still show up in usage reports. |
| `synthesis_history` | `provider_name` | Same rationale -- historical accuracy over referential integrity. |

### Relationship Diagram (Simplified)

```
                    +-------------+
                    |  providers  |
                    +------+------+
                           |
              name FK      |      name FK
          +----------------+------------------+
          |                                   |
  +-------v--------+                 +--------v-------+
  | voice_profiles |                 | training_jobs  |
  +---+----+---+---+                 +--------+-------+
      |    |   |                              |
      |    |   +--- active_version_id --------+--- result_version_id
      |    |                |                 |
      |    |        +-------v--------+        |
      |    |        | model_versions |<-------+
      |    |        +----------------+
      |    |
      |    +---> audio_samples
      |
      +- - - - > synthesis_history (no FK, audit only)
```

---

## 5. Status Enums and State Machines

### Voice Profile Status

The `voice_profiles.status` column tracks the lifecycle of a voice profile.

```mermaid
stateDiagram-v2
    [*] --> pending : Profile created

    pending --> training : Training job submitted
    training --> ready : Training completed successfully
    training --> error : Training failed

    ready --> training : Re-train with new samples
    ready --> archived : User archives profile

    error --> training : Retry training
    error --> archived : User archives profile

    archived --> pending : User unarchives profile

    pending --> archived : User archives before training
```

| Status | Description | Allowed Transitions |
|:---|:---|:---|
| `pending` | Profile created, awaiting training | `training`, `archived` |
| `training` | Active training job in progress | `ready`, `error` |
| `ready` | Model trained and available for synthesis | `training`, `archived` |
| `error` | Training failed, requires intervention | `training`, `archived` |
| `archived` | Soft-deleted, hidden from default listings | `pending` |

---

### Training Job Status

The `training_jobs.status` column tracks the lifecycle of an individual training run.

```mermaid
stateDiagram-v2
    [*] --> queued : Job created

    queued --> preprocessing : Celery worker picks up job
    queued --> cancelled : User cancels before start

    preprocessing --> training : Audio preprocessed
    preprocessing --> failed : Preprocessing error
    preprocessing --> cancelled : User cancels

    training --> completed : Model trained successfully
    training --> failed : Training error
    training --> cancelled : User cancels

    completed --> [*]
    failed --> [*]
    cancelled --> [*]
```

| Status | Description | Progress Range | Terminal? |
|:---|:---|:---|:---|
| `queued` | Waiting in Celery queue | 0.0 | No |
| `preprocessing` | Normalizing and validating audio samples | 0.0 -- 0.2 | No |
| `training` | Model training in progress | 0.2 -- 0.95 | No |
| `completed` | Training finished, model version created | 1.0 | Yes |
| `failed` | An error occurred, see `error_message` | varies | Yes |
| `cancelled` | User or system cancelled the job | varies | Yes |

---

### Provider GPU Mode

The `providers.gpu_mode` column determines how the provider executes inference and training.

| Mode | Description |
|:---|:---|
| `none` | CPU-only providers (Kokoro, Piper) or cloud providers (ElevenLabs, Azure) |
| `host_cpu` | Local model runs on host CPU |
| `docker_gpu` | Local model runs inside a GPU-enabled Docker container |
| `auto` | System auto-detects GPU availability and picks the best mode |

---

## 6. JSON Field Schemas

Several columns store structured data as JSON strings. Below are the expected shapes.

### `voice_profiles.tags`

```json
["male", "english", "narrator", "deep"]
```

A flat array of string tags for filtering and categorization.

---

### `audio_samples.analysis_json`

```json
{
  "pitch": {
    "mean_hz": 142.5,
    "min_hz": 85.0,
    "max_hz": 320.0,
    "std_hz": 38.2
  },
  "energy": {
    "mean_db": -22.4,
    "max_db": -8.1,
    "rms": 0.075
  },
  "spectral": {
    "spectral_centroid": 1842.0,
    "spectral_bandwidth": 1560.0,
    "zero_crossing_rate": 0.085
  },
  "duration_seconds": 12.4,
  "sample_rate": 22050,
  "channels": 1
}
```

---

### `training_jobs.config_json`

```json
{
  "epochs": 100,
  "batch_size": 8,
  "learning_rate": 0.0001,
  "warmup_steps": 500,
  "sample_rate": 22050,
  "provider_specific": {
    "model_variant": "xtts_v2",
    "language": "en"
  }
}
```

---

### `model_versions.config_json`

Snapshot of the `training_jobs.config_json` at the time training completed -- preserving the exact configuration that produced this model.

---

### `model_versions.metrics_json`

```json
{
  "loss": 0.0342,
  "mel_loss": 0.0218,
  "duration_loss": 0.0124,
  "mos_estimate": 3.82,
  "training_time_seconds": 1847,
  "epochs_completed": 100
}
```

---

### `synthesis_history.settings_json`

```json
{
  "speed": 1.0,
  "pitch": 0.0,
  "volume": 1.0,
  "persona": "Professional",
  "output_format": "wav",
  "sample_rate": 22050,
  "provider_specific": {}
}
```

---

### `persona_presets.settings_json`

```json
{
  "emotion": "neutral",
  "emphasis": 0.5,
  "pause_factor": 1.0
}
```

Extra provider-specific tuning knobs beyond the standard speed/pitch/volume.

---

### `providers.config_json`

Shape varies by provider. Examples:

**Cloud provider (ElevenLabs)**:
```json
{
  "model_id": "eleven_multilingual_v2",
  "stability": 0.5,
  "similarity_boost": 0.75,
  "style": 0.0
}
```

**Local provider (Coqui XTTS)**:
```json
{
  "model_version": "v2.0.3",
  "device": "cpu",
  "compute_type": "float32",
  "max_audio_length_seconds": 30
}
```

---

## 7. Data Flow Diagrams

### 7.1 Create Voice Profile

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI
    participant DB as Database
    participant Prov as Provider Registry

    User->>API: POST /api/v1/profiles
    Note right of User: { name, provider_name, language, tags }

    API->>DB: Verify provider exists (SELECT providers WHERE name = ?)
    DB-->>API: Provider row

    alt Provider not found or disabled
        API-->>User: 400 Bad Request
    end

    API->>DB: INSERT INTO voice_profiles (status = 'pending')
    DB-->>API: New profile row

    API-->>User: 201 Created { id, name, status: "pending", ... }
```

---

### 7.2 Upload Audio Samples

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI
    participant FS as File System
    participant DB as Database

    User->>API: POST /api/v1/profiles/{id}/samples
    Note right of User: multipart/form-data (audio files)

    API->>DB: Verify profile exists
    DB-->>API: Profile row

    loop For each uploaded file
        API->>FS: Save to storage/{profile_id}/{uuid}.{ext}
        FS-->>API: File path

        API->>API: Extract metadata (duration, sample_rate, size)

        API->>DB: INSERT INTO audio_samples
        DB-->>API: Sample row
    end

    API-->>User: 201 Created { samples: [...] }
```

---

### 7.3 Train Voice Model

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI
    participant DB as Database
    participant Celery as Celery Worker
    participant Provider as TTS Provider
    participant WH as Webhook Dispatcher

    User->>API: POST /api/v1/profiles/{id}/train
    Note right of User: { config overrides }

    API->>DB: Verify profile + samples exist
    API->>DB: INSERT INTO training_jobs (status = 'queued')
    API->>DB: UPDATE voice_profiles SET status = 'training'
    API->>Celery: Dispatch train_voice_model.delay(job_id)

    API-->>User: 202 Accepted { job_id, status: "queued" }

    Note over Celery: Async execution begins

    Celery->>DB: UPDATE training_jobs SET status = 'preprocessing'
    Celery->>Provider: Preprocess audio samples
    Provider-->>Celery: Preprocessed files

    Celery->>DB: UPDATE training_jobs SET status = 'training', progress = 0.2
    Celery->>Provider: Train model (with progress callbacks)

    loop Progress updates
        Provider-->>Celery: progress = 0.X
        Celery->>DB: UPDATE training_jobs SET progress = 0.X
    end

    Provider-->>Celery: Trained model artifacts

    Celery->>DB: INSERT INTO model_versions (version_number = N)
    Celery->>DB: UPDATE training_jobs SET status = 'completed', result_version_id = ?
    Celery->>DB: UPDATE voice_profiles SET status = 'ready', active_version_id = ?

    Celery->>WH: POST to subscribed webhooks (training.completed)
```

---

### 7.4 Synthesize Speech

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI
    participant DB as Database
    participant Provider as TTS Provider
    participant FS as File System

    User->>API: POST /api/v1/synthesis
    Note right of User: { profile_id, text, settings }

    API->>DB: Load profile + active model version
    DB-->>API: Profile (status = 'ready'), ModelVersion

    alt Profile not ready
        API-->>User: 400 "Profile not ready for synthesis"
    end

    API->>DB: Load persona preset (if specified in settings)
    API->>Provider: synthesize(text, model_version, settings)

    Note over Provider: TTS inference

    Provider-->>API: Audio bytes + metadata

    API->>FS: Save to storage/synthesis/{uuid}.{format}
    FS-->>API: Output path

    API->>DB: INSERT INTO synthesis_history (latency_ms, duration, ...)
    DB-->>API: History row

    API-->>User: 200 OK { audio_url, duration, latency_ms }
```

---

## 8. Migration Guide

Atlas Vox uses [Alembic](https://alembic.sqlalchemy.org/) for database migrations, configured for async operation with SQLAlchemy 2.x.

### Configuration

| File | Purpose |
|:---|:---|
| `backend/alembic.ini` | Alembic settings (script location, logging) |
| `backend/alembic/env.py` | Migration environment with async engine support |
| `backend/alembic/versions/` | Individual migration scripts |

The `alembic/env.py` overrides the connection URL from `alembic.ini` with `settings.database_url` at runtime, so the `DATABASE_URL` environment variable always takes precedence.

### Common Commands

```bash
# Navigate to the backend directory
cd backend

# Create a new migration (auto-detects model changes)
alembic revision --autogenerate -m "description of changes"

# Apply all pending migrations
alembic upgrade head

# Apply migrations up to a specific revision
alembic upgrade <revision_id>

# Rollback the last migration
alembic downgrade -1

# Rollback to a specific revision
alembic downgrade <revision_id>

# Rollback all migrations (reset database)
alembic downgrade base

# Show current migration state
alembic current

# Show migration history
alembic history --verbose

# Show pending migrations
alembic history --indicate-current
```

### Development Shortcut

For development and testing, `init_db()` in `backend/app/core/database.py` creates all tables directly from model metadata without Alembic:

```python
from app.core.database import init_db

async def startup():
    await init_db()  # CREATE TABLE IF NOT EXISTS for all models
```

> **Warning**: Do not use `init_db()` in production. It cannot handle schema changes or data migrations. Always use Alembic in production environments.

### Creating Migrations for New Models

1. Define the model in `backend/app/models/<name>.py`
2. Import it in `backend/app/models/__init__.py` so it registers with `Base.metadata`
3. Verify `backend/alembic/env.py` imports the model (or imports from `__init__`)
4. Generate the migration:
   ```bash
   cd backend
   alembic revision --autogenerate -m "add <table_name> table"
   ```
5. Review the generated migration in `backend/alembic/versions/`
6. Apply it:
   ```bash
   alembic upgrade head
   ```

### Switching from SQLite to PostgreSQL

1. Set the connection URL:
   ```bash
   export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/atlas_vox
   ```
2. Create the database:
   ```bash
   createdb atlas_vox
   ```
3. Run all migrations from scratch:
   ```bash
   cd backend && alembic upgrade head
   ```

> **Note**: There is no automatic data migration tool between SQLite and PostgreSQL. For existing data, export from SQLite and import into PostgreSQL manually, or use a tool like `pgloader`.

---

## 9. Design Decisions and Rationale

### UUIDs as Primary Keys

All tables use `VARCHAR(36)` UUIDs generated at the application layer (`uuid.uuid4()`), not database-native auto-increment integers.

**Why**: UUIDs allow IDs to be generated client-side or in distributed workers without a database round-trip. This is critical for Celery tasks that create `model_versions` records -- the worker can generate the ID before inserting, avoiding race conditions. The tradeoff is slightly larger index sizes, which is negligible at Atlas Vox's expected scale.

---

### JSON Text Columns Instead of Normalized Tables

Several columns (`tags`, `analysis_json`, `config_json`, `metrics_json`, `settings_json`) store JSON as `TEXT` rather than using normalized relational tables.

**Why**: These fields are provider-specific and schema-fluid. A normalized `tags` table would add join overhead for a simple array. Training configs vary wildly between providers (Coqui XTTS needs different parameters than ElevenLabs). JSON columns keep the schema stable while allowing each provider to store whatever it needs. The tradeoff is that you cannot query *inside* these fields efficiently in SQLite (PostgreSQL's `JSONB` would improve this if needed).

---

### No Foreign Key on `synthesis_history.profile_id`

The `synthesis_history` table intentionally omits a foreign key constraint on `profile_id`.

**Why**: Synthesis history is an audit log. If a user deletes a voice profile, the history of what they synthesized with it must survive. A foreign key with `CASCADE DELETE` would destroy usage analytics. A foreign key with `SET NULL` would lose the association. Keeping the profile ID as a plain value preserves the full history while allowing profiles to be freely deleted.

---

### Provider Name as Foreign Key (Not ID)

`voice_profiles.provider_name` and `training_jobs.provider_name` reference `providers.name` (the unique slug), not `providers.id`.

**Why**: The provider name is a natural key that is meaningful, stable, and human-readable. It appears in API responses, configuration files, and logs. Using it as the FK eliminates the need for joins when you just need to know which provider backs a profile. Provider names like `kokoro`, `elevenlabs`, or `coqui_xtts` are defined by the system and do not change.

---

### Lazy Seeding of System Presets

The 6 system persona presets are inserted on-demand (the first time `GET /api/v1/presets` is called) rather than via a migration or startup hook.

**Why**: This avoids coupling data seeding to the migration pipeline. Migrations should be structural (schema changes), not data-oriented. Lazy seeding also means the presets are automatically created in test databases without needing a separate fixture.

---

### Dual Timestamp Pattern

Most tables have `created_at` and `updated_at` columns, but `audio_samples`, `model_versions`, `synthesis_history`, and `api_keys` have only `created_at`.

**Why**: These are effectively immutable records. An audio sample, once uploaded, is not modified -- it might be deleted, but never updated. A model version is a snapshot. Synthesis history is an audit log. API keys only track `last_used_at` for the mutable part. Omitting `updated_at` from immutable tables signals to developers that these records should not be mutated.

| Has `updated_at` | Reason |
|:---|:---|
| `providers` | Config can be toggled, GPU mode changed |
| `voice_profiles` | Status changes, name/description edits |
| `training_jobs` | Status and progress updated continuously |
| `persona_presets` | Custom presets can be edited |
| `webhooks` | URL, events, and active flag can change |
| ~~`audio_samples`~~ | Immutable after upload |
| ~~`model_versions`~~ | Immutable training artifacts |
| ~~`synthesis_history`~~ | Immutable audit log |
| ~~`api_keys`~~ | Only `last_used_at` changes (separate column) |

---

### `expire_on_commit=False`

The session factory is configured with `expire_on_commit=False`.

**Why**: In an async context with SQLAlchemy, accessing attributes on a committed object would normally trigger a lazy load, which requires a synchronous database call -- impossible inside an `async def`. Disabling expiration keeps attributes accessible after commit without re-querying.

---

*This document was generated from the SQLAlchemy model definitions in `backend/app/models/` and the database configuration in `backend/app/core/`. For the latest schema, always refer to the model source files and Alembic migration history.*
