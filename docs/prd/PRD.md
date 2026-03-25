# Atlas Vox — Intelligent Voice Training & Customization Platform

## Context

The user wants a standalone, full-featured voice training and customization platform that allows building, managing, and serving TTS voice models across 9 providers (including both Dia and Dia2). The platform must expose four interfaces: a React/TypeScript Web UI, a Python CLI (`atlas-vox`), a REST API, and an MCP server. It is a **standalone repository** (not part of ATLAS) but designed to integrate with ATLAS and other services via its API and MCP server. The user's research covers voice profile extraction, persona customization, noise cleanup, speed/pitch control, and provider comparison — all of which must be productized into a polished developer tool.

**Key decisions from user:**
- Standalone Git repository, independent of ATLAS
- GPU strategy: configurable per provider — Docker GPU containers OR host CPU fallback
- Both Dia (1.6B, dialogue-focused) and Dia2 (2B, streaming) supported as separate providers
- Project name: **Atlas Vox** (CLI: `atlas-vox`)

---

## Product Requirements Document (PRD)

### 1. Product Overview

**Atlas Vox** is a self-hosted voice training and customization platform that provides a unified interface for creating, training, customizing, and serving TTS voice models across multiple providers. It targets developers, home lab enthusiasts, and AI application builders who need a single tool to manage voice synthesis across both local (GPU) and cloud providers.

### 2. Problem Statement

Building custom voice models requires juggling multiple provider APIs, each with different training pipelines, audio requirements, and inference patterns. There is no unified tool that lets users:
- Train voice models across providers from a single UI
- Compare voice quality side-by-side
- Serve trained models via a standard API/MCP interface for other services
- Manage the full lifecycle from audio recording to production serving

### 3. Target Users

- **AI Application Developers**: Need TTS integration via API/MCP for chatbots, agents, assistants
- **Home Lab Enthusiasts**: Want local voice cloning with privacy, running on their own GPU hardware
- **Content Creators**: Need custom voices for narration, podcasts, video
- **Home Automation Users**: Want personalized TTS voices for smart home systems (Home Assistant, etc.)

### 4. Supported TTS Providers (9 total)

| Provider | Type | Voice Cloning | Fine-tuning | Streaming | GPU Required | Key Strength |
|----------|------|---------------|-------------|-----------|-------------|--------------|
| **ElevenLabs** | Cloud | Instant + Pro | No | Yes | No | Premium quality, minimal samples |
| **Azure AI Speech** | Cloud | Custom Neural Voice | Yes | Yes | No | Enterprise SSML, multi-style |
| **Coqui XTTS v2** | Local | 6s min audio | Yes | Yes | Configurable | Open-source, minimal data cloning |
| **StyleTTS2** | Local | Zero-shot | Yes | No | Configurable | Human-level synthesis quality |
| **CosyVoice** | Local | Zero-shot multilingual | No | Yes (150ms) | Configurable | 9 languages + 18 dialects |
| **Kokoro** | Local | No | No | No | No (CPU) | 82M params, fast, 54 voices |
| **Piper** | Local | No | Yes | No | No (CPU) | Ultra-lightweight ONNX, Home Assistant |
| **Nari-labs Dia** | Local | Audio conditioning | No | No | Configurable | Ultra-realistic dialogue, 1.6B params |
| **Nari-labs Dia2** | Local | Limited | No | Yes | Configurable | Streaming dialogue, 2B params |

**GPU Strategy**: Each local GPU provider can be configured to run as:
- **Docker GPU mode**: Provider runs in a Docker container with NVIDIA runtime and pinned CUDA/PyTorch versions (isolates GPU compatibility issues like RTX 5090 sm_120)
- **Host CPU mode**: Provider runs on host in CPU-only mode (slower but works immediately without GPU setup)
- Configuration is per-provider via `.env` or Provider Settings UI

### 5. Core Features

#### 5.1 Voice Profile Management
- Create/edit/delete voice profiles with metadata (name, description, language, provider, tags)
- Upload reference audio samples in multiple formats (WAV, MP3, FLAC, OGG, WebM, M4A)
- In-browser audio recording for training samples
- Audio preprocessing pipeline: noise reduction (noisereduce), normalization (pydub), silence trimming, format conversion to WAV 16kHz mono
- Voice analysis display: pitch contour, energy envelope, spectral characteristics
- Voice profile status lifecycle: pending → training → ready → error → archived

#### 5.2 Training Pipeline
- Provider-specific training workflows with capability-aware UI (hide unsupported features per provider)
- Celery + Redis job queue for long-running GPU training tasks
- Real-time progress tracking via WebSocket
- Model versioning: each training run produces an immutable version; users can A/B compare and roll back
- Audio preprocessing as a separate queued step before training
- Batch training support (queue multiple profiles)

