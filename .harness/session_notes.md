# Atlas Vox — Session Notes

## Session 1: 2026-03-25 — Initial Scaffolding

### Completed
- Phase 1 Foundation scaffolding (86 files)
- Backend: core config, logging, database, security, dependencies
- 9 SQLAlchemy models, 8 Pydantic schema modules
- TTSProvider ABC + KokoroTTSProvider (first provider)
- ProviderRegistry + ProfileService
- API endpoints: /health, /profiles (CRUD), /providers
- FastAPI app with lifespan, CORS, structured logging
- CLI entry point (atlas-vox) with version and serve commands
- Celery + Alembic configuration
- Frontend: Vite + React + TypeScript + Tailwind + Zustand
- Layout shell (Sidebar, Header, theme toggle)
- 8 page stubs, API client, TypeScript types
- Root configs: .gitignore, .env.example, Makefile, README.md

### Decisions
- SQLite default (aiosqlite), optional PostgreSQL
- Auth disabled by default for single-user/homelab
- Kokoro as first provider (CPU-only, no GPU needed)
- UUID primary keys stored as String(36) for SQLite compatibility

### Next Session Priority
1. Set up PRP/harness framework integration
2. Begin Phase 2: Audio Pipeline & Training Infrastructure

### Archon References
- Project ID: f8f125bb-e15e-4632-a4f4-03b6b0870687
- Architecture Doc ID: d8ef75d4-056d-4107-aa73-3699bfd8c61f
