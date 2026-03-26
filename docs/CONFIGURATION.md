# Atlas Vox Configuration Reference

> **Complete reference for all environment variables, configuration modes, and deployment profiles.**

Atlas Vox uses [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) to manage configuration. All settings are read from environment variables and/or a `.env` file in the project root.

---

## Table of Contents

- [How Configuration Works](#how-configuration-works)
- [Complete Variable Reference](#complete-variable-reference)
  - [Application](#application)
  - [Server](#server)
  - [Database](#database)
  - [Authentication](#authentication)
  - [Redis](#redis)
  - [Storage](#storage)
  - [Provider: ElevenLabs](#provider-elevenlabs)
  - [Provider: Azure AI Speech](#provider-azure-ai-speech)
  - [Provider: Coqui XTTS v2](#provider-coqui-xtts-v2)
  - [Provider: StyleTTS2](#provider-styletts2)
  - [Provider: CosyVoice](#provider-cosyvoice)
  - [Provider: Kokoro](#provider-kokoro)
  - [Provider: Piper](#provider-piper)
  - [Provider: Dia](#provider-dia)
  - [Provider: Dia2](#provider-dia2)
- [Configuration Profiles](#configuration-profiles)
  - [Development (Default)](#development-default)
  - [Homelab](#homelab)
  - [Production](#production)
  - [GPU Workstation](#gpu-workstation)
- [Production vs Development Differences](#production-vs-development-differences)
- [Advanced Topics](#advanced-topics)
  - [CORS Origins Format](#cors-origins-format)
  - [GPU Mode Values](#gpu-mode-values)
  - [Database URL Formats](#database-url-formats)
  - [Computed Properties](#computed-properties)

---

## How Configuration Works

Configuration is loaded through this priority chain (highest priority first):

```
Environment variables  >  .env file  >  Default values
```

1. **Environment variables** -- set via `export`, Docker Compose, systemd, etc.
2. **`.env` file** -- placed in the working directory (typically `backend/`)
3. **Default values** -- defined in `backend/app/core/config.py`

To get started, copy the example file:

```bash
cp .env.example .env
```

The settings object is a singleton. Import it anywhere in the codebase:

```python
from app.core.config import settings

print(settings.app_name)        # "atlas-vox"
print(settings.is_production)   # False
print(settings.is_sqlite)       # True
```

---

## Complete Variable Reference

### Application

Core application identity and behavior.

| Variable | Type | Default | Description |
|---|---|---|---|
| `APP_NAME` | `str` | `atlas-vox` | Application name used in logs and server info |
| `APP_ENV` | `str` | `development` | Environment: `development`, `staging`, `production` |
| `DEBUG` | `bool` | `true` | Enable debug mode (verbose logging, auto-reload) |
| `LOG_LEVEL` | `str` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` | `str` | `json` | Log format: `json` (structured) or `console` (human-readable) |

---

### Server

HTTP server binding and CORS.

| Variable | Type | Default | Description |
|---|---|---|---|
| `HOST` | `str` | `0.0.0.0` | Host to bind the API server to |
| `PORT` | `int` | `8000` | Port to listen on |
| `CORS_ORIGINS` | `list[str]` | `["http://localhost:3000", "http://localhost:5173"]` | Allowed CORS origins (JSON array format) |

---

### Database

Database connection. SQLite works out of the box; PostgreSQL is recommended for production.

| Variable | Type | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | `str` | `sqlite+aiosqlite:///./atlas_vox.db` | Async database URL (SQLAlchemy format) |

**Supported database URLs:**

| Database | URL Format |
|---|---|
| SQLite (default) | `sqlite+aiosqlite:///./atlas_vox.db` |
| SQLite (absolute) | `sqlite+aiosqlite:////var/data/atlas_vox.db` |
| PostgreSQL | `postgresql+asyncpg://user:password@host:5432/atlas_vox` |

---

### Authentication

Authentication can be completely disabled for single-user/homelab setups.

| Variable | Type | Default | Description |
|---|---|---|---|
| `AUTH_DISABLED` | `bool` | `true` | Disable all authentication. When `true`, all requests get a default admin user. |
| `JWT_SECRET_KEY` | `str` | `change-me-in-production` | Secret key for JWT signing. **Must** be changed in production. |
| `JWT_ALGORITHM` | `str` | `HS256` | JWT signing algorithm |
| `JWT_EXPIRE_MINUTES` | `int` | `1440` | Token expiration time (default: 24 hours) |

> **Security Warning:** The default `JWT_SECRET_KEY` is intentionally insecure. Generate a proper key for any non-local deployment:
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(32))"
> ```

---

### Redis

Required for Celery task queue (training jobs, preprocessing).

| Variable | Type | Default | Description |
|---|---|---|---|
| `REDIS_URL` | `str` | `redis://localhost:6379/0` | Redis connection URL (used as Celery broker and result backend) |

---

### Storage

File storage for audio samples, preprocessed data, synthesized output, and model weights.

| Variable | Type | Default | Description |
|---|---|---|---|
| `STORAGE_PATH` | `path` | `./storage` | Root directory for all file storage |

**Storage directory structure** (created by `atlas-vox init`):

```
storage/
+-- samples/           # Raw uploaded audio files, organized by profile_id
+-- preprocessed/      # Processed audio ready for training
+-- output/            # Synthesized audio output files
+-- models/
    +-- piper/         # Piper ONNX model files
    +-- coqui_xtts/    # Coqui XTTS model files
```

---

### Provider: ElevenLabs

Cloud-based TTS via the ElevenLabs API. Requires an API key.

| Variable | Type | Default | Description |
|---|---|---|---|
| `ELEVENLABS_API_KEY` | `str` | `""` (disabled) | ElevenLabs API key. Leave empty to disable. |
| `ELEVENLABS_MODEL_ID` | `str` | `eleven_multilingual_v2` | Model ID for synthesis |

---

### Provider: Azure AI Speech

Cloud-based TTS via Azure Cognitive Services. Requires a subscription key.

| Variable | Type | Default | Description |
|---|---|---|---|
| `AZURE_SPEECH_KEY` | `str` | `""` (disabled) | Azure Speech Service subscription key |
| `AZURE_SPEECH_REGION` | `str` | `eastus` | Azure region for the speech resource |

---

### Provider: Coqui XTTS v2

Local voice cloning model. Requires only 6 seconds of reference audio.

| Variable | Type | Default | Description |
|---|---|---|---|
| `COQUI_XTTS_GPU_MODE` | `str` | `host_cpu` | Execution mode (see [GPU Mode Values](#gpu-mode-values)) |

---

### Provider: StyleTTS2

Local zero-shot voice synthesis with style diffusion.

| Variable | Type | Default | Description |
|---|---|---|---|
| `STYLETTS2_GPU_MODE` | `str` | `host_cpu` | Execution mode |

---

### Provider: CosyVoice

Local multilingual voice synthesis with streaming support.

| Variable | Type | Default | Description |
|---|---|---|---|
| `COSYVOICE_GPU_MODE` | `str` | `host_cpu` | Execution mode |

---

### Provider: Kokoro

Lightweight local TTS with 54 built-in voices. CPU-only, no GPU required. **Default provider.**

| Variable | Type | Default | Description |
|---|---|---|---|
| `KOKORO_ENABLED` | `bool` | `true` | Enable/disable Kokoro provider |

---

### Provider: Piper

Fast ONNX-based local TTS compatible with Home Assistant.

| Variable | Type | Default | Description |
|---|---|---|---|
| `PIPER_ENABLED` | `bool` | `true` | Enable/disable Piper provider |
| `PIPER_MODEL_PATH` | `path` | `./storage/models/piper` | Directory for Piper ONNX models |

---

### Provider: Dia

Local dialogue-oriented TTS model with 1.6B parameters.

| Variable | Type | Default | Description |
|---|---|---|---|
| `DIA_GPU_MODE` | `str` | `host_cpu` | Execution mode |

---

### Provider: Dia2

Streaming dialogue model with 2B parameters (successor to Dia).

| Variable | Type | Default | Description |
|---|---|---|---|
| `DIA2_GPU_MODE` | `str` | `host_cpu` | Execution mode |

---

## Configuration Profiles

### Development (Default)

Minimal setup for local development. Works out of the box with no external dependencies beyond Python.

```env
# .env -- Development
APP_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG
LOG_FORMAT=console

DATABASE_URL=sqlite+aiosqlite:///./atlas_vox.db
AUTH_DISABLED=true

KOKORO_ENABLED=true
PIPER_ENABLED=true
```

---

### Homelab

Self-hosted single-user deployment. Authentication disabled, SQLite database, local providers only.

```env
# .env -- Homelab
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["http://homelab.local:3000"]

DATABASE_URL=sqlite+aiosqlite:////opt/atlas-vox/data/atlas_vox.db
AUTH_DISABLED=true
STORAGE_PATH=/opt/atlas-vox/storage
REDIS_URL=redis://localhost:6379/0

KOKORO_ENABLED=true
PIPER_ENABLED=true
COQUI_XTTS_GPU_MODE=host_cpu
```

---

### Production

Multi-user deployment with PostgreSQL, authentication, and cloud providers.

```env
# .env -- Production
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["https://vox.example.com"]

DATABASE_URL=postgresql+asyncpg://atlas:s3cret@db.internal:5432/atlas_vox
AUTH_DISABLED=false
JWT_SECRET_KEY=your-generated-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480

REDIS_URL=redis://redis.internal:6379/0
STORAGE_PATH=/var/lib/atlas-vox/storage

ELEVENLABS_API_KEY=sk-your-elevenlabs-key
AZURE_SPEECH_KEY=your-azure-key
AZURE_SPEECH_REGION=westus2

KOKORO_ENABLED=true
PIPER_ENABLED=true
```

---

### GPU Workstation

Development or homelab with NVIDIA GPU for local model acceleration.

```env
# .env -- GPU Workstation
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO

DATABASE_URL=sqlite+aiosqlite:///./atlas_vox.db
AUTH_DISABLED=true
REDIS_URL=redis://localhost:6379/0

# GPU-accelerated providers
COQUI_XTTS_GPU_MODE=docker_gpu
STYLETTS2_GPU_MODE=docker_gpu
COSYVOICE_GPU_MODE=docker_gpu
DIA_GPU_MODE=docker_gpu
DIA2_GPU_MODE=docker_gpu

# CPU providers (always available)
KOKORO_ENABLED=true
PIPER_ENABLED=true
```

---

## Production vs Development Differences

| Behavior | Development | Production |
|---|---|---|
| **Database auto-create** | Tables created on startup via `init_db()` | Disabled -- use Alembic migrations |
| **Debug mode** | Enabled (verbose errors, auto-reload) | Disabled |
| **Log format** | `console` (human-readable) | `json` (structured, machine-parseable) |
| **Authentication** | Disabled by default | **Must** be enabled |
| **JWT secret** | Default insecure key | **Must** be changed |
| **CORS origins** | `localhost:3000`, `localhost:5173` | Production domain only |
| **OpenAPI docs** | Available at `/docs` and `/redoc` | Consider disabling or restricting |

The `is_production` property is derived from the `APP_ENV` variable:

```python
# Returns True when APP_ENV == "production"
settings.is_production
```

---

## Advanced Topics

### CORS Origins Format

The `CORS_ORIGINS` variable accepts a JSON array as a string:

```env
# Single origin
CORS_ORIGINS=["https://app.example.com"]

# Multiple origins
CORS_ORIGINS=["https://app.example.com","https://admin.example.com"]
```

The value is parsed by a Pydantic validator that calls `json.loads()` on string input. You can also pass a native list when constructing settings programmatically.

**Methods allowed by default:** `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`
**Headers allowed:** `Authorization`, `Content-Type`
**Credentials:** Enabled (`allow_credentials=True`)

---

### GPU Mode Values

Providers that support GPU acceleration accept these mode values:

| Value | Description |
|---|---|
| `host_cpu` | Run on the host machine's CPU (default, always works) |
| `docker_gpu` | Run inside a Docker container with NVIDIA GPU passthrough |
| `auto` | Auto-detect: use GPU if CUDA is available, otherwise fall back to CPU |

**Requirements for `docker_gpu`:**

- NVIDIA GPU with CUDA support
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/overview.html) installed
- Docker with GPU runtime configured

---

### Database URL Formats

Atlas Vox uses async SQLAlchemy drivers. The URL must use the async driver prefix:

| Database | Sync Driver | Async Driver (use this) |
|---|---|---|
| SQLite | `sqlite:///` | `sqlite+aiosqlite:///` |
| PostgreSQL | `postgresql://` | `postgresql+asyncpg://` |

The `is_sqlite` property helps code adapt to database-specific behavior:

```python
if settings.is_sqlite:
    # SQLite-specific handling (e.g., no concurrent writes)
    ...
```

---

### Computed Properties

The `Settings` class exposes two computed properties that are not configurable via environment variables:

| Property | Type | Logic |
|---|---|---|
| `is_sqlite` | `bool` | `True` if `DATABASE_URL` contains `"sqlite"` |
| `is_production` | `bool` | `True` if `APP_ENV == "production"` |

These are used internally to gate behavior like automatic table creation and migration strategies.
