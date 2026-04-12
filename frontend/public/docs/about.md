# About Atlas Vox

## Project Information

| | |
|---|---|
| **Version** | 0.1.0 |
| **TTS Providers** | 9 |
| **Interfaces** | Web UI, REST API, CLI, MCP Server |
| **Backend** | Python 3.11 + FastAPI + SQLAlchemy + Celery |
| **Frontend** | React 18 + TypeScript + Vite + Tailwind CSS |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Task Queue** | Celery + Redis |
| **License** | MIT |

---

## TTS Provider Comparison

| Provider | Type | Model | Voices | Languages | Streaming | Cloning | Pricing |
|----------|------|-------|--------|-----------|-----------|---------|---------|
| Kokoro | Local CPU | 82M params | 54 | en, ja, zh, ko, fr, de, it, pt, es, hi | No | No | Open Source |
| Piper | Local CPU | ONNX VITS | 200+ | 30+ | No | No | Open Source |
| ElevenLabs | Cloud | Proprietary | 100+ | 29 | Yes | Yes | Freemium |
| Azure Speech | Cloud | Neural TTS | 400+ | 140+ | Yes | No | Paid |
| Coqui XTTS v2 | Local GPU | ~1.5B params | Custom | 17 | Yes | Yes | Open Source |
| StyleTTS2 | Local GPU | ~200M params | Custom | en | No | Yes | Open Source |
| CosyVoice | Local GPU | 300M params | Custom | en, zh, ja, ko | Yes | Yes | Open Source |
| Dia | Local GPU | 1.6B params | 2 | en | No | No | Open Source |
| Dia2 | Local GPU | 2B params | 2 | en | Yes | No | Open Source |

---

## Technology Stack

| Area | Technology |
|------|-----------|
| Backend Framework | FastAPI + Pydantic v2 |
| ORM | SQLAlchemy (async) |
| Task Queue | Celery + Redis |
| Migrations | Alembic |
| Logging | structlog (JSON) |
| Frontend Framework | React 18 + TypeScript 5 |
| Build Tool | Vite |
| CSS | Tailwind CSS |
| State Management | Zustand |
| Audio Visualization | wavesurfer.js |
| Code Editor | Monaco Editor |
| CLI | Typer + Rich |
| MCP Transport | JSONRPC 2.0 + SSE |
| Authentication | Argon2id + Bearer tokens |

---

## Documentation Links

- [Swagger API Docs](http://localhost:8100/docs)
- [ReDoc API Reference](http://localhost:8100/redoc)
- [GitHub Repository](https://github.com/HouseGarofalo/atlas-vox)
- [Product Requirements Document](/docs/prp/PRD.md)