#### 5.3 Voice Customization
- Persona presets: Friendly, Professional, Energetic, Calm, Authoritative, Soothing (user-extensible)
- Speed (0.5x–2.0x), pitch (-50 to +50), volume controls
- SSML editor (Monaco-based) for providers that support it (Azure, Piper partial)
- Real-time preview with parameter adjustments
- Custom persona creation and saving to library

#### 5.4 Synthesis & Testing
- Text-to-speech synthesis with any trained/ready voice model
- Side-by-side comparison: synthesize same text across multiple voices/providers
- Batch synthesis: process a script file (one line per utterance) with a selected voice
- Streaming synthesis for supported providers (ElevenLabs, Coqui XTTS, CosyVoice, Dia2)
- Audio export in WAV, MP3, OGG formats
- Synthesis history log with replay

#### 5.5 REST API
- Full CRUD for profiles, samples, training jobs, presets
- Synthesis endpoints (single, streaming, batch, comparison)
- Provider management and health checks
- API key authentication with scoped permissions (read, write, synthesize, train, admin)
- OpenAPI/Swagger auto-generated documentation
- Rate limiting (configurable per key)
- Webhook subscriptions for training events (completed, failed)

#### 5.6 MCP Server
- JSONRPC 2.0 protocol with SSE transport
- Tools: `atlas_vox_synthesize`, `atlas_vox_list_voices`, `atlas_vox_train_voice`, `atlas_vox_get_training_status`, `atlas_vox_manage_profile`, `atlas_vox_compare_voices`, `atlas_vox_provider_status`
- Resources: `atlas-vox://profiles`, `atlas-vox://providers`
- API key or JWT authentication
- Enables Claude Code, ATLAS, and other AI agents to use Atlas Vox as a voice service

#### 5.7 CLI Interface
- `atlas-vox init` — Initialize configuration and database
- `atlas-vox train <profile> --provider <provider> --samples <dir>` — Train a voice model
- `atlas-vox synthesize <text> --voice <profile> --output <file>` — Generate speech
- `atlas-vox profiles list|create|delete|export|import` — Manage voice profiles
- `atlas-vox providers list|status|configure` — Manage TTS providers
- `atlas-vox serve [--port 8000] [--mcp]` — Start API server (optionally with MCP)
- `atlas-vox compare <text> --voices <v1,v2,...>` — Compare voices side-by-side
- `atlas-vox presets list|create|delete` — Manage persona presets
- Built with Typer + Rich for beautiful terminal output

#### 5.8 Web UI Pages
1. **Dashboard** — Profile count, training jobs (active/completed/failed), provider health grid, recent synthesis history
2. **Voice Profiles** — Card grid with status badges, create/edit modal, audio upload (drag-drop + record), training trigger
3. **Training Studio** — Audio recorder with waveform visualization, sample management, preprocessing controls, training config per provider, real-time progress via WebSocket
4. **Synthesis Lab** — Text area with character count, voice selector dropdown, persona/speed/pitch controls, SSML toggle, preview button with audio player, batch mode tab
5. **Comparison Tool** — Select 2+ voices, enter text, generate side-by-side audio players with latency/quality metrics
6. **Provider Settings** — Card per provider with config form (API keys, endpoints, model selection, GPU/CPU toggle), health check button, capability display
7. **API Keys** — Create/revoke API keys with scope selection, usage stats
8. **Settings** — Theme (light/dark), default provider, audio format preferences, webhook config

### 6. Non-Functional Requirements

- **Performance**: Synthesis latency < 2s for short texts (< 200 chars) on local providers with GPU
- **Scalability**: Handle 10+ concurrent synthesis requests; queue unlimited training jobs
- **Security**: API keys hashed with Argon2id; no plaintext secrets; optional auth disable for single-user
- **Accessibility**: WCAG 2.1 AA, keyboard navigation, ARIA labels, 44px min touch targets
- **Portability**: SQLite default (zero-config), optional PostgreSQL; Docker Compose for one-command deploy
- **Privacy**: All local providers run entirely on user hardware; cloud providers clearly labeled

---

## Technical Architecture

### 7. Technology Stack

**Backend:**
- Python 3.11+
- FastAPI 0.115+ (async REST API + WebSocket)
- Pydantic v2 (validation, settings, schemas)
- SQLAlchemy 2.0+ async (ORM) with aiosqlite (SQLite) or asyncpg (PostgreSQL)
- Alembic (database migrations)
- Celery 5.3+ with Redis (task queue for training jobs)
- structlog (structured JSON logging)
- httpx (async HTTP client for cloud providers)
- Typer + Rich (CLI)
- python-jose[cryptography] (JWT) + argon2-cffi (key hashing)
- pydub + noisereduce + librosa + numpy (audio processing)
- python-multipart (file uploads)
- websockets (WebSocket support)

