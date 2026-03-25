# Atlas Vox — Initializer Prompt

You are the initializer agent for the Atlas Vox project. This prompt runs ONCE at the start of the project to generate all implementation tasks from the specification.

## Instructions

1. **Read the specification**: `docs/prp/PRD.md` contains the full PRD with 6 implementation phases
2. **Read current state**: Check `.harness/config.json` and `features.json` for what's already done
3. **Connect to Archon**: Project ID is in `.archon_project.json`
4. **Generate tasks**: For each phase, create Archon tasks with:
   - Clear title prefixed with phase number: `[P2] Implement audio_processor service`
   - Detailed description with acceptance criteria
   - Feature label matching phase: `Phase 2 - Audio Pipeline`
   - Task order (higher = higher priority)
5. **Update features.json**: Assign Archon task IDs to each feature
6. **Update progress**: Write to `claude-progress.txt`
7. **Commit**: `git add . && git commit -m "chore: initialize harness tasks from PRD"`

## Phase 1 Status: COMPLETE
Phase 1 scaffolding is already done. Start task generation from Phase 2.

## Key Context
- Archon Project ID: `f8f125bb-e15e-4632-a4f4-03b6b0870687`
- Backend: Python 3.11+, FastAPI, SQLAlchemy async, Celery+Redis
- Frontend: React 18+, TypeScript, Vite, Tailwind, Zustand
- 9 TTS providers (only Kokoro implemented so far)
- PRD location: `docs/prp/PRD.md`
