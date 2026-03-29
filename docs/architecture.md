# 🏗️ Atlas Vox Architecture

> System architecture, component design, and data flow documentation.

---

## Table of Contents

- [System Overview](#-system-overview)
- [Architecture Diagram](#-architecture-diagram)
- [Component Overview](#-component-overview)
- [Provider Abstraction Pattern](#-provider-abstraction-pattern)
- [Data Flow: Synthesis](#-data-flow-synthesis)
- [Data Flow: Training](#-data-flow-training)
- [Technology Stack](#-technology-stack)
- [Database Schema](#-database-schema)
- [Directory Structure](#-directory-structure)

---

## 🎯 System Overview

Atlas Vox is a modular, self-hosted platform with four entry points (Web UI, REST API, CLI, MCP Server) that all converge on a shared backend layer. The backend orchestrates **9 TTS providers** through a unified abstraction, manages voice profiles and training jobs, and persists data in a relational database.

**Key architectural decisions:**
- **Provider abstraction**: Every TTS engine implements a common `TTSProvider` ABC. The UI adapts dynamically based on each provider's declared capabilities.
- **Async-first**: All backend services use `async def` with SQLAlchemy async and aiosqlite/asyncpg.
- **Background workers**: CPU/GPU-intensive tasks (training, preprocessing) run in Celery workers, keeping the API server responsive.
- **Config-driven**: All settings flow through Pydantic Settings, supporting `.env` files, environment variables, and runtime DB overrides.

---

## 📐 Architecture Diagram

```mermaid
graph TB
    subgraph Clients
        WebUI["Web UI - React + Vite :3100"]
        CLI["CLI - Typer + Rich"]
        API_Client["API Client - curl / SDK"]
        MCP_Client["MCP Client - AI Agents"]
    end

    subgraph Docker["Docker Containers"]
        subgraph Backend["FastAPI Backend :8100"]
            Router["API Router - 12 endpoint modules"]
            MCP["MCP Server - JSONRPC 2.0 + SSE"]
            Services["Service Layer - 7 services"]
            Registry["Provider Registry"]
        end

        subgraph Providers["TTS Providers (9)"]
            Cloud["Cloud - ElevenLabs, Azure Speech"]
            LocalCPU["Local CPU - Kokoro, Piper"]
            LocalGPU["Local GPU - Coqui XTTS, StyleTTS2, CosyVoice, Dia, Dia2"]
        end

        subgraph Storage
            DB[("SQLite / PostgreSQL - 9 tables")]
            FileStore["File Storage - ./storage/"]
            Redis["Redis - Celery Broker"]
        end

        subgraph Workers
            CeleryWorker["Celery Worker - Training + Preprocessing"]
            GPUWorker["GPU Worker - CUDA 12.1"]
        end
    end

    WebUI -->|HTTP/WS| Router
    CLI -->|HTTP| Router
    API_Client -->|HTTP| Router
    MCP_Client -->|SSE| MCP

    Router --> Services
    MCP --> Services
    Services --> Registry
    Services --> DB
    Services --> FileStore
    Services --> Redis

    Registry --> Cloud
    Registry --> LocalCPU
    Registry --> LocalGPU

    Redis --> CeleryWorker
    Redis --> GPUWorker
    CeleryWorker --> DB
    CeleryWorker --> FileStore
    GPUWorker --> DB
    GPUWorker --> FileStore
```

### ASCII Architecture Diagram

```
+------ Docker Containers -----------------------------------------+
|                                                                   |
|  Web UI :3100   ----+                                            |
|  CLI (Typer)    ----+---> FastAPI Backend :8100                  |
|  API Client     ----+      |                                     |
|  MCP Client     ----+      +---> Provider Registry               |
|                             |      |                              |
|                             |      +---> Cloud (ElevenLabs, Azure)|
|                             |      +---> CPU (Kokoro, Piper)      |
|                             |      +---> GPU (Coqui, StyleTTS2...)|
|                             |                                     |
|  Redis :6379 <-- Celery --> Worker                               |
|  SQLite / PG                                                     |
+------------------------------------------------------------------+
```

---

## 🧩 Component Overview

### Frontend (React + TypeScript)

| Component | Purpose |
|-----------|---------|
| **Pages** (9+) | Lazy-loaded route components: Dashboard, Profiles, Library, Training, Synthesis, Comparison, Providers, API Keys, Settings, Help, Docs |
| **Stores** (5+) | Zustand state stores: profiles, providers, training, synthesis, voice library, settings, admin |
| **Services** | Typed API client (`api.ts`) with 30+ methods |
| **Components** (40+) | UI primitives (Card, Button, Modal, Badge), audio components (AudioPlayer, AudioRecorder), layout (Sidebar, AppLayout) |
| **Hooks** | WebSocket hook for training progress, audio playback hooks |

### Backend (FastAPI + Python)

| Layer | Purpose |
|-------|---------|
| **API Endpoints** (12 modules) | REST routes organized by resource: health, profiles, providers, voices, samples, training, synthesis, compare, audio, presets, api_keys, webhooks |
| **Services** (7) | Business logic: `profile_service`, `synthesis_service`, `training_service`, `comparison_service`, `audio_processor`, `provider_registry`, `webhook_dispatcher` |
| **Providers** (9) | TTS engine implementations extending `TTSProvider` ABC |
| **Models** (9) | SQLAlchemy async ORM: VoiceProfile, AudioSample, TrainingJob, ModelVersion, PersonaPreset, SynthesisHistory, ApiKey, Webhook, Provider |
| **Schemas** | Pydantic v2 request/response schemas with validation |
| **Tasks** | Celery background tasks: `training.py`, `preprocessing.py` |
| **Core** | Config (Pydantic Settings), Database, Security, Logging, Dependencies |

### Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Database** | SQLite (dev) / PostgreSQL (prod) | Persistent storage |
| **Cache/Broker** | Redis 7 | Celery task broker, result backend |
| **Worker** | Celery 5 | Background training and preprocessing |
| **Proxy** | Nginx | Frontend serving, API reverse proxy |

---

## 🔌 Provider Abstraction Pattern

The provider abstraction is the core architectural pattern in Atlas Vox. It allows the system to treat all TTS engines uniformly while adapting the UI based on each provider's capabilities.

### TTSProvider ABC

```python
class TTSProvider(ABC):
    """Abstract base for all TTS providers."""

    @abstractmethod
    async def synthesize(self, text, voice_id, settings) -> AudioResult: ...

    @abstractmethod
    async def clone_voice(self, samples, config) -> VoiceModel: ...

    @abstractmethod
    async def fine_tune(self, model_id, samples, config) -> VoiceModel: ...

    @abstractmethod
    async def list_voices(self) -> list[VoiceInfo]: ...

    @abstractmethod
    async def get_capabilities(self) -> ProviderCapabilities: ...

    @abstractmethod
    async def health_check(self) -> ProviderHealth: ...

    async def stream_synthesize(self, text, voice_id, settings) -> AsyncIterator[bytes]:
        raise NotImplementedError("Streaming not supported")
```

### ProviderCapabilities

Each provider declares its capabilities via a dataclass. The frontend reads these to adapt the UI dynamically:

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
    gpu_mode: str = "none"
    min_samples_for_cloning: int = 0
    max_text_length: int = 5000
    supported_languages: list[str] = field(default_factory=lambda: ["en"])
    supported_output_formats: list[str] = field(default_factory=lambda: ["wav"])
```

### Provider Registry

The `ProviderRegistry` manages provider lifecycle:

```mermaid
graph LR
    A[App Startup] --> B[seed_providers]
    B --> C[load_provider_configs]
    C --> D[Registry Ready]
    D --> E[get_provider]
    D --> F[health_check]
    D --> G[get_capabilities]
    D --> H[list_available]
    D --> I[apply_config]
```

- **Seed**: Ensures all providers exist in the database
- **Load configs**: Merges env vars, DB config, and runtime overrides
- **Runtime**: Providers are instantiated lazily and configured on demand

### Configuration Layering

Provider configuration merges from three sources (later overrides earlier):

```
1. Schema defaults (Pydantic model defaults)
2. Database config (stored in provider.config_json)
3. Runtime overrides (env vars, API calls)
```

Secret fields (API keys) are masked with `****` in API responses and preserved when the masked value is sent back.

### All 9 Providers

| # | Provider | Type | Module | Runtime |
|---|----------|------|--------|---------|
| 1 | Kokoro | Local CPU | `kokoro_tts.py` | Docker |
| 2 | Piper | Local CPU | `piper_tts.py` | Docker |
| 3 | ElevenLabs | Cloud | `elevenlabs.py` | Docker |
| 4 | Azure Speech | Cloud | `azure_speech.py` | Docker |
| 5 | Coqui XTTS v2 | Local GPU | `coqui_xtts.py` | Docker |
| 6 | StyleTTS2 | Local GPU | `styletts2.py` | Docker |
| 7 | CosyVoice | Local GPU | `cosyvoice.py` | Docker |
| 8 | Dia | Local GPU | `dia.py` | Docker |
| 9 | Dia2 | Local GPU | `dia2.py` | Docker |

---

## 🔊 Data Flow: Synthesis

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant Service as SynthesisService
    participant Registry as ProviderRegistry
    participant Provider as TTSProvider
    participant Storage as File Storage
    participant DB

    Client->>API: POST /synthesize
    API->>Service: synthesize(text, profile_id, ...)
    Service->>DB: Get profile + active version
    Service->>Registry: get_provider(profile.provider_name)
    Registry-->>Service: provider instance
    Service->>Provider: synthesize(text, voice_id, settings)
    Provider->>Storage: Write audio file
    Provider-->>Service: AudioResult(path, duration)
    Service->>DB: Save SynthesisHistory
    Service-->>API: audio_url, latency_ms
    API-->>Client: 200 OK + JSON
```

**Key points:**
- Profile determines which provider and voice to use
- Active model version (if any) is passed as the voice ID
- Audio files are saved to `storage/output/`
- Each synthesis is recorded in `synthesis_history` table

---

## 🎓 Data Flow: Training

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant Service as TrainingService
    participant Celery as Celery Task
    participant Worker as Celery Worker
    participant Provider as TTSProvider
    participant DB
    participant WS as WebSocket

    Client->>API: POST /profiles/{id}/train
    API->>Service: start_training(profile_id, ...)
    Service->>DB: Create TrainingJob (status=queued)
    Service->>Celery: Dispatch training task
    Service-->>API: TrainingJob
    API-->>Client: 201 Created

    Client->>WS: Connect /training/jobs/{id}/progress

    Worker->>DB: Update status=preprocessing
    Worker->>Provider: Preprocess samples
    Worker->>DB: Update status=training
    Worker->>Provider: clone_voice / fine_tune
    Provider-->>Worker: VoiceModel
    Worker->>DB: Create ModelVersion
    Worker->>DB: Update job completed
    Worker->>DB: Update profile ready

    WS-->>Client: Progress frames (1s poll)
    WS-->>Client: Final frame (DONE)
```

**Key points:**
- Training is asynchronous via Celery
- WebSocket provides real-time progress updates
- Each successful training creates a new ModelVersion
- Profile status transitions: pending -> training -> ready (or error)

---

## 🛠️ Technology Stack

### Backend

| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Runtime |
| FastAPI | 0.115+ | Web framework |
| Pydantic | v2 | Validation and settings |
| SQLAlchemy | 2.0+ (async) | ORM |
| aiosqlite | 0.20+ | Async SQLite driver |
| Alembic | 1.13+ | Database migrations |
| Celery | 5.3+ | Background task queue |
| Redis | 5.0+ | Celery broker |
| structlog | 24.0+ | Structured logging |
| python-jose | 3.3+ | JWT authentication |
| argon2-cffi | 23.1+ | Password/API key hashing |

### Frontend

| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 18+ | UI framework |
| TypeScript | 5+ | Type safety |
| Vite | 5+ | Build tool |
| Tailwind CSS | 3+ | Styling |
| Zustand | Latest | State management |
| Sonner | Latest | Toast notifications |
| Lucide React | Latest | Icons |
| React Router | v6 | Client-side routing |

### Infrastructure

| Technology | Purpose |
|-----------|---------|
| Docker | Containerization |
| Docker Compose | Service orchestration |
| Nginx | Frontend serving, reverse proxy |
| NVIDIA Container Toolkit | GPU passthrough |
| CUDA 12.1 | GPU compute |

---

## 🗄️ Database Schema

```mermaid
erDiagram
    voice_profiles ||--o{ audio_samples : has
    voice_profiles ||--o{ training_jobs : has
    voice_profiles ||--o{ model_versions : has
    voice_profiles ||--o{ synthesis_history : has

    voice_profiles {
        string id PK
        string name
        string description
        string language
        string provider_name
        string status
        string tags_json
        string active_version_id FK
        datetime created_at
        datetime updated_at
    }

    audio_samples {
        string id PK
        string profile_id FK
        string filename
        string original_filename
        string file_path
        string format
        int file_size_bytes
        float duration_seconds
        int sample_rate
        boolean preprocessed
        string preprocessed_path
        string analysis_json
        datetime created_at
    }

    training_jobs {
        string id PK
        string profile_id FK
        string provider_name
        string status
        float progress
        string celery_task_id
        string error_message
        string result_version_id FK
        datetime started_at
        datetime completed_at
        datetime created_at
        datetime updated_at
    }

    model_versions {
        string id PK
        string profile_id FK
        int version_number
        string provider_model_id
        string model_path
        string config_json
        string metrics_json
        datetime created_at
    }

    persona_presets {
        string id PK
        string name
        string description
        float speed
        float pitch
        float volume
        boolean is_system
        datetime created_at
    }

    synthesis_history {
        string id PK
        string profile_id FK
        string provider_name
        string text
        string output_path
        string output_format
        float duration_seconds
        int latency_ms
        datetime created_at
    }

    api_keys {
        string id PK
        string name
        string key_hash
        string key_prefix
        string scopes
        boolean active
        datetime created_at
        datetime last_used_at
    }

    webhooks {
        string id PK
        string url
        string events
        string secret
        boolean active
        datetime created_at
    }

    providers {
        string id PK
        string name
        string display_name
        string provider_type
        boolean enabled
        string gpu_mode
        string config_json
        datetime created_at
        datetime updated_at
    }
```

---

## 📁 Directory Structure

```
atlas-vox/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/       # 12 API endpoint modules (60+ routes)
│   │   ├── core/                   # Config, Database, Security, Logging
│   │   ├── models/                 # 9 SQLAlchemy ORM models
│   │   ├── schemas/                # Pydantic v2 request/response schemas
│   │   ├── services/               # 7 business logic services
│   │   ├── providers/              # 9 TTS provider implementations
│   │   ├── tasks/                  # Celery background tasks
│   │   ├── cli/                    # Typer CLI commands
│   │   ├── mcp/                    # MCP server (JSONRPC 2.0)
│   │   └── main.py                 # FastAPI app entry point
│   ├── tests/                      # Pytest suite (43+ tests)
│   ├── migrations/                 # Alembic migrations
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/                  # 11 lazy-loaded React pages
│   │   ├── components/             # 40+ UI, audio, layout components
│   │   ├── stores/                 # 5+ Zustand state stores
│   │   ├── services/               # Typed API client (api.ts)
│   │   ├── hooks/                  # WebSocket, audio hooks
│   │   ├── data/                   # Static data (providerMetadata)
│   │   └── types/                  # TypeScript interfaces
│   └── package.json
├── docker/                         # Dockerfiles + compose configs
├── docs/                           # Documentation
├── Makefile                        # Development commands
└── CLAUDE.md                       # Project instructions
```

---

<div align="center">

[Back to User Guide](USER_GUIDE.md) | [API Reference](API_REFERENCE.md) | [Deployment Guide](DEPLOYMENT.md)

</div>