**Frontend:**
- React 18+ with TypeScript 5+
- Vite (build tool)
- Tailwind CSS (styling with light/dark theme)
- Zustand (state management)
- React Router v6 (routing with lazy loading)
- Framer Motion (animations with prefers-reduced-motion)
- Lucide React (icons)
- Sonner (toast notifications)
- wavesurfer.js (waveform visualization)
- @monaco-editor/react (SSML editor)

**Infrastructure:**
- Docker + Docker Compose
- Redis 7+ (Celery broker + result backend)
- NVIDIA Container Toolkit (optional, for GPU providers in Docker)
- Nginx (optional reverse proxy)

### 8. Provider Abstraction

```python
class TTSProvider(ABC):
    """Abstract base for all TTS providers."""

    @abstractmethod
    async def synthesize(self, text: str, voice_id: str, settings: SynthesisSettings) -> AudioResult:
        """Synthesize text to speech."""

    @abstractmethod
    async def clone_voice(self, samples: list[AudioSample], config: CloneConfig) -> VoiceModel:
        """Clone a voice from audio samples (if supported)."""

    @abstractmethod
    async def fine_tune(self, model_id: str, samples: list[AudioSample], config: FineTuneConfig) -> VoiceModel:
        """Fine-tune an existing model (if supported)."""

    @abstractmethod
    async def list_voices(self) -> list[VoiceInfo]:
        """List available voices/models."""

    @abstractmethod
    async def get_capabilities(self) -> ProviderCapabilities:
        """Return provider capability flags for UI adaptation."""

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Check if provider is reachable and operational."""

    async def stream_synthesize(self, text: str, voice_id: str, settings: SynthesisSettings) -> AsyncIterator[bytes]:
        """Streaming synthesis (optional, raise NotSupported if unavailable)."""
        raise NotImplementedError("Streaming not supported by this provider")
```

```python
@dataclass
class ProviderCapabilities:
    supports_cloning: bool = False
    supports_fine_tuning: bool = False
    supports_streaming: bool = False
    supports_ssml: bool = False
    supports_zero_shot: bool = False
    supports_batch: bool = False
    requires_gpu: bool = False
    gpu_mode: str = "none"          # "none" | "docker" | "host" | "configurable"
    min_samples_for_cloning: int = 0
    max_text_length: int = 5000
    supported_languages: list[str] = field(default_factory=lambda: ["en"])
    supported_output_formats: list[str] = field(default_factory=lambda: ["wav"])
```

### 9. Database Schema

**Tables**: `providers`, `voice_profiles`, `audio_samples`, `training_jobs`, `model_versions`, `synthesis_history`, `api_keys`, `webhooks`, `persona_presets`

Key relationships:
- `voice_profiles` → `providers` (each profile uses one provider)
- `voice_profiles` → `audio_samples` (1:many, training data)
- `voice_profiles` → `model_versions` (1:many, trained models)
- `voice_profiles.active_version_id` → `model_versions` (current active model)
- `training_jobs` → `voice_profiles` + `providers` (tracks each training run)
- `training_jobs.result_version_id` → `model_versions` (output of successful training)

Provider config includes `gpu_mode` field: `"docker_gpu"`, `"host_cpu"`, or `"auto"` (try Docker GPU, fall back to CPU).

### 10. API Endpoints

**Profiles**: `GET/POST /api/v1/profiles`, `GET/PUT/DELETE /api/v1/profiles/{id}`, `GET /api/v1/profiles/{id}/versions`, `POST /api/v1/profiles/{id}/activate-version/{version_id}`

**Samples**: `POST /api/v1/profiles/{id}/samples` (multipart upload), `GET /api/v1/profiles/{id}/samples`, `DELETE /api/v1/profiles/{id}/samples/{sample_id}`, `GET /api/v1/profiles/{id}/samples/{sample_id}/analysis`, `POST /api/v1/profiles/{id}/samples/preprocess`

**Training**: `POST /api/v1/profiles/{id}/train`, `GET /api/v1/training/jobs`, `GET /api/v1/training/jobs/{job_id}`, `POST /api/v1/training/jobs/{job_id}/cancel`, `WS /api/v1/training/jobs/{job_id}/progress`

**Synthesis**: `POST /api/v1/synthesize`, `POST /api/v1/synthesize/stream`, `POST /api/v1/synthesize/batch`, `POST /api/v1/compare`, `GET /api/v1/synthesis/history`

**Providers**: `GET /api/v1/providers`, `GET /api/v1/providers/{name}`, `PUT /api/v1/providers/{name}/config`, `POST /api/v1/providers/{name}/health`, `GET /api/v1/providers/{name}/voices`

**Presets**: `GET/POST /api/v1/presets`, `PUT/DELETE /api/v1/presets/{id}`

**API Keys**: `GET/POST /api/v1/api-keys`, `DELETE /api/v1/api-keys/{id}`

**Webhooks**: `GET/POST /api/v1/webhooks`, `PUT/DELETE /api/v1/webhooks/{id}`, `POST /api/v1/webhooks/{id}/test`

