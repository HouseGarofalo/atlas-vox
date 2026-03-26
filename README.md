<div align="center">

# Atlas Vox

### Intelligent Voice Training & Customization Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![React 18](https://img.shields.io/badge/react-18-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![TypeScript](https://img.shields.io/badge/typescript-5.5-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

**9 TTS providers** &middot; **4 interfaces** &middot; **Full training pipeline** &middot; **Self-hosted**

[Quick Start](#-quick-start) &middot; [Architecture](#-architecture) &middot; [Providers](#-tts-providers) &middot; [API Docs](docs/API.md) &middot; [CLI Docs](docs/CLI.md) &middot; [Deployment](#-deployment)

</div>

---

## Overview

Atlas Vox is a self-hosted platform for training custom voice models and synthesizing speech across 9 TTS engines. It provides a unified interface to cloud providers (ElevenLabs, Azure) and local open-source models (Kokoro, Piper, Coqui XTTS v2, StyleTTS2, CosyVoice, Dia, Dia2) with voice cloning, fine-tuning, and real-time streaming.

### Key Features

| Feature | Description |
|---------|-------------|
| **Voice Profiles** | Create identities bound to any provider, track training versions |
| **Audio Training** | Upload samples, preprocess (noise reduction, normalization), train models via Celery |
| **Real-time Synthesis** | Text-to-speech with speed/pitch/volume control and SSML support |
| **Voice Comparison** | Side-by-side synthesis across multiple profiles |
| **Persona Presets** | Reusable voice personas (Friendly, Professional, Energetic, etc.) |
| **4 Interfaces** | Web UI, REST API, CLI, MCP Server |
| **GPU Flexibility** | Per-provider GPU mode: Docker GPU, host CPU, or auto-detect |
| **API Key Management** | Scoped keys (read/write/synthesize/train/admin) with Argon2id hashing |
| **Webhook Events** | HMAC-signed delivery for training.completed / training.failed |

---

## Tech Stack

```
Backend              Frontend             Infrastructure
-------              --------             --------------
Python 3.11+         React 18             Docker Compose
FastAPI 0.115        TypeScript 5         Redis (Celery broker)
SQLAlchemy 2.0       Vite 5               SQLite / PostgreSQL
Pydantic v2          Tailwind CSS 3       Nginx (production)
Celery 5             Zustand              Alembic (migrations)
structlog            Sonner               Argon2id (security)
Typer + Rich         Lucide React         HMAC-SHA256 (webhooks)
```

---

## Quick Start

### Prerequisites

- Python 3.11+ and Node.js 20+
- Redis (for background training jobs) &mdash; optional for basic synthesis

### 1. Clone & Install

```bash
git clone https://github.com/HouseGarofalo/atlas-vox.git
cd atlas-vox
make install
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env to add provider API keys (ElevenLabs, Azure) if needed
# SQLite works out of the box - no database setup required
```

### 3. Run

```bash
make dev
```

| Service | URL |
|---------|-----|
| Web UI | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

### Docker (Full Stack)

```bash
make docker-up        # CPU mode
make docker-gpu-up    # With NVIDIA GPU support
```

---

## Architecture

```
                                  +------------------+
                                  |    Web UI :3000   |
                                  |  React + Vite     |
                                  +--------+---------+
                                           |
                                           v
+----------+     +------------------+   +-----------+   +------------------+
|  CLI      +---->                  |   |           |   |                  |
| (Typer)   |    |  FastAPI :8000   +-->+ SQLite /  |   |  Redis :6379     |
+----------+     |                  |   | PostgreSQL|   |  (Celery broker) |
                 |  11 API routers  |   |           |   +--------+---------+
+----------+     |  60+ endpoints   |   +-----------+            |
| MCP Server+--->|  WebSocket       |                            v
| (JSONRPC) |    +--+--------+-----+                   +---------+---------+
+----------+        |        |                         |  Celery Worker    |
                    v        v                         |  Training tasks   |
             +------+--+ +---+--------+                |  Preprocessing    |
             | Provider| | Provider   |                +-------------------+
             | Registry| | Storage    |
             | (9 TTS) | | ./storage  |
             +---------+ +------------+
```

### Training Pipeline

```
Upload audio --> Preprocess (noise reduction, normalize, resample 16kHz)
             --> Analysis (pitch, energy, spectral via librosa)
             --> Train (Celery task, provider-specific)
             --> Model Version created
             --> Profile status: ready --> Synthesis available
```

---

## TTS Providers

9 providers ship out of the box. Each extends `TTSProvider` ABC and declares capabilities dynamically &mdash; the UI adapts automatically.

| Provider | Type | Cloning | Stream | SSML | GPU | Languages | Notes |
|----------|------|:-------:|:------:|:----:|-----|-----------|-------|
| **Kokoro** | Local | | | | CPU | en | 82M params, 54 voices, ultra-fast |
| **Piper** | Local | | | | CPU | 30+ | ONNX, Home Assistant compatible |
| **ElevenLabs** | Cloud | :white_check_mark: | :white_check_mark: | | &mdash; | 29 | Premium quality, instant cloning |
| **Azure Speech** | Cloud | :white_check_mark: | :white_check_mark: | :white_check_mark: | &mdash; | 140+ | Enterprise SSML, CNV |
| **Coqui XTTS v2** | Local | :white_check_mark: | :white_check_mark: | | Cfg | 17 | Clone from 6s audio |
| **StyleTTS2** | Local | :white_check_mark: | | | Cfg | en | Zero-shot, style diffusion |
| **CosyVoice** | Local | :white_check_mark: | :white_check_mark: | | Cfg | 9 | 150ms streaming latency |
| **Dia** | Local | :white_check_mark: | | | Cfg | en | 1.6B param dialogue model |
| **Dia2** | Local | | :white_check_mark: | | Cfg | en | 2B param streaming dialogue |

**GPU Modes** (`Cfg` = configurable per provider):

| Mode | Variable Example | Description |
|------|-----------------|-------------|
| `host_cpu` | `COQUI_XTTS_GPU_MODE=host_cpu` | Run on host CPU (default) |
| `docker_gpu` | `COQUI_XTTS_GPU_MODE=docker_gpu` | NVIDIA GPU in Docker |
| `auto` | `COQUI_XTTS_GPU_MODE=auto` | Auto-detect, fallback CPU |

> See [docs/PROVIDERS.md](docs/PROVIDERS.md) for per-provider setup guides.

---

## Web UI

8 pages accessible via sidebar navigation with full light/dark theme and mobile-responsive layout.

| Page | Route | Purpose |
|------|-------|---------|
| **Dashboard** | `/` | Stats, provider health, active jobs, recent synthesis |
| **Voice Profiles** | `/profiles` | Create, manage, delete voice identities |
| **Training Studio** | `/training` | Upload audio, record, preprocess, train models |
| **Synthesis Lab** | `/synthesis` | Text-to-speech with parameter controls + presets |
| **Comparison** | `/compare` | Side-by-side multi-voice comparison |
| **Providers** | `/providers` | View all 9 providers with capabilities and health |
| **API Keys** | `/api-keys` | Create/revoke scoped API keys |
| **Settings** | `/settings` | Theme toggle, default provider, audio format |

---

## Database

**Default**: SQLite (zero config, auto-created at `./atlas_vox.db`)
**Production**: PostgreSQL via `DATABASE_URL=postgresql+asyncpg://...`

### Schema (9 tables)

```
voice_profiles ──┬── audio_samples
                 ├── model_versions
                 └── training_jobs

persona_presets     synthesis_history     api_keys
webhooks            providers
```

> See [docs/DATABASE.md](docs/DATABASE.md) for full schema reference.

---

## Configuration

All settings via `.env` file or environment variables. See [`.env.example`](.env.example) for the complete template.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./atlas_vox.db` | Database connection |
| `AUTH_DISABLED` | `true` | Skip auth (homelab mode) |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker |
| `STORAGE_PATH` | `./storage` | Audio & model storage |
| `ELEVENLABS_API_KEY` | *(empty)* | ElevenLabs cloud API |
| `AZURE_SPEECH_KEY` | *(empty)* | Azure AI Speech key |

> See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for all 25+ variables.

---

## Deployment

### Docker Compose (Recommended)

```bash
make docker-up        # Backend, frontend, Redis, Celery worker
make docker-gpu-up    # Same + NVIDIA GPU passthrough
```

### Production Checklist

- [ ] Set `APP_ENV=production` and `DEBUG=false`
- [ ] Generate strong `JWT_SECRET_KEY`
- [ ] Set `AUTH_DISABLED=false`
- [ ] Switch to PostgreSQL
- [ ] Run `alembic upgrade head`
- [ ] Configure CORS for your domain
- [ ] Set provider API keys
- [ ] Configure Redis persistence

---

## Development

```bash
make dev          # Start backend + frontend dev servers
make test         # Run pytest (43+ tests)
make test-cov     # Tests with coverage report
make lint         # Ruff (Python) + ESLint (TypeScript)
make format       # Auto-format all code
make migrate      # Run Alembic migrations
make clean        # Remove caches and build artifacts
```

### Project Structure

```
atlas-vox/
  backend/
    app/
      api/v1/endpoints/   # 11 API endpoint modules (60+ routes)
      core/               # Config, database, security, logging
      models/             # 9 SQLAlchemy async ORM models
      schemas/            # Pydantic v2 request/response schemas
      services/           # 7 business logic services
      providers/          # 9 TTS provider implementations
      tasks/              # Celery background tasks (training, preprocessing)
      cli/                # Typer CLI with 7 command groups
      mcp/                # MCP server (JSONRPC 2.0 + SSE)
    tests/                # Pytest suite (43+ tests)
    alembic/              # Database migrations
  frontend/
    src/
      pages/              # 8 lazy-loaded React pages
      components/         # 40+ UI, audio, layout components
      stores/             # 5 Zustand state stores
      services/           # Typed API client (30+ methods)
      hooks/              # WebSocket, audio hooks
      types/              # TypeScript interfaces
  docker/                 # Dockerfiles + compose configs
  docs/                   # Extended documentation
```

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [docs/API.md](docs/API.md) | Complete API reference with request/response examples |
| [docs/DATABASE.md](docs/DATABASE.md) | Full schema, relationships, and migration guide |
| [docs/PROVIDERS.md](docs/PROVIDERS.md) | Per-provider setup, capabilities, and GPU configuration |
| [docs/CLI.md](docs/CLI.md) | CLI command reference |
| [docs/MCP.md](docs/MCP.md) | MCP server tools, resources, and integration guide |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | All environment variables and settings |
| [docs/FRONTEND.md](docs/FRONTEND.md) | Component architecture, stores, routing |
| [docs/SECURITY.md](docs/SECURITY.md) | Authentication, API keys, CORS, webhook signing |

---

<div align="center">

Built with FastAPI, React, and 9 TTS engines

</div>
