# Atlas Vox — Project Instructions for Claude Code

## Project Overview

Atlas Vox is an intelligent voice training and customization platform. Read `docs/prp/PRD.md` for the complete product requirements and implementation plan.

## Development Framework

This project uses **PRP (Product Requirements Planning)** + **Autonomous Agent Harness** for structured development.

### Key Files
- **`docs/prp/PRD.md`** — Full PRD with architecture, schema, API, and 6-phase implementation plan
- **`.archon_project.json`** — Archon project link (ID: `f8f125bb-e15e-4632-a4f4-03b6b0870687`)
- **`.harness/config.json`** — Harness configuration (phases, testing strategy)
- **`features.json`** — Feature registry with implementation and test status
- **`claude-progress.txt`** — Session progress tracking for agent handoffs
- **`prompts/initializer_prompt.md`** — First-session agent (task generation from PRD)
- **`prompts/coding_prompt.md`** — Continuation sessions (feature implementation)

### Agent Workflow
1. **Read** `claude-progress.txt` and `.harness/session_notes.md` for context
2. **Check Archon** for current task (`find_tasks(filter_by="status", filter_value="doing")`)
3. **Implement** following the PRD phase plan
4. **Update** `features.json`, `claude-progress.txt`, and Archon task status
5. **Commit** with clean handoff for next session

## Quick Start for Coding Agent

1. **Read `docs/prp/PRD.md` first** — full PRD with 6 phases
2. **Follow the phases in order** — Phase 1 (Foundation) is complete, start from Phase 2
3. **Verify each phase** — each phase has a "Verification" section with specific checks

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy async, Alembic, Celery + Redis, structlog
- **Frontend**: React 18+, TypeScript 5+, Vite, Tailwind CSS, Zustand, wavesurfer.js
- **CLI**: Typer + Rich
- **MCP**: JSONRPC 2.0 + SSE transport
- **Database**: SQLite (default) via aiosqlite, optional PostgreSQL via asyncpg

## Key Conventions

### Backend
- All services are async (`async def`)
- Use Pydantic v2 for all request/response schemas
- Use structlog for logging (JSON format)
- Provider pattern: all TTS providers extend `TTSProvider` ABC from `providers/base.py`
- Each provider declares capabilities via `get_capabilities()` — the frontend adapts dynamically
- Training jobs use Celery tasks — never block the FastAPI event loop
- Authentication is optional (`AUTH_DISABLED=true` for single-user mode)
- Use `Depends(get_db)` for database sessions, `Depends(get_current_user)` for auth

### Frontend
- Zustand for state management (one store per domain: profiles, training, providers, synthesis, auth)
- React Router v6 with lazy loading for pages
- Tailwind CSS with CSS custom properties for light/dark theme
- wavesurfer.js for audio waveform visualization
- Monaco Editor for SSML editing
- All API calls go through `services/api.ts`

### CLI
- Typer for command definitions, Rich for terminal output (tables, progress bars)
- Entry point: `atlas-vox` (configured in pyproject.toml `[project.scripts]`)

### Code Style
- Backend: Ruff for linting and formatting
- Frontend: ESLint v9 flat config + Prettier
- Type hints required on all Python function signatures
- TypeScript strict mode enabled

## 9 TTS Providers

| Provider | Module | GPU | Key Notes |
|----------|--------|-----|-----------|
| ElevenLabs | `elevenlabs.py` | No | Cloud API, official SDK |
| Azure AI Speech | `azure_speech.py` | No | Cloud, SSML support |
| Coqui XTTS v2 | `coqui_xtts.py` | Configurable | Voice cloning from 6s audio |
| StyleTTS2 | `styletts2.py` | Configurable | Zero-shot, style diffusion |
| CosyVoice | `cosyvoice.py` | Configurable | Multilingual, streaming |
| Kokoro | `kokoro_tts.py` | No (CPU) | Lightweight, 54 voices, default |
| Piper | `piper_tts.py` | No (CPU) | ONNX, Home Assistant compatible |
| Dia | `dia.py` | Configurable | Dialogue, 1.6B params |
| Dia2 | `dia2.py` | Configurable | Streaming dialogue, 2B params |

"Configurable" GPU means: user can choose Docker GPU container or host CPU mode per provider.

## File Organization

See the complete directory structure in `docs/prp/PRD.md` section 12. Key paths:
- `backend/app/providers/` — TTS provider implementations
- `backend/app/services/` — Business logic
- `backend/app/api/v1/endpoints/` — FastAPI routes
- `backend/app/mcp/` — MCP server
- `backend/app/cli/` — CLI commands
- `frontend/src/pages/` — React pages
- `frontend/src/stores/` — Zustand stores

## Common Commands

```bash
make dev          # Start backend + frontend in dev mode
make test         # Run all tests
make lint         # Run Ruff (backend) + ESLint (frontend)
make migrate      # Run Alembic migrations
make docker-up    # Start full stack with Docker Compose
make docker-gpu-up # Start with GPU worker
```

## Archon Integration

- **Project ID**: `f8f125bb-e15e-4632-a4f4-03b6b0870687`
- **Task management**: All tasks tracked via Archon MCP (`find_tasks`, `manage_task`)
- **Documents**: Architecture and PRD stored as Archon documents
- **Session state**: `claude-progress.txt` + `.harness/session_notes.md` for handoffs