**Utility**: `GET /api/v1/health`, `GET /api/v1/audio/{filename}`

### 11. MCP Server Tools

| Tool | Description |
|------|-------------|
| `atlas_vox_synthesize` | Synthesize text to speech using a voice profile. Returns audio URL or base64. |
| `atlas_vox_list_voices` | List available voice profiles with status and provider info. |
| `atlas_vox_train_voice` | Start training a voice model. Returns job ID for tracking. |
| `atlas_vox_get_training_status` | Get status and progress of a training job. |
| `atlas_vox_manage_profile` | Create, update, or delete a voice profile. |
| `atlas_vox_compare_voices` | Compare multiple voices by synthesizing the same text. |
| `atlas_vox_provider_status` | Check health and capabilities of TTS providers. |

MCP Resources: `atlas-vox://profiles` (voice profile list), `atlas-vox://providers` (provider capabilities)

### 12. Directory Structure

```
atlas-vox/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   ├── profiles.py
│   │   │       │   ├── samples.py
│   │   │       │   ├── training.py
│   │   │       │   ├── synthesis.py
│   │   │       │   ├── compare.py
│   │   │       │   ├── providers.py
│   │   │       │   ├── presets.py
│   │   │       │   ├── api_keys.py
│   │   │       │   ├── webhooks.py
│   │   │       │   ├── health.py
│   │   │       │   └── audio.py
│   │   │       └── router.py
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic Settings
│   │   │   ├── database.py        # SQLAlchemy async engine
│   │   │   ├── security.py        # JWT + API key auth
│   │   │   ├── dependencies.py    # FastAPI deps (get_db, get_current_user)
│   │   │   └── logging.py         # structlog setup
│   │   ├── models/
│   │   │   ├── provider.py
│   │   │   ├── voice_profile.py
│   │   │   ├── audio_sample.py
│   │   │   ├── training_job.py
│   │   │   ├── model_version.py
│   │   │   ├── synthesis_history.py
│   │   │   ├── api_key.py
│   │   │   ├── webhook.py
│   │   │   └── persona_preset.py
│   │   ├── schemas/
│   │   │   ├── profile.py
│   │   │   ├── sample.py
│   │   │   ├── training.py
│   │   │   ├── synthesis.py
│   │   │   ├── provider.py
│   │   │   ├── preset.py
│   │   │   ├── api_key.py
│   │   │   └── webhook.py
│   │   ├── services/
│   │   │   ├── profile_service.py
│   │   │   ├── audio_processor.py     # Shared preprocessing pipeline
│   │   │   ├── training_service.py    # Training orchestration
│   │   │   ├── synthesis_service.py   # Text chunking, concatenation, streaming
│   │   │   ├── comparison_service.py
│   │   │   ├── webhook_dispatcher.py
│   │   │   └── provider_registry.py   # Provider discovery & management
│   │   ├── providers/
│   │   │   ├── base.py                # TTSProvider ABC + ProviderCapabilities
│   │   │   ├── elevenlabs.py
│   │   │   ├── azure_speech.py
│   │   │   ├── coqui_xtts.py
│   │   │   ├── styletts2.py
│   │   │   ├── cosyvoice.py
│   │   │   ├── kokoro_tts.py
│   │   │   ├── piper_tts.py
│   │   │   ├── dia.py                 # Nari-labs Dia (1.6B, dialogue)
│   │   │   └── dia2.py               # Nari-labs Dia2 (2B, streaming)
│   │   ├── mcp/
│   │   │   ├── server.py              # MCP server (JSONRPC 2.0 + SSE)
│   │   │   ├── tools.py               # Tool definitions and handlers
│   │   │   └── transport.py           # SSE transport layer
│   │   ├── cli/
│   │   │   ├── main.py                # Typer app entry point
│   │   │   └── commands/
│   │   │       ├── init.py
│   │   │       ├── train.py
│   │   │       ├── synthesize.py
│   │   │       ├── profiles.py
│   │   │       ├── providers.py
│   │   │       ├── serve.py
│   │   │       ├── compare.py
│   │   │       └── presets.py
│   │   ├── tasks/
│   │   │   ├── celery_app.py          # Celery configuration
│   │   │   ├── training.py            # Training Celery task
│   │   │   └── preprocessing.py       # Audio preprocessing Celery task
│   │   └── main.py                    # FastAPI app with lifespan
│   ├── alembic/
│   │   ├── alembic.ini
│   │   └── versions/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── fixtures/                  # Small WAV files for testing
│   │   ├── test_providers/
│   │   ├── test_api/
│   │   ├── test_services/
│   │   ├── test_mcp/
│   │   └── test_cli/
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── audio/
│   │   │   │   ├── WaveformDisplay.tsx
│   │   │   │   ├── AudioRecorder.tsx
│   │   │   │   └── AudioPlayer.tsx
│   │   │   ├── training/
│   │   │   │   ├── TrainingProgress.tsx
│   │   │   │   └── TrainingConfig.tsx
│   │   │   ├── synthesis/
│   │   │   │   ├── SynthesisControls.tsx
│   │   │   │   ├── SSMLEditor.tsx
│   │   │   │   └── BatchProcessor.tsx
│   │   │   ├── profiles/
│   │   │   │   ├── ProfileCard.tsx
│   │   │   │   ├── ProfileForm.tsx
│   │   │   │   └── SampleUploader.tsx
│   │   │   ├── providers/
│   │   │   │   ├── ProviderCard.tsx
│   │   │   │   └── ProviderConfig.tsx
│   │   │   ├── layout/
│   │   │   │   ├── AppLayout.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── Header.tsx
│   │   │   └── ui/                    # Shared UI primitives
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── ProfilesPage.tsx
│   │   │   ├── TrainingStudioPage.tsx
│   │   │   ├── SynthesisLabPage.tsx
│   │   │   ├── ComparisonPage.tsx
│   │   │   ├── ProvidersPage.tsx
│   │   │   ├── ApiKeysPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   ├── stores/
│   │   │   ├── profileStore.ts
│   │   │   ├── trainingStore.ts
│   │   │   ├── providerStore.ts
│   │   │   ├── synthesisStore.ts
│   │   │   └── authStore.ts
│   │   ├── services/
│   │   │   └── api.ts                 # API client with typed endpoints
│   │   ├── types/
│   │   │   └── index.ts               # All TypeScript interfaces
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts
│   │   │   ├── useAudioRecorder.ts
│   │   │   └── useAudioPlayer.ts
│   │   ├── styles/
│   │   │   └── globals.css
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── Dockerfile.gpu-worker         # GPU-capable Celery worker image
│   ├── docker-compose.yml            # Standard deployment (CPU)
│   └── docker-compose.gpu.yml        # GPU override for local providers
├── storage/                           # Runtime data (gitignored)
│   ├── samples/
│   ├── preprocessed/
│   ├── models/
│   ├── output/
│   └── exports/
├── docs/
│   ├── architecture.md
│   ├── api-reference.md
│   ├── provider-guides/
│   │   ├── elevenlabs.md
│   │   ├── azure-speech.md
│   │   ├── coqui-xtts.md
│   │   ├── styletts2.md
│   │   ├── cosyvoice.md
│   │   ├── kokoro.md
│   │   ├── piper.md
│   │   ├── dia.md
│   │   └── dia2.md
│   ├── mcp-integration.md
│   └── cli-reference.md
├── .env.example
├── .gitignore
├── CLAUDE.md
├── README.md
└── Makefile                           # Common dev commands
```

