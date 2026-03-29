<div align="center">

# Atlas Vox

### Intelligent Voice Training & Customization Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![React 18](https://img.shields.io/badge/react-18-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![TypeScript](https://img.shields.io/badge/typescript-5.5-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Redis](https://img.shields.io/badge/redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![Tailwind CSS](https://img.shields.io/badge/tailwind-3-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

**9 TTS providers** &middot; **4 interfaces** &middot; **OpenAI-compatible API** &middot; **Self-hosted**

[Quick Start](#-quick-start) &middot; [Features](#-features) &middot; [Providers](#-tts-providers) &middot; [Documentation](#-documentation) &middot; [Architecture](#-architecture)

</div>

---

## Overview

Atlas Vox is a self-hosted platform for training custom voice models and synthesizing speech across **9 TTS engines**. It provides a unified interface to cloud providers (ElevenLabs, Azure) and local open-source models (Kokoro, Piper, Coqui XTTS v2, StyleTTS2, CosyVoice, Dia, Dia2). Features include voice cloning, an OpenAI-compatible API (`/v1/audio/speech`), an MCP server with 9 tools for AI agent integration, real-time streaming, and a full design system for UI customization.

All data stays on your machine. No audio is sent to third parties unless you explicitly configure a cloud provider.

---

## ✨ Features

| Category | Features |
|----------|----------|
| **Voice Profiles** | Create voice identities bound to any provider, manage training versions, track status |
| **Audio Training** | Upload samples, record in-browser, preprocess (noise reduction, normalization), train models via Celery |
| **Real-time Synthesis** | Text-to-speech with speed / pitch / volume controls, SSML support (Azure), streaming |
| **Voice Comparison** | Side-by-side synthesis across multiple profiles for A/B testing |
| **Voice Library** | Browse 200+ voices across all providers with preview playback |
| **Voice Cloning** | 4 providers support cloning: ElevenLabs, Coqui XTTS, StyleTTS2, CosyVoice |
| **OpenAI-Compatible API** | Drop-in `POST /v1/audio/speech` endpoint works with OpenAI SDKs, LangChain, CrewAI |
| **Persona Presets** | 6 built-in presets (Friendly, Professional, Energetic, Calm, Authoritative, Soothing) + custom |
| **4 Interfaces** | Web UI, REST API (60+ endpoints), CLI (Typer + Rich), MCP Server (9 tools for AI agents) |
| **GPU Flexibility** | Per-provider GPU mode: Docker GPU, host CPU, or auto-detect |
| **API Key Management** | Scoped keys (read / write / synthesize / train / admin) with Argon2id hashing |
| **Webhook Events** | HMAC-signed delivery for training.completed / training.failed |
| **In-App Help** | Built-in help center, provider setup guides, and troubleshooting |

---

## 🚀 Quick Start

### Prerequisites

- **Docker** Engine 24+ with Compose v2 (recommended)
- Or: Python 3.11+ and Node.js 20+ (for local development)

### 1. Clone & Start

```bash
git clone https://github.com/HouseGarofalo/atlas-vox.git
cd atlas-vox
make docker-up
```

### 2. Open

| Service | URL |
|---------|-----|
| **Web UI** | http://localhost:3100 |
| **API** | http://localhost:8100 |
| **Swagger Docs** | http://localhost:8100/docs |

### 3. (Optional) Enable GPU

```bash
make docker-gpu-up    # Adds NVIDIA GPU worker for local models
```

That's it. Kokoro (54 voices) and Piper work immediately with no configuration. For cloud providers, add your API keys on the Providers page.

<details>
<summary><strong>Local Development (without Docker)</strong></summary>

```bash
make install    # Install Python + Node dependencies
make dev        # Start backend (localhost:8100) + frontend (localhost:3000)
```

You will need Redis running locally for training jobs.
</details>

---

## 🔌 TTS Providers

9 providers, each extending `TTSProvider` ABC with dynamic capability declaration — the UI adapts automatically.

### Built-in Providers (Docker)

| Provider | Type | Cloning | Stream | SSML | GPU | Languages | Key Feature |
|----------|------|:-------:|:------:|:----:|-----|-----------|-------------|
| **Kokoro** | Local CPU | | | | CPU | en | 54 voices, 82M params, ultra-fast |
| **Piper** | Local CPU | | | | CPU | 30+ | ONNX, Home Assistant compatible |
| **ElevenLabs** | Cloud | ✅ | ✅ | | — | 29 | Premium quality, instant cloning |
| **Azure Speech** | Cloud | ✅ | ✅ | ✅ | — | 140+ | Enterprise SSML, 400+ voices |
| **Coqui XTTS v2** | Local | ✅ | ✅ | | Cfg | 17 | Clone from 6s audio |
| **StyleTTS2** | Local | ✅ | | | Cfg | en | Human-level MOS, style transfer |
| **CosyVoice** | Local | ✅ | ✅ | | Cfg | 9 | 150ms streaming latency |
| **Dia** | Local | ✅ | | | Cfg | en | 1.6B param dialogue + non-verbals |
| **Dia2** | Local | | ✅ | | Cfg | en | 2B param streaming dialogue |

**GPU Modes** (Cfg = configurable per Docker provider):

| Mode | Example | Description |
|------|---------|-------------|
| `host_cpu` | `COQUI_XTTS_GPU_MODE=host_cpu` | Run on CPU (default) |
| `docker_gpu` | `COQUI_XTTS_GPU_MODE=docker_gpu` | NVIDIA GPU in Docker |
| `auto` | `COQUI_XTTS_GPU_MODE=auto` | Auto-detect, fallback CPU |

---

## 🖥️ Web UI

13 pages accessible via sidebar navigation with full light/dark theme and mobile-responsive layout.

| Page | Route | Purpose |
|------|-------|---------|
| **Dashboard** | `/` | Stats, provider health grid, active jobs, recent synthesis |
| **Voice Profiles** | `/profiles` | Create, manage, delete voice identities |
| **Voice Library** | `/library` | Browse all voices across all providers with filtering |
| **Training Studio** | `/training` | Upload/record audio, preprocess, train models |
| **Synthesis Lab** | `/synthesis` | Text-to-speech with parameter controls + presets |
| **Comparison** | `/compare` | Side-by-side multi-voice comparison |
| **Providers** | `/providers` | View all 9 providers with health, config, and test |
| **API Keys** | `/api-keys` | Create/revoke scoped API keys |
| **Settings** | `/settings` | Theme toggle, default provider, audio format |
| **Docs** | `/docs` | Provider setup guides with step-by-step instructions |
| **Help** | `/help` | In-app help center with FAQ and troubleshooting |
| **Admin** | `/admin` | System administration and provider management |
| **Design System** | `/design` | Customize accent color, fonts, radius, density, card styles |

---

## 🏗️ Architecture

```
                                  +------------------+
                                  |    Web UI :3100   |
                                  |  React + Vite     |
                                  +--------+---------+
                                           |
                                           v
+----------+     +------------------+   +-----------+   +------------------+
|  CLI      +---->                  |   |           |   |                  |
| (Typer)   |    |  FastAPI :8100   +-->+ SQLite /  |   |  Redis :6379     |
+----------+     |                  |   | PostgreSQL|   |  (Celery broker) |
                 |  12 API routers  |   |           |   +--------+---------+
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

**Tech Stack:**

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

## ⚙️ Configuration

All settings via environment variables or `.env` file.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./atlas_vox.db` | Database connection |
| `AUTH_DISABLED` | `true` | Skip auth (homelab mode) |
| `REDIS_URL` | `redis://localhost:6379/1` | Celery broker |
| `STORAGE_PATH` | `./storage` | Audio & model storage |
| `ELEVENLABS_API_KEY` | *(empty)* | ElevenLabs cloud API |
| `AZURE_SPEECH_KEY` | *(empty)* | Azure AI Speech key |
| `AZURE_SPEECH_REGION` | `eastus` | Azure region |
| `BACKEND_PORT` | `8100` | Docker host port for API |
| `FRONTEND_PORT` | `3100` | Docker host port for UI |

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the complete 25+ variable reference.

---

## 🧪 Development

```bash
make dev          # Start backend + frontend dev servers
make test         # Run pytest (300 backend + 239 frontend tests)
make test-cov     # Tests with coverage report
make lint         # Ruff (Python) + ESLint (TypeScript)
make format       # Auto-format all code
make migrate      # Run Alembic migrations
make seed         # Seed database with providers
make clean        # Remove caches and build artifacts
```

### Project Structure

```
atlas-vox/
  backend/
    app/
      api/v1/endpoints/   # 12 API endpoint modules (60+ routes)
      core/               # Config, database, security, logging
      models/             # 9 SQLAlchemy async ORM models
      schemas/            # Pydantic v2 request/response schemas
      services/           # 7 business logic services
      providers/          # 9 TTS provider implementations
      tasks/              # Celery background tasks
      cli/                # Typer CLI with 7 command groups
      mcp/                # MCP server (JSONRPC 2.0 + SSE)
    tests/                # Pytest suite (300 tests)
  frontend/
    src/
      pages/              # 13 lazy-loaded React pages
      components/         # 40+ UI, audio, layout components
      stores/             # 8 Zustand state stores
      services/           # Typed API client (40+ methods)
  docker/                 # Dockerfiles + compose configs
  docs/                   # Extended documentation
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[User Guide](docs/USER_GUIDE.md)** | Comprehensive end-user guide with walkthroughs for every feature |
| **[API Reference](docs/API_REFERENCE.md)** | Complete REST API with request/response examples |
| **[Architecture](docs/ARCHITECTURE.md)** | System design, data flows, provider abstraction pattern |
| **[Deployment](docs/DEPLOYMENT.md)** | Docker, GPU setup, environment variables, production hardening |
| **[Troubleshooting](docs/TROUBLESHOOTING.md)** | Common issues with symptoms, causes, and fixes |
| [Providers](docs/PROVIDERS.md) | Per-provider setup guides and capabilities |
| [Database](docs/DATABASE.md) | Full schema, relationships, and migration guide |
| [CLI](docs/CLI.md) | CLI command reference |
| [MCP](docs/MCP.md) | MCP server tools, resources, and integration |
| [Configuration](docs/CONFIGURATION.md) | All environment variables and settings |
| [Frontend](docs/FRONTEND.md) | Component architecture, stores, routing |
| [Security](docs/SECURITY.md) | Authentication, API keys, CORS, webhook signing |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes and add tests
4. Run `make lint` and `make test`
5. Commit with a descriptive message
6. Push and create a Pull Request

### Code Style

- **Backend**: Ruff for linting/formatting, type hints on all functions
- **Frontend**: ESLint + Prettier, TypeScript strict mode
- **Commits**: Conventional commits preferred (`feat:`, `fix:`, `docs:`, etc.)

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

Built with FastAPI, React, and 9 TTS engines

**[User Guide](docs/USER_GUIDE.md)** &middot; **[API Reference](docs/API_REFERENCE.md)** &middot; **[Deployment](docs/DEPLOYMENT.md)**

</div>
