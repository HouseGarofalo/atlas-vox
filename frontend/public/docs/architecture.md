# Architecture

## System Overview

Atlas Vox is a modular voice platform with 4 access interfaces, 9 TTS providers, and a complete training pipeline backed by Celery workers.

```
  +---------------------------+     +---------------------------+
  |        Frontend           |     |          CLI              |
  |   React 18 + TypeScript   |     |    Typer + Rich           |
  |   Tailwind + Zustand      |     |    atlas-vox <command>    |
  +------------+--------------+     +------------+--------------+
               |                                 |
               |  HTTP / WebSocket               |  HTTP
               v                                 v
  +----------------------------------------------------------+
  |                   Backend (FastAPI)                       |
  |  +-----------+  +-----------+  +----------+  +---------+ |
  |  | REST API  |  | WebSocket |  | MCP/SSE  |  | OpenAI  | |
  |  | /api/v1/* |  | /ws       |  | /mcp/sse |  | Compat  | |
  |  +-----------+  +-----------+  +----------+  +---------+ |
  |                                                          |
  |  +----------------------------------------------------+  |
  |  |              Service Layer                         |  |
  |  |  synthesis_service  |  training_service            |  |
  |  |  profile_service    |  comparison_service          |  |
  |  |  audio_processor    |  webhook_dispatcher          |  |
  |  +----------------------------------------------------+  |
  |                                                          |
  |  +----------------------------------------------------+  |
  |  |           Provider Abstraction Layer                |  |
  |  |  TTSProvider ABC -> get_capabilities() -> UI adapts |  |
  |  |  9 providers: kokoro, piper, elevenlabs, azure,     |  |
  |  |  coqui_xtts, styletts2, cosyvoice, dia, dia2       |  |
  |  +----------------------------------------------------+  |
  +---------------------------+------------------------------+
                              |
                +-------------+-------------+
                |                           |
  +-------------v---------+   +-------------v---------+
  |   SQLite / PostgreSQL |   |     Redis (db 1)      |
  |   10 tables           |   |   Celery broker        |
  |   async via aiosqlite |   |   Cache + pub/sub      |
  +-----------------------+   +-----------------------+
                                        |
                              +---------v---------+
                              |   Celery Worker    |
                              |   Training jobs    |
                              |   Preprocessing    |
                              +-------------------+
```

---

## Component Descriptions

### Backend (FastAPI)

Python 3.11+ async web framework. Handles REST API, WebSocket connections, MCP server, and OpenAI-compatible endpoints. Uses Pydantic v2 for validation and structlog for structured logging.

### Frontend (React)

React 18 with TypeScript, Vite bundler, Tailwind CSS for styling, Zustand for state management. Features wavesurfer.js for audio visualization and Monaco Editor for SSML editing.

### CLI (Typer)

Command-line interface built with Typer and Rich. Provides synthesize, train, compare, and provider management commands. Entry point: `atlas-vox`.

### MCP Server (JSONRPC 2.0)

Model Context Protocol server with SSE transport. Exposes 9 tools and 2 resources for AI assistant integration. Connects via `/mcp/sse` endpoint.

### Celery Worker (Redis)

Background task processor for training jobs, audio preprocessing, and model fine-tuning. Uses Redis as broker and result backend. Never blocks the FastAPI event loop.

---

## Data Flow

```
Request Flow (Synthesis):
  Client Request
    -> FastAPI Router (/api/v1/synthesize)
      -> Dependency Injection (get_db, get_current_user)
        -> SynthesisService.synthesize()
          -> ProviderRegistry.get_provider(name)
            -> TTSProvider.synthesize(text, voice, params)
              -> Audio bytes returned
          -> Save to storage/audio/
          -> Record in synthesis_history table
        -> Return {audio_url, latency_ms, provider, voice}

Request Flow (Training):
  Client Request
    -> FastAPI Router (/api/v1/training)
      -> TrainingService.start_training()
        -> Create training_job record (status: queued)
        -> Dispatch Celery task
          -> Celery Worker picks up job
            -> Preprocessing (noise reduction, normalization)
            -> Provider-specific fine-tuning
            -> Save model weights
            -> Update job status (completed/failed)
          -> WebSocket notification to client
```

---

## Database Schema

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `voice_profiles` | id, name, provider_name, voice_id, language, status | Voice identities bound to providers |
| `training_jobs` | id, profile_id, provider_name, status, progress, error | Training job tracking |
| `model_versions` | id, profile_id, version, model_path, metrics | Trained model versions |
| `audio_samples` | id, profile_id, file_path, duration, format, preprocessed | Training audio samples |
| `synthesis_history` | id, profile_id, text, audio_url, latency_ms, provider | Synthesis request log |
| `api_keys` | id, key_hash, name, scopes, expires_at, revoked | API key management |
| `presets` | id, name, speed, pitch, volume, provider_name | Persona presets |
| `provider_configs` | id, provider_name, config_json, enabled | Per-provider settings |
| `webhook_subscriptions` | id, url, events, secret, active | Webhook delivery config |
| `healing_incidents` | id, severity, category, title, action_taken, outcome | Self-healing event log |

---

## Provider Abstraction Pattern

All TTS providers implement the `TTSProvider` abstract base class. Each provider declares its capabilities via `get_capabilities()`, and the frontend dynamically adapts the UI based on what each provider supports.

```python
# backend/app/providers/base.py

class TTSProvider(ABC):
    """Abstract base class for all TTS providers."""

    @abstractmethod
    async def synthesize(self, text: str, voice_id: str, **params) -> bytes:
        """Synthesize text to audio bytes."""

    @abstractmethod
    async def get_voices(self) -> list[Voice]:
        """List available voices."""

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Check provider health."""

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Declare provider capabilities."""
        # Returns: { ssml, streaming, voice_cloning, languages, ... }

# The ProviderRegistry discovers and manages all providers:
#   registry.get_provider("kokoro")  -> KokoroProvider instance
#   registry.get_all_healthy()       -> list of healthy providers
#   registry.get_capabilities("dia") -> { dialogue: true, ... }
```