---

## Implementation Plan (PRP)

### Phase 1: Foundation — Project Scaffolding, Database, Config, First Provider

**Goal**: Working FastAPI server with database, auth, config, and one provider (Kokoro — lightest weight, CPU-only, good for testing without GPU).

**Tasks**:
1. Initialize project structure (pyproject.toml with `[project.scripts]` for `atlas-vox` CLI entry point, frontend package.json, .env.example, .gitignore, Makefile)
2. Implement `core/config.py` — Pydantic Settings loading from .env, including per-provider `gpu_mode` settings
3. Implement `core/logging.py` — structlog with JSON output
4. Implement `core/database.py` — SQLAlchemy async engine, session factory, Base model (aiosqlite default, asyncpg optional)
5. Create all SQLAlchemy models (`models/*.py`) and Alembic initial migration
6. Implement `core/security.py` — API key hashing (Argon2id), JWT create/verify, optional auth toggle (`AUTH_DISABLED=true`)
7. Implement `core/dependencies.py` — `get_db`, `get_current_user` (optional auth)
8. Implement `providers/base.py` — TTSProvider ABC, ProviderCapabilities (with `gpu_mode` field), ProviderHealth dataclasses
9. Implement `providers/kokoro_tts.py` — First provider (synthesize, list_voices, capabilities, health)
10. Implement `services/provider_registry.py` — Discover and manage enabled providers
11. Implement Pydantic v2 schemas for profiles, providers, health
12. Implement `api/v1/endpoints/profiles.py` — Full CRUD
13. Implement `api/v1/endpoints/providers.py` — List, get, configure (including GPU/CPU mode), health check
14. Implement `api/v1/endpoints/health.py` — System health
15. Implement `main.py` — FastAPI app with lifespan, CORS, router mounts
16. Scaffold frontend: Vite + React + TypeScript + Tailwind + Zustand
17. Implement frontend layout shell (AppLayout, Sidebar, Header) and routing

**Verification**: `curl /api/v1/health` returns OK; `curl /api/v1/providers` lists Kokoro; create a profile via API; synthesize text with Kokoro provider.

### Phase 2: Audio Pipeline & Training Infrastructure

