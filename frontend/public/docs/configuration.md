# Configuration

## Environment Variables

Atlas Vox is configured via environment variables. Set them in a `.env` file or export them in your shell.

### Application

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `APP_NAME` | str | Atlas Vox | Application display name |
| `APP_VERSION` | str | 0.1.0 | Application version string |
| `DEBUG` | bool | false | Enable debug mode with verbose logging |
| `LOG_LEVEL` | str | INFO | Logging level: DEBUG, INFO, WARNING, ERROR |
| `AUTH_DISABLED` | bool | true | Disable authentication (single-user mode) |

### Server

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `BACKEND_HOST` | str | 0.0.0.0 | Backend bind address |
| `BACKEND_PORT` | int | 8100 | Backend HTTP port |
| `FRONTEND_PORT` | int | 3100 | Frontend dev server port (Vite) |
| `CORS_ORIGINS` | str | * | Comma-separated allowed CORS origins |
| `RATE_LIMIT_SYNTHESIS` | int | 10 | Synthesis requests per minute |
| `RATE_LIMIT_TRAINING` | int | 5 | Training requests per minute |

### Database

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATABASE_URL` | str | sqlite+aiosqlite:///atlas_vox.db | SQLAlchemy async database URL |
| `DATABASE_ECHO` | bool | false | Echo SQL statements (debug) |

### Auth

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `JWT_SECRET` | str | (auto-generated) | JWT signing secret (32+ characters) |
| `JWT_ALGORITHM` | str | HS256 | JWT signing algorithm |
| `JWT_EXPIRATION_MINUTES` | int | 60 | JWT token expiration in minutes |

### Redis

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `REDIS_URL` | str | redis://localhost:6379/1 | Redis connection URL (uses db 1) |
| `CELERY_BROKER_URL` | str | redis://localhost:6379/1 | Celery broker URL |
| `CELERY_RESULT_BACKEND` | str | redis://localhost:6379/1 | Celery result backend URL |

### Storage

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STORAGE_DIR` | str | ./storage | Root directory for file storage |
| `AUDIO_OUTPUT_DIR` | str | ./storage/audio | Synthesized audio output directory |
| `SAMPLES_DIR` | str | ./storage/samples | Training sample upload directory |
| `MODELS_DIR` | str | ./storage/models | Model weights directory |

### Providers

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `KOKORO_ENABLED` | bool | true | Enable Kokoro TTS provider |
| `PIPER_ENABLED` | bool | true | Enable Piper TTS provider |
| `PIPER_MODEL_PATH` | str | ./storage/models/piper | Path to Piper ONNX model files |
| `ELEVENLABS_API_KEY` | str | *(required)* | ElevenLabs API key |
| `ELEVENLABS_MODEL_ID` | str | eleven_multilingual_v2 | ElevenLabs TTS model ID |
| `AZURE_SPEECH_KEY` | str | *(required)* | Azure Speech subscription key |
| `AZURE_SPEECH_REGION` | str | eastus | Azure Speech service region |
| `COQUI_XTTS_GPU_MODE` | str | host_cpu | Coqui XTTS GPU mode: host_cpu, docker_gpu, auto |
| `STYLETTS2_GPU_MODE` | str | host_cpu | StyleTTS2 GPU mode |
| `COSYVOICE_GPU_MODE` | str | host_cpu | CosyVoice GPU mode |
| `DIA_GPU_MODE` | str | host_cpu | Dia GPU mode |
| `DIA2_GPU_MODE` | str | host_cpu | Dia2 GPU mode |

---

## Configuration Profiles

### Development

Local development with hot reload. No GPU, no auth, SQLite database.

```env
DEBUG=true
LOG_LEVEL=DEBUG
AUTH_DISABLED=true
DATABASE_URL=sqlite+aiosqlite:///atlas_vox.db
REDIS_URL=redis://localhost:6379/1
KOKORO_ENABLED=true
PIPER_ENABLED=true
```

### Homelab

Self-hosted deployment with GPU support. Optional auth. Docker Compose recommended.

```env
DEBUG=false
LOG_LEVEL=INFO
AUTH_DISABLED=true
DATABASE_URL=sqlite+aiosqlite:///atlas_vox.db
REDIS_URL=redis://redis:6379/1
COQUI_XTTS_GPU_MODE=docker_gpu
DIA_GPU_MODE=docker_gpu
ELEVENLABS_API_KEY=sk_your_key_here
```

### Production

Full production deployment with PostgreSQL, auth enabled, and all providers configured.

```env
DEBUG=false
LOG_LEVEL=WARNING
AUTH_DISABLED=false
JWT_SECRET=your-32-char-secret-here-change-me
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/atlas_vox
REDIS_URL=redis://redis:6379/1
CORS_ORIGINS=https://your-domain.com
ELEVENLABS_API_KEY=sk_your_key
AZURE_SPEECH_KEY=your_azure_key
AZURE_SPEECH_REGION=eastus
```

---

## Example .env File

```env
# Atlas Vox Environment Configuration
# Copy to .env and customize for your deployment

# --- Application ---
APP_NAME=Atlas Vox
DEBUG=false
LOG_LEVEL=INFO
AUTH_DISABLED=true

# --- Server ---
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8100
CORS_ORIGINS=http://localhost:3100,http://localhost:3000

# --- Database ---
DATABASE_URL=sqlite+aiosqlite:///atlas_vox.db

# --- Redis ---
REDIS_URL=redis://localhost:6379/1
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# --- Storage ---
STORAGE_DIR=./storage
AUDIO_OUTPUT_DIR=./storage/audio
SAMPLES_DIR=./storage/samples
MODELS_DIR=./storage/models

# --- Cloud Providers (optional) ---
# ELEVENLABS_API_KEY=sk_your_key_here
# AZURE_SPEECH_KEY=your_key_here
# AZURE_SPEECH_REGION=eastus

# --- GPU Providers (optional) ---
# COQUI_XTTS_GPU_MODE=docker_gpu
# STYLETTS2_GPU_MODE=docker_gpu
# COSYVOICE_GPU_MODE=docker_gpu
# DIA_GPU_MODE=docker_gpu
# DIA2_GPU_MODE=docker_gpu
```
