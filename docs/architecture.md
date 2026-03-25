# Atlas Vox — Architecture

## System Overview

Atlas Vox is a self-hosted voice training and customization platform supporting 9 TTS providers, 4 interfaces, and a complete training pipeline.

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Web UI     │  │    CLI       │  │  REST API    │  │  MCP Server  │
│  (React)     │  │  (Typer)     │  │  (FastAPI)   │  │ (JSONRPC 2.0)│
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │                 │
       └─────────────────┴────────┬────────┴─────────────────┘
                                  │
                          ┌───────▼───────┐
                          │  FastAPI App   │
                          │  (async)       │
                          └───────┬───────┘
                    ┌─────────────┼──────────────┐
              ┌─────▼─────┐ ┌────▼─────┐ ┌──────▼──────┐
              │ Services  │ │ Provider │ │   Celery    │
              │ Layer     │ │ Registry │ │   Workers   │
              └─────┬─────┘ └────┬─────┘ └──────┬──────┘
                    │            │               │
              ┌─────▼─────┐ ┌───▼────────┐ ┌────▼─────┐
              │ SQLAlchemy│ │ 9 TTS      │ │  Redis   │
              │ (async)   │ │ Providers  │ │ (broker) │
              └─────┬─────┘ └────────────┘ └──────────┘
                    │
              ┌─────▼─────┐
              │  SQLite/   │
              │ PostgreSQL │
              └────────────┘
```

## Key Components

### Backend (Python)
- **FastAPI** — async HTTP server, OpenAPI docs auto-generated
- **SQLAlchemy 2.0** — async ORM with aiosqlite/asyncpg
- **Celery + Redis** — distributed task queue for training/preprocessing
- **Provider Registry** — pluggable TTS provider system with capability discovery

### Frontend (React)
- **Vite** — build tool with HMR
- **Zustand** — lightweight state management (1 store per domain)
- **Tailwind CSS** — utility-first styling with light/dark theme
- **wavesurfer.js** — audio waveform visualization

### 9 TTS Providers

| Provider | Type | Cloning | Streaming | GPU |
|----------|------|---------|-----------|-----|
| Kokoro | Local | No | No | CPU only |
| Piper | Local | No | No | CPU only |
| Coqui XTTS v2 | Local | Yes (6s) | Yes | Configurable |
| StyleTTS2 | Local | Yes (zero-shot) | No | Configurable |
| CosyVoice | Local | Yes (zero-shot) | Yes | Configurable |
| Dia (1.6B) | Local | Yes (conditioning) | No | Configurable |
| Dia2 (2B) | Local | No | Yes | Configurable |
| ElevenLabs | Cloud | Yes | Yes | N/A |
| Azure Speech | Cloud | Yes (CNV) | Yes | N/A |

## Data Flow

### Training Pipeline
```
Upload Audio → Preprocess (noise/normalize/resample) → Queue Celery Task
→ Provider Training (clone/fine-tune) → Create Model Version → Activate
```

### Synthesis Pipeline
```
Text Input → Resolve Profile/Version → Split Text (chunking)
→ Provider Synthesis → Format Conversion → Save History → Return Audio URL
```

## Database Schema
- `voice_profiles` — voice identity with provider/language/status
- `audio_samples` — uploaded training audio with preprocessing metadata
- `training_jobs` — Celery task tracking with progress
- `model_versions` — immutable training outputs with metrics
- `synthesis_history` — audit log of all synthesis operations
- `persona_presets` — speed/pitch/volume presets
- `api_keys` — Argon2id hashed API keys with scoped permissions
- `webhooks` — event subscriptions with HMAC-signed delivery
- `providers` — provider configuration and state