**Goal**: Upload audio, preprocess it, queue training jobs, track progress, version models.

**Tasks**:
1. Implement `services/audio_processor.py` — noise reduction (noisereduce), normalization (pydub), silence trimming, format conversion (to WAV 16kHz mono), spectral analysis (pitch, energy via librosa)
2. Implement `api/v1/endpoints/samples.py` — multipart upload (multiple files), list, delete, analysis endpoint
3. Set up Celery + Redis (`tasks/celery_app.py`)
4. Implement `tasks/preprocessing.py` — Celery task for audio preprocessing pipeline
5. Implement `tasks/training.py` — Celery task for provider-specific training dispatch (respects `gpu_mode` config)
6. Implement `services/training_service.py` — Orchestrate preprocessing → training → versioning
7. Implement `api/v1/endpoints/training.py` — Start training, list jobs, get status, cancel
8. Implement WebSocket endpoint for real-time training progress (`/training/jobs/{id}/progress`)
9. Implement model versioning logic (create version on training success, activate version)
10. Implement `providers/coqui_xtts.py` — Voice cloning + fine-tuning (Docker GPU or host CPU mode)
11. Implement `providers/piper_tts.py` — Synthesis + voice listing provider

**Verification**: Upload WAV samples to a profile; trigger preprocessing; start Coqui XTTS training; monitor progress via WebSocket; verify model version created on success.

### Phase 3: All Providers & Full Synthesis Pipeline

**Goal**: All 9 providers implemented; synthesis with text chunking, streaming, batch, and comparison.

**Tasks**:
1. Implement `providers/elevenlabs.py` — Instant cloning, synthesis, streaming, voice design
2. Implement `providers/azure_speech.py` — SSML synthesis, Custom Neural Voice training
3. Implement `providers/styletts2.py` — Zero-shot synthesis, style control (Docker GPU or host CPU)
4. Implement `providers/cosyvoice.py` — Zero-shot multilingual cloning, streaming (Docker GPU or host CPU)
5. Implement `providers/dia.py` — Dia 1.6B dialogue generation with audio conditioning (Docker GPU or host CPU)
6. Implement `providers/dia2.py` — Dia2 2B streaming dialogue generation (Docker GPU or host CPU)
7. Implement `services/synthesis_service.py` — Text chunking for long texts, audio concatenation, streaming orchestration
8. Implement `api/v1/endpoints/synthesis.py` — Single, streaming (chunked transfer), batch synthesis
9. Implement `services/comparison_service.py` — Parallel synthesis across voices/providers
10. Implement `api/v1/endpoints/compare.py` — Side-by-side comparison
11. Implement `api/v1/endpoints/presets.py` — CRUD for persona presets + seed system defaults (Friendly, Professional, Energetic, Calm, Authoritative, Soothing)
12. Implement `api/v1/endpoints/audio.py` — Serve generated audio files
13. Implement `api/v1/endpoints/api_keys.py` — Create, list (masked), revoke API keys

**Verification**: Synthesize text with each of the 9 providers; compare two voices side-by-side; batch-process a 10-line script; verify streaming synthesis with Dia2 and CosyVoice; apply persona preset and hear difference.

### Phase 4: Web UI

**Goal**: Complete React frontend with all 8 pages.

**Tasks**:
1. Implement API client (`services/api.ts`) with typed endpoints, error handling, auth header injection
2. Implement Zustand stores (profileStore, trainingStore, providerStore, synthesisStore, authStore)
3. Build shared UI components (buttons, inputs, cards, modals, badges, dropdowns, toggles)
4. Build audio components: WaveformDisplay (wavesurfer.js), AudioRecorder (MediaRecorder API), AudioPlayer
5. **DashboardPage**: Profile count cards, active training jobs list, provider health grid (9 providers), recent synthesis history
6. **ProfilesPage**: Card grid, create/edit modal, audio upload (drag-drop + in-browser record), status badges, training trigger button
7. **TrainingStudioPage**: Audio recorder, sample list with waveforms, preprocessing toggle, provider-specific training config form (adapts to provider capabilities), WebSocket progress bar
8. **SynthesisLabPage**: Text area with char count, voice dropdown (filtered by ready status), persona/speed/pitch sliders, SSML toggle with Monaco editor, preview with audio player, batch tab
9. **ComparisonPage**: Multi-voice selector, text input, "Generate All" button, side-by-side audio players with latency display
10. **ProvidersPage**: Provider cards with status indicator, config form (API keys masked, GPU/CPU toggle for local providers), health check button, capability badges
11. **ApiKeysPage**: Create key form with scope checkboxes, key list with masked values, revoke button
12. **SettingsPage**: Theme toggle (light/dark), default provider, audio format preferences, webhook config
13. Implement light/dark theme with Tailwind CSS custom properties
14. Implement responsive layout (mobile-friendly)

**Verification**: Navigate all 8 pages; create profile via UI; upload audio with drag-drop; record audio in browser; start training and see live progress; synthesize and play audio; compare two voices; configure a provider with GPU/CPU toggle.

### Phase 5: CLI & MCP Server

**Goal**: Full CLI tool and MCP server for AI agent integration.

**Tasks**:
1. Implement `cli/main.py` — Typer app with Rich console output, entry point as `atlas-vox`
2. Implement `cli/commands/init.py` — Create config file, initialize database, check system dependencies (espeak-ng, Redis, etc.)
3. Implement `cli/commands/profiles.py` — list (Rich table), create (interactive prompts), delete, export/import (JSON)
4. Implement `cli/commands/train.py` — Upload samples from directory, start training, show Rich progress bar with live status
5. Implement `cli/commands/synthesize.py` — TTS with output to file, `--play` flag to play audio immediately
6. Implement `cli/commands/providers.py` — List with health status (Rich table), configure (interactive), GPU/CPU mode toggle
7. Implement `cli/commands/serve.py` — Start uvicorn + optional MCP server (`--mcp` flag)
8. Implement `cli/commands/compare.py` — Synthesize across voices, output Rich comparison table with file paths
9. Implement `cli/commands/presets.py` — List, create, delete
10. Implement `mcp/server.py` — JSONRPC 2.0 handler, tool/resource registration
11. Implement `mcp/tools.py` — All 7 MCP tool handlers (atlas_vox_synthesize, atlas_vox_list_voices, atlas_vox_train_voice, atlas_vox_get_training_status, atlas_vox_manage_profile, atlas_vox_compare_voices, atlas_vox_provider_status)
12. Implement `mcp/transport.py` — SSE transport with API key auth
13. Implement `api/v1/endpoints/webhooks.py` — CRUD for webhook subscriptions
14. Implement `services/webhook_dispatcher.py` — Fire webhooks on training events (HMAC-signed payloads)

**Verification**: `atlas-vox init` creates config; `atlas-vox providers list` shows all 9 providers; `atlas-vox synthesize "Hello" --voice kokoro-default` produces audio; MCP client calls `atlas_vox_synthesize`; webhook fires on training completion.

### Phase 6: Testing, Docker, Documentation, Polish

**Goal**: Comprehensive test coverage, containerized deployment, documentation.

**Tasks**:
1. Write unit tests for all 9 providers (mocked HTTP with httpx/respx)
2. Write unit tests for audio_processor (known WAV fixtures)
3. Write integration tests for all API endpoints (pytest + httpx.AsyncClient + in-memory SQLite)
4. Write MCP protocol compliance tests
5. Write CLI integration tests (Typer test runner)
6. Write Playwright E2E tests for critical UI flows (profile creation, training, synthesis, comparison)
7. Create `docker/Dockerfile.backend` (multi-stage, slim Python image)
8. Create `docker/Dockerfile.frontend` (multi-stage, nginx for static serving)
9. Create `docker/Dockerfile.gpu-worker` (NVIDIA CUDA base image for GPU Celery workers)
10. Create `docker/docker-compose.yml` (backend, frontend, redis, cpu-worker)
11. Create `docker/docker-compose.gpu.yml` (override: adds gpu-worker with NVIDIA runtime)
12. Write `CLAUDE.md` with project conventions for Claude Code agents
13. Write `README.md` with quickstart, architecture overview, provider comparison table
14. Write provider guides (`docs/provider-guides/*.md`) — one per provider with setup, config, and capabilities
15. Write `docs/api-reference.md` (or link to auto-generated OpenAPI at `/docs`)
16. Write `docs/mcp-integration.md` (setup guide for Claude Code / ATLAS integration)
17. Write `docs/cli-reference.md` (all commands with examples)
18. Create `Makefile` with targets: `dev`, `test`, `lint`, `format`, `docker-up`, `docker-gpu-up`, `migrate`, `seed`

**Verification**: `make test` passes all tests; `docker-compose up` starts full stack; `make lint` passes Ruff (backend) + ESLint (frontend); Playwright E2E suite passes; README quickstart steps work on a clean machine.

---

## Key Architectural Decisions

1. **SQLite default + optional PostgreSQL**: Relational data model (profiles → samples → versions) fits SQL perfectly. SQLite is zero-config for dev/single-user; PostgreSQL for production scale.

2. **Celery + Redis for training queue**: Training is GPU-intensive and long-running (minutes to hours). Must not block the API event loop. Celery provides distributed execution, retries, progress tracking.

3. **Provider capability negotiation**: Each provider declares capabilities via `get_capabilities()`. The UI dynamically shows/hides features (e.g., hide "Clone Voice" button for Kokoro which doesn't support it). This avoids hardcoding provider logic in the frontend.

4. **Configurable GPU/CPU per provider**: Local providers can run in Docker GPU containers (pinned CUDA versions, solves sm_120 issues) or host CPU mode. Set per-provider via config. This gives flexibility for different hardware setups.

5. **Shared audio preprocessing pipeline**: All providers benefit from clean, normalized audio. One pipeline (noisereduce + pydub + librosa) runs before any provider-specific training.

6. **Immutable model versions**: Each training run creates a new version. Users A/B compare and roll back. The active version is a pointer on the profile. No destructive updates.

7. **Optional authentication**: `AUTH_DISABLED=true` for single-user/homelab. When enabled, supports JWT (web UI) + API keys (CLI/MCP/external). No mandatory user registration.

8. **MCP as first-class interface**: Not an afterthought — the MCP server is designed alongside the API to ensure AI agents (Claude Code, ATLAS) can fully operate Atlas Vox programmatically.

9. **Dia + Dia2 as separate providers**: Dia (1.6B) excels at high-quality dialogue generation with audio conditioning. Dia2 (2B) adds real-time streaming but with less voice consistency. Users pick based on use case.

---

## Provider-Specific Implementation Notes

### ElevenLabs
- Use official Python SDK (`elevenlabs`)
- Instant Voice Cloning: POST `/voices/ivc/create` with audio + name
- Synthesis: POST `/text-to-speech/{voice_id}` (REST) or WebSocket for streaming
- Store `voice_id` in `model_versions.provider_model_id`

### Azure AI Speech
- Use `azure-cognitiveservices-speech` SDK
- Custom Neural Voice requires Azure portal setup (document in provider guide)
- SSML synthesis via `SpeechSynthesizer` with `SpeakSsmlAsync`
- Personal Voice requires consent recording workflow

### Coqui XTTS v2
- Use `TTS` package from coqui-ai/TTS (community maintained)
- Voice cloning: `tts.tts_to_file(text, speaker_wav=sample_path)`
- Fine-tuning: Use training recipes from the TTS package
- GPU mode: Docker container with CUDA 12.1 + PyTorch 2.1; CPU mode: host Python install

### StyleTTS2
- Clone from yl4579/StyleTTS2 and import as module
- Zero-shot: generate style from diffusion model, no reference needed
- Multi-speaker: requires speaker reference audio
- Requires espeak-ng. Complex setup — document thoroughly in provider guide

### CosyVoice
- Clone from FunAudioLLM/CosyVoice
- `cosyvoice.inference_zero_shot(text, prompt_text, prompt_audio)` for cloning
- Streaming via `inference_zero_shot` generator (150ms latency)
- Multilingual: 9 languages + 18 Chinese dialects

### Kokoro
- `pip install kokoro>=0.9.4`
- `KPipeline(lang_code='a')` for American English
- 54 built-in voices, no cloning capability
- CPU inference works well — great default/fallback provider
- Requires espeak-ng system dependency

### Piper
- `pip install piper-tts` (moved to OHF-Voice/piper1-gpl)
- ONNX models downloaded from Piper model repository
- `piper.synthesize(text)` → WAV bytes
- Ultra-lightweight, Home Assistant compatible
- Custom voice training via separate Piper training pipeline

### Nari-labs Dia (1.6B)
- Install: `pip install git+https://github.com/nari-labs/dia.git`
- Dialogue tags: `[S1]`, `[S2]` for multi-speaker
- Audio conditioning: provide 5-10s reference audio for voice style
- Requires CUDA 12.6+, ~4.4GB VRAM (float16)
- Non-verbal: `(laughs)`, `(sighs)` in text for expressive output

### Nari-labs Dia2 (2B)
- Install from `nari-labs/Dia2-2B` repo
- Streaming generation: begins producing audio after initial words
- Multi-speaker support via `[S1]` and `[S2]` tags
- Requires CUDA 12.8+, GPU acceleration required
- Up to 2 minutes of English output per generation
- Voice quality varies per generation — recommend audio prefixes for consistency

---

## Verification Strategy

### End-to-End Smoke Test
1. `atlas-vox init` → config and database created
2. `atlas-vox providers configure kokoro` → set up Kokoro (no API key needed)
3. `atlas-vox profiles create --name "Test Voice" --provider kokoro` → profile created
4. `atlas-vox synthesize "Hello world" --voice "Test Voice" --output test.wav` → audio file generated
5. `atlas-vox serve --port 8000 --mcp` → server starts
6. `curl http://localhost:8000/api/v1/health` → healthy
7. Open `http://localhost:3000` → Dashboard loads, shows 1 profile, Kokoro healthy
8. In Synthesis Lab: type text, select "Test Voice", click Preview → audio plays
9. MCP client connects to `http://localhost:8000/mcp` → `atlas_vox_list_voices` returns profiles
10. `docker-compose up` → full stack starts from containers

### Test Coverage Targets
- Unit tests: 80%+ coverage on providers, services, schemas
- Integration tests: All API endpoints exercised
- E2E tests: 5 critical flows (profile CRUD, training, synthesis, comparison, provider config)
