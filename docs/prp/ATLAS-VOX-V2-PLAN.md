# Implementation Plan: Atlas Vox v2.0

**PRD Reference:** `docs/prp/ATLAS-VOX-V2-PRD.md`
**Audit Reference:** `docs/prp/AUDIT-AND-ROADMAP.md`
**Created:** 2026-04-05
**Author:** Claude Code (PRP Framework)
**Status:** Draft
**Estimated Effort:** 12-18 sessions (~104 hours)

---

## Overview

This plan transforms 166 audit findings into 69 actionable implementation tasks across 6 phases. Each task includes exact file paths, code patterns to follow, validation criteria, and dependency chains. The plan is designed for session-based execution where each session implements a coherent subset of tasks that can be committed and deployed independently.

---

## Prerequisites

### Before Starting
- [x] PRD approved (`docs/prp/ATLAS-VOX-V2-PRD.md`)
- [x] Audit complete (`docs/prp/AUDIT-AND-ROADMAP.md`)
- [x] Docker stack running (verified 2026-04-05)
- [x] All 9 providers returning voices via API (353 total, verified)
- [ ] Answers to open questions 1, 3, 6 in PRD (can proceed without — defaults assumed)

### Key Codebase Patterns (Reference)
| Pattern | Reference File | Usage |
|---------|---------------|-------|
| Auth dependency injection | `backend/app/core/dependencies.py` | `user: CurrentUser` on endpoints |
| Scope enforcement | `dependencies.py:require_scope()` | `Depends(require_scope("admin"))` |
| Rate limiting | `synthesis.py:29` | `@limiter.limit("10/minute")` + `request: Request` param |
| Router mounting | `backend/app/api/v1/router.py` | `api_router.include_router(module.router)` |
| Provider abstraction | `backend/app/providers/base.py:195-237` | Abstract methods + optional `NotImplementedError` |
| Model registration | `backend/app/models/__init__.py` | Import all models for SQLAlchemy metadata |
| Backend testing | `backend/tests/conftest.py` | `pytest-asyncio` + `AsyncClient` + DB override |
| Frontend testing | `frontend/package.json` | Vitest + `@vitest/coverage-v8` |
| Store pattern | `frontend/src/stores/profileStore.ts` | Zustand with `create<State>((set, get) => ({...}))` |
| Type definitions | `frontend/src/types/index.ts` | Shared TypeScript interfaces |

---

## Phase A: Critical Fixes [Sessions 1-3]

**Objective:** Eliminate all ship-blocking bugs — unauthenticated endpoints, data corruption, broken navigation, Docker failures, and injection vectors.
**Gate:** ALL A-tasks must pass before any Phase B work begins.

---

### A1: Add Authentication to All Unauthenticated Endpoints
- **Description:** Add `user: CurrentUser` dependency to 14 endpoints across 4 files that currently have zero auth. These endpoints expose provider API keys, self-healing controls, telemetry, and voice data to any unauthenticated caller.
- **Files to modify:**
  - `backend/app/api/v1/endpoints/providers.py` — Add `user: CurrentUser` to ALL 10 endpoint functions
  - `backend/app/healing/endpoints.py` — Add `user: CurrentUser` to ALL 5 endpoint functions
  - `backend/app/main.py:110-113` — Add `user: CurrentUser` to `get_telemetry()`
  - `backend/app/api/v1/endpoints/voices.py` — `list_all_voices` and `preview_voice` get `user: CurrentUser`
- **Estimated Time:** 2hr
- **Pattern to follow:**
  ```python
  # Reference: backend/app/api/v1/endpoints/profiles.py:29
  from app.core.dependencies import CurrentUser, DbSession
  
  @router.get("")
  async def list_all_profiles(db: DbSession, user: CurrentUser, ...):
      # user is auto-injected; 401 if auth enabled and no token
  ```
- **Validation:**
  - [ ] `curl http://localhost:8100/api/v1/providers` returns 401 when AUTH_DISABLED=false
  - [ ] `curl -H "Authorization: Bearer <token>" http://localhost:8100/api/v1/providers` succeeds
  - [ ] Existing tests still pass (they set AUTH_DISABLED=true in conftest)
  - [ ] Run: `cd backend && python -m pytest tests/test_api/test_providers.py -v`

---

### A2: Fix VersionCompareModal Destructive Version Mutation
- **Description:** The version comparison modal calls `api.activateVersion()` for each version being compared, permanently changing the profile's active version. Fix by adding a `version_id` query parameter to the synthesis endpoint and using it directly without activation.
- **Files to modify:**
  - `backend/app/api/v1/endpoints/synthesis.py` — Add optional `version_id: str | None = Query(None)` param to `synthesize_text()`. When provided, use that version's voice_id for synthesis without changing active_version.
  - `frontend/src/pages/ProfilesPage.tsx:480-484` — Replace `api.activateVersion()` calls with `api.synthesize({ ..., version_id })` approach
- **Estimated Time:** 1hr
- **Implementation notes:**
  ```python
  # In synthesis endpoint, add:
  version_id: str | None = Query(None, description="Synthesize using specific model version without activating it")
  
  # In synthesis logic, if version_id is provided:
  # 1. Load ModelVersion by ID
  # 2. Use its voice_id/model_path for synthesis
  # 3. Do NOT modify profile.active_version_id
  ```
- **Validation:**
  - [ ] Compare two versions — profile's active_version_id unchanged after
  - [ ] Both comparison audios play correctly
  - [ ] Regular synthesis (no version_id) still works as before

---

### A3: Fix Broken Navigation `/voice-library` → `/library`
- **Description:** Single string replacement.
- **Files:** `frontend/src/pages/ProfilesPage.tsx:191`
- **Estimated Time:** 10min
- **Change:** `navigate("/voice-library")` → `navigate("/library")`
- **Validation:**
  - [ ] Click "Browse Voice Library" in new profile dialog → lands on Voice Library page
  - [ ] Voice Library loads with 353 voices

---

### A4: Add 404 Catch-All Route
- **Description:** Create a simple NotFoundPage component and add it as the catch-all route.
- **Files:**
  - New: `frontend/src/pages/NotFoundPage.tsx`
  - Modify: `frontend/src/App.tsx` — add `<Route path="*" element={<NotFoundPage />} />`
- **Estimated Time:** 15min
- **Implementation:**
  ```tsx
  // NotFoundPage.tsx — minimal, follows existing page patterns
  export default function NotFoundPage() {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <h1 className="text-4xl font-bold">404</h1>
        <p className="mt-2 text-[var(--color-text-secondary)]">Page not found</p>
        <Button onClick={() => navigate("/")}>Back to Dashboard</Button>
      </div>
    );
  }
  ```
- **Validation:**
  - [ ] Navigate to `/nonexistent` → shows 404 page
  - [ ] "Back to Dashboard" button works

---

### A5: Fix Provider Singleton Race Condition
- **Description:** `synthesis_service.synthesize()` mutates shared provider instances via `provider.configure()`. Under concurrent requests, one user's voice_settings bleed into another's synthesis. Fix by passing voice_settings as a parameter to `synthesize()` instead of mutating provider config.
- **Files to modify:**
  - `backend/app/providers/base.py` — Add `voice_settings: dict | None = None` parameter to `synthesize()` signature. Each provider applies settings locally without mutating instance state.
  - `backend/app/services/synthesis_service.py:160-163` — Remove `provider.configure()` call. Pass `voice_settings` directly to `provider.synthesize()`.
  - All 9 provider `synthesize()` implementations — Add `voice_settings` parameter, apply as local overrides
- **Estimated Time:** 2hr
- **Implementation approach:**
  ```python
  # base.py — Updated signature
  @abstractmethod
  async def synthesize(
      self, text: str, voice_id: str, settings: SynthesisSettings,
      voice_settings: dict | None = None,  # NEW — per-request overrides
  ) -> AudioResult:
  
  # Each provider applies locally:
  async def synthesize(self, text, voice_id, settings, voice_settings=None):
      effective_config = {**self._config}
      if voice_settings:
          effective_config.update(voice_settings)
      # Use effective_config instead of self._config for this request
  ```
- **Validation:**
  - [ ] Two concurrent synthesis requests with different voice_settings produce correct, independent results
  - [ ] Run: `cd backend && python -m pytest tests/ -v -k "synthes"` — all pass
  - [ ] Manually test: synthesize with speed=0.5 and speed=2.0 simultaneously

---

### A6: Fix Dockerfile Model Download Scripts
- **Description:** Extract broken inline `python3 -c` strings to standalone Python scripts.
- **Files:**
  - New: `docker/scripts/download_piper_model.py`
  - New: `docker/scripts/download_kokoro_model.py`
  - Modify: `docker/Dockerfile.backend:53-91` — Replace inline python with `COPY` + `RUN python3`
- **Estimated Time:** 1hr
- **Implementation:**
  ```dockerfile
  # Replace lines 53-68 with:
  COPY docker/scripts/download_piper_model.py /tmp/
  RUN python3 /tmp/download_piper_model.py || echo "Piper model download skipped"
  
  # Replace lines 71-91 with:
  COPY docker/scripts/download_kokoro_model.py /tmp/
  RUN python3 /tmp/download_kokoro_model.py || echo "Kokoro model download skipped"
  ```
- **Validation:**
  - [ ] `docker compose -f docker/docker-compose.yml build backend` completes successfully
  - [ ] Piper and Kokoro models present in container: `docker exec atlas-vox-backend ls storage/models/piper/`
  - [ ] Kokoro synthesis works in Docker: `curl -X POST http://localhost:8100/api/v1/synthesis/synthesize -d '{"text":"hello","provider_name":"kokoro","voice_id":"af_heart"}'`

---

### A7: Create .dockerignore
- **Description:** Prevent secrets, large files, and unnecessary data from entering Docker build context.
- **Files:** New: `.dockerignore` at project root
- **Estimated Time:** 15min
- **Content:**
  ```
  .git
  .env
  .env.*
  storage/
  temp/
  node_modules/
  frontend/dist/
  *.db
  *.db-shm
  *.db-wal
  __pycache__/
  .pytest_cache/
  .ruff_cache/
  .claude/
  .claude-backup/
  .playwright-mcp/
  e2e-screenshots/
  audit-*.png
  .venv/
  venv/
  *.egg-info/
  gpu-service/.venv/
  ```
- **Validation:**
  - [ ] `docker compose -f docker/docker-compose.yml build` runs faster
  - [ ] `docker exec atlas-vox-backend cat /app/.env` fails (not in image)

---

### A8: Fix Docker Layer Caching
- **Description:** Move `COPY backend/app ./app` AFTER `pip install` in Dockerfile builder stage.
- **Files:** `docker/Dockerfile.backend:3-6`
- **Estimated Time:** 30min
- **Change:**
  ```dockerfile
  # BEFORE (broken caching):
  COPY backend/pyproject.toml backend/README.md ./
  COPY backend/app ./app              # <-- invalidates pip cache
  RUN pip install --no-cache-dir --prefix=/install ".[audio]"
  
  # AFTER (proper caching):
  COPY backend/pyproject.toml backend/README.md ./
  RUN pip install --no-cache-dir --prefix=/install ".[audio]"  # <-- cached if deps unchanged
  COPY backend/app ./app              # <-- only invalidated by code changes
  ```
- **Validation:**
  - [ ] First build: full pip install (~5 min)
  - [ ] Change a Python file, rebuild: pip install cached, only COPY step re-runs (~30s)

---

### A9: Fix GPU Service Broken Provider Imports
- **Description:** Wrap nonexistent provider imports in try/except so the GPU service starts.
- **Files:** `gpu-service/app/providers/__init__.py`
- **Estimated Time:** 30min
- **Implementation:**
  ```python
  # Wrap each import:
  try:
      from .f5_tts_provider import F5TTSProvider
  except ImportError:
      F5TTSProvider = None  # Not yet implemented
  
  # Repeat for: fish_speech, openvoice_provider, orpheus_provider, piper_training_provider
  ```
- **Validation:**
  - [ ] `cd gpu-service && python -c "from app.providers import *; print('OK')"` succeeds

---

### A10: Add Docker Health Checks + Resource Limits
- **Description:** Add `healthcheck` and `deploy.resources.limits` to all services.
- **Files:** `docker/docker-compose.yml`
- **Estimated Time:** 30min
- **Implementation:**
  ```yaml
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2'
  
  frontend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 256M
  
  redis:
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 512M
  
  worker:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
  ```
  Also change `depends_on` to use `condition: service_healthy`.
- **Validation:**
  - [ ] `docker compose -f docker/docker-compose.yml up -d` — all containers show "healthy"
  - [ ] `docker ps` shows health status for each container

---

### A11: Fix JWT Secret Handling
- **Description:** Auto-generate JWT secret in Docker if none provided. Add minimum length validation.
- **Files:**
  - `backend/app/core/config.py:36,90-96` — Add `secrets.token_urlsafe(32)` as default, add min length check
  - `docker/docker-compose.yml` — Add `JWT_SECRET_KEY=${JWT_SECRET_KEY:-}` to env
- **Estimated Time:** 30min
- **Validation:**
  - [ ] App starts without JWT_SECRET_KEY env var — generates random key, logs warning
  - [ ] App starts with explicit key — uses provided key
  - [ ] Setting AUTH_DISABLED=false with short key (<32 chars) raises ValueError

---

### A12: Add DB Backup Script + docker-reset Warning
- **Description:** Create backup script; add confirmation to destructive Makefile target.
- **Files:**
  - New: `scripts/backup-db.sh` — Copies SQLite DB from Docker volume to `backups/` dir
  - Modify: `Makefile` — Add confirmation prompt to `docker-reset` target
- **Estimated Time:** 1hr
- **Validation:**
  - [ ] `bash scripts/backup-db.sh` creates timestamped backup in `backups/`
  - [ ] `make docker-reset` prompts "This will DELETE all data. Continue? [y/N]"

---

### A13: Commit Untracked Audio Design Files
- **Description:** Stage and commit the 9 untracked Audio Design feature files.
- **Files:** `backend/app/schemas/audio_tools.py`, `backend/tests/test_api/test_audio_design.py`, `backend/tests/test_services/test_audio_processor_design.py`, `frontend/src/components/audio/AudioTimeline.tsx`, `frontend/src/pages/AudioDesignPage.tsx`, `frontend/src/stores/audioDesignStore.ts`, `frontend/src/test/pages/AudioDesignPage.test.tsx`, `frontend/src/test/stores/audioDesignStore.test.ts`, `docs/cloud_audio_enhancement_apis.md`
- **Estimated Time:** 15min
- **Validation:**
  - [ ] `git status` shows no untracked feature files
  - [ ] Audio Design page loads at `/audio-design`

---

### A14: Update .gitignore
- **Description:** Add missing patterns for IDE artifacts and build files.
- **Files:** `.gitignore`
- **Estimated Time:** 10min
- **Patterns to add:**
  ```
  .claude/
  .playwright-mcp/
  e2e-screenshots/
  audit-*.png
  *.db-shm
  *.db-wal
  ```
- **Validation:**
  - [ ] `git status` no longer shows `.claude/` or `*.db-shm` as untracked

---

### A15: Fix output_format to Enum
- **Description:** Constrain `output_format` to prevent ffmpeg command injection via pydub.
- **Files:**
  - `backend/app/schemas/synthesis.py` — Add `OutputFormat` enum, use in `SynthesisRequest.output_format`, `BatchSynthesisRequest`
  - `backend/app/api/v1/endpoints/openai_compat.py` — Constrain `SpeechRequest.response_format`
- **Estimated Time:** 30min
- **Implementation:**
  ```python
  from enum import Enum
  
  class OutputFormat(str, Enum):
      WAV = "wav"
      MP3 = "mp3"
      OGG = "ogg"
      FLAC = "flac"
  
  class SynthesisRequest(BaseModel):
      output_format: OutputFormat = OutputFormat.WAV  # was: str = "wav"
  ```
- **Validation:**
  - [ ] `POST /synthesize` with `output_format: "wav"` succeeds
  - [ ] `POST /synthesize` with `output_format: "evil;rm -rf /"` returns 422

---

### A16: Whitelist voice_settings Keys
- **Description:** Prevent voice_settings from overriding provider API keys or sensitive config.
- **Files:**
  - `backend/app/schemas/synthesis.py` — Add `VOICE_SETTINGS_BLOCKED_KEYS` set and validator
  - `backend/app/services/synthesis_service.py:162` — Apply whitelist before passing to provider
- **Estimated Time:** 30min
- **Implementation:**
  ```python
  VOICE_SETTINGS_BLOCKED_KEYS = {
      "api_key", "subscription_key", "model_id", "model_path",
      "gpu_mode", "enabled", "config_json",
  }
  
  @field_validator("voice_settings")
  @classmethod
  def validate_voice_settings(cls, v):
      if v is None:
          return v
      blocked = set(v.keys()) & VOICE_SETTINGS_BLOCKED_KEYS
      if blocked:
          raise ValueError(f"Blocked keys in voice_settings: {blocked}")
      return v
  ```
- **Validation:**
  - [ ] `voice_settings: {"speed": 1.5}` succeeds
  - [ ] `voice_settings: {"api_key": "steal"}` returns 422

---

### Phase A Validation Gate
```bash
# All tests must pass
cd backend && python -m pytest tests/ -v --tb=short

# Frontend builds without errors
cd frontend && npx tsc --noEmit && npm run build

# Docker stack builds and runs
docker compose -f docker/docker-compose.yml up --build -d
sleep 30
curl -f http://localhost:8100/api/v1/health

# Voice library returns all voices
curl -s "http://localhost:8100/api/v1/voices?limit=5000" | python -c "
import json, sys
data = json.load(sys.stdin)
assert data['total'] >= 300, f'Only {data[\"total\"]} voices'
providers = set(v['provider'] for v in data['voices'])
assert 'azure_speech' in providers, 'Azure missing'
assert 'elevenlabs' in providers, 'ElevenLabs missing'
print(f'PASS: {data[\"total\"]} voices from {len(providers)} providers')
"
```

---

## Phase B: Security Hardening [Sessions 3-4]

**Objective:** Close all high/medium security vulnerabilities. Add scope enforcement, upload limits, security headers, non-root containers, encryption at rest.
**Gate:** Zero high-severity security findings after this phase.

---

### B1: Add require_scope to Admin Operations
- **Description:** Apply `require_scope("admin")` to all config-mutation and admin endpoints.
- **Files:** `providers.py` (config update/delete), `healing/endpoints.py` (toggle, review), `api_keys.py` (all), `webhooks.py` (all)
- **Estimated Time:** 1hr
- **Pattern:**
  ```python
  from app.core.dependencies import require_scope
  
  @router.put("/{name}/config")
  async def update_provider_config(
      name: str, data: ProviderConfigUpdate, db: DbSession,
      user: CurrentUser,
      _admin = require_scope("admin"),  # Enforce admin scope
  ):
  ```
- **Validation:**
  - [ ] User with `scopes: ["read"]` gets 403 on config update
  - [ ] User with `scopes: ["admin"]` succeeds

---

### B2: Add File Upload Size Limits
- **Files:** `samples.py`, `audio_tools.py:203,389`, `nginx.conf`
- **Estimated Time:** 30min
- **Implementation:**
  ```python
  # In each upload endpoint, before reading:
  MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100MB
  content = await audio.read()
  if len(content) > MAX_UPLOAD_BYTES:
      raise HTTPException(413, f"File too large. Max {MAX_UPLOAD_BYTES // (1024*1024)}MB")
  ```
  ```nginx
  # nginx.conf — add inside server block:
  client_max_body_size 100m;
  ```
- **Validation:**
  - [ ] Upload 50MB file → succeeds
  - [ ] Upload 200MB file → returns 413

---

### B3: Add Path Traversal Protection
- **Files:** `audio.py:28,52,75`
- **Estimated Time:** 30min
- **Implementation:**
  ```python
  AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".opus"}
  
  def safe_audio_path(base_dir: Path, filename: str) -> Path:
      clean = Path(filename).name  # Strip directory components
      if ".." in clean or "/" in clean or "\\" in clean:
          raise HTTPException(400, "Invalid filename")
      if Path(clean).suffix.lower() not in AUDIO_EXTENSIONS:
          raise HTTPException(400, "Invalid file type")
      full = (base_dir / clean).resolve()
      if not str(full).startswith(str(base_dir.resolve())):
          raise HTTPException(400, "Path traversal detected")
      return full
  ```

---

### B4: Nginx Security Headers + gzip + Proxy Timeouts
- **Files:** `docker/nginx.conf`
- **Estimated Time:** 30min
- **Add to server block:**
  ```nginx
  # Security headers
  add_header X-Content-Type-Options "nosniff" always;
  add_header X-Frame-Options "DENY" always;
  add_header X-XSS-Protection "1; mode=block" always;
  add_header Referrer-Policy "strict-origin-when-cross-origin" always;
  add_header Permissions-Policy "microphone=(), camera=()" always;
  
  # Compression
  gzip on;
  gzip_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml;
  gzip_min_length 256;
  gzip_vary on;
  
  # Upload size
  client_max_body_size 100m;
  
  # In /api/ location:
  proxy_connect_timeout 10;
  proxy_send_timeout 300;
  proxy_read_timeout 300;
  
  # In /mcp/ location — long-lived SSE:
  proxy_read_timeout 86400;
  ```

---

### B5: Non-Root User in Dockerfiles
- **Files:** `Dockerfile.backend`, `Dockerfile.frontend`, `Dockerfile.gpu-worker`
- **Estimated Time:** 30min
- **Implementation:**
  ```dockerfile
  # Backend — add before EXPOSE:
  RUN addgroup --system app && adduser --system --ingroup app app
  RUN chown -R app:app /app/storage /app/data
  USER app
  
  # Frontend — use unprivileged nginx:
  FROM nginxinc/nginx-unprivileged:alpine
  # Change EXPOSE to 8080 and update docker-compose port mapping
  ```

---

### B6-B12: Remaining Security Tasks
*(Follow same structure as above — rate limits, encryption, Redis auth, error sanitization, SSML sanitizer, Docker env vars, git cleanup)*

Each follows the established patterns. See PRD sections B6-B12 for complete specifications.

---

### Phase B Validation Gate
```bash
# Security checks
# 1. Auth required (set AUTH_DISABLED=false temporarily)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8100/api/v1/providers
# Expected: 401

# 2. Security headers present
curl -sI http://localhost:3100/ | grep -i "x-content-type-options"
# Expected: nosniff

# 3. Non-root
docker exec atlas-vox-backend whoami
# Expected: app (not root)

# 4. Upload limit works
dd if=/dev/zero bs=1M count=200 | curl -X POST -F "audio=@-" http://localhost:8100/api/v1/audio-tools/upload
# Expected: 413
```

---

## Phase C: Feature Completion [Sessions 5-7]

**Objective:** Complete partially-implemented features — real streaming, voice cloning for 2 more providers, Whisper transcription, text chunking, Alembic in Docker, MCP expansion, multilingual voices.

### Task Summary
| ID | Task | Key Files | Effort |
|----|------|-----------|--------|
| C1 | Real streaming for Kokoro + XTTS + fix fake streaming in Dia2/CosyVoice | 4 provider files + SSE endpoint + frontend | 4hr |
| C2 | clone_voice for CosyVoice + StyleTTS2 | 2 provider files + TrainingStudio UI badges | 3hr |
| C3 | Whisper-based transcription fallback | New `whisper_transcriber.py` + base.py | 2hr |
| C4 | Text chunking for long synthesis | New `text_chunker.py` + synthesis_service | 2hr |
| C5 | Alembic in Docker startup | `init-models.sh` | 30min |
| C6 | MCP tool expansion | `mcp/tools.py` | 2hr |
| C7 | Remove English-only filter from Azure | `azure_speech.py:869` + language map | 30min |
| C8 | Word boundary estimation fallback | New `word_boundary_estimator.py` | 3hr |

### C1 Implementation Detail: Real Streaming
```python
# Pattern: asyncio.Queue bridge for sync generators
import asyncio

async def stream_synthesize(self, text, voice_id, settings, voice_settings=None):
    queue: asyncio.Queue[bytes | None] = asyncio.Queue()
    
    def _generate_sync():
        # Run the synchronous model generation
        for chunk in model.generate_stream(text, voice_id):
            asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)
        asyncio.run_coroutine_threadsafe(queue.put(None), loop)  # sentinel
    
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _generate_sync)
    
    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        yield chunk
```

### C1 Frontend: SSE Endpoint + UI
```typescript
// New API method in api.ts:
async streamSynthesize(data: SynthesisRequest): Promise<ReadableStream<Uint8Array>> {
  const resp = await fetch(`${this.baseURL}/synthesis/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return resp.body!;
}
```

---

## Phase D: Code Quality [Sessions 7-9]

**Objective:** Eliminate technical debt — type safety, component duplication, store inconsistency, error handling.

### Task Summary
| ID | Task | Key Files | Effort |
|----|------|-----------|--------|
| D1 | Wire settingsStore into SynthesisLab | `SynthesisLabPage.tsx`, `settingsStore.ts` | 30min |
| D2 | Extract shared ConfigField component | `ProviderConfigCard.tsx`, `ProvidersPage.tsx` → new shared component | 2hr |
| D3 | Consolidate types into `types/index.ts` | 5+ files → `types/index.ts` | 1hr |
| D4 | Fix blob URL memory leak | `SynthesisLabPage.tsx:231` | 30min |
| D5 | Replace 22 `any` types with `unknown` + type guards | 7 frontend files | 2hr |
| D6 | Unify audio playback | New `useAudioPlayer` hook | 2hr |
| D7 | Create shared VoicePicker | New component, 4 consuming pages | 2hr |
| D8 | Standardize backend error responses | New `AppException` hierarchy | 1hr |
| D9 | Standardize store patterns | All 10 stores | 2hr |
| D10 | Remove duplicate get_db | `database.py`, `health.py` | 15min |
| D11 | Add Error Boundaries | `App.tsx` | 1hr |
| D12 | Add virtual scrolling to Voice Library | `VoiceLibraryPage.tsx` | 1hr |
| D13 | Fix Coqui XTTS capabilities | `coqui_xtts.py` | 15min |
| D14 | Add SynthesisHistory FK | `synthesis_history.py` | 30min |
| D15 | Remove/redirect AdminPage | `App.tsx`, `AdminPage.tsx` | 15min |

### D5 Pattern: Replacing `any` with `unknown`
```typescript
// BEFORE:
catch (e: any) {
  toast.error(e.message);
}

// AFTER — create utils/errors.ts:
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "An unexpected error occurred";
}

// Usage:
catch (error: unknown) {
  toast.error(getErrorMessage(error));
}
```

### D9 Pattern: Standardized Store
```typescript
interface StoreBase {
  loading: boolean;
  error: string | null;
  lastFetchedAt: number | null;
}

// In each store:
fetchProfiles: async () => {
  const { lastFetchedAt } = get();
  if (lastFetchedAt && Date.now() - lastFetchedAt < 30_000) return; // stale check
  set({ loading: true, error: null });
  try {
    const data = await api.listProfiles();
    set({ profiles: data.profiles, loading: false, lastFetchedAt: Date.now() });
  } catch (e: unknown) {
    set({ error: getErrorMessage(e), loading: false });
  }
},
reset: () => set({ profiles: [], loading: false, error: null, lastFetchedAt: null }),
```

---

## Phase E: High-Impact Features [Sessions 9-13]

**Objective:** Add competitive-parity features — pronunciation dictionary, usage analytics, batch synthesis, synthesis history UI, voice cloning wizard, real-time preview, favorites, text import.

### Task Summary
| ID | Task | New Files | Effort |
|----|------|-----------|--------|
| E1 | Pronunciation dictionary | Model, schema, endpoint, store, page | 4hr |
| E2 | Usage analytics dashboard | Model, endpoint, dashboard widget, page | 4hr |
| E3 | Batch synthesis | Celery task, endpoint, WebSocket, UI tab | 3hr |
| E4 | Synthesis history UI | Page, store, API wiring | 3hr |
| E5 | Voice cloning wizard | Multi-step component, MediaRecorder | 4hr |
| E6 | Real-time parameter preview | Debounced synthesis, mini waveform | 3hr |
| E7 | Voice favorites & collections | Model, endpoint, VoiceCard star button | 2hr |
| E8 | Text import (URL, PDF, EPUB) | Backend parser service, import UI | 3hr |

### E1 Implementation Structure
```
NEW FILES:
  backend/app/models/pronunciation_entry.py
  backend/app/schemas/pronunciation.py
  backend/app/api/v1/endpoints/pronunciation.py
  frontend/src/pages/PronunciationPage.tsx
  frontend/src/stores/pronunciationStore.ts
  backend/tests/test_api/test_pronunciation.py

MODIFIED FILES:
  backend/app/models/__init__.py  — register new model
  backend/app/api/v1/router.py   — mount new endpoint
  frontend/src/App.tsx            — add route
  frontend/src/components/layout/Sidebar.tsx — add nav item
  backend/app/services/synthesis_service.py  — apply dict before synthesis
```

### E2 Usage Tracking Integration Point
```python
# In synthesis_service.py, after successful synthesis:
from app.models.usage_event import UsageEvent

usage = UsageEvent(
    id=str(uuid4()),
    provider_name=provider_name,
    profile_id=profile_id,
    voice_id=voice_id,
    characters=len(text),
    duration_ms=result.latency_ms,
    estimated_cost_usd=calculate_cost(provider_name, len(text)),
    event_type="synthesis",
)
db.add(usage)
# Committed by the endpoint's DB session
```

---

## Phase F: Polish & Advanced [Sessions 13-18]

**Objective:** CI/CD improvements, voice emotion controls, format export, provider health dashboard, text preprocessing, keyboard shortcuts, accessibility, webhooks, light image, monitoring.

### Task Summary
| ID | Task | Effort |
|----|------|--------|
| F1 | CI pipeline: frontend tests + security scan + coverage | 2hr |
| F2 | Voice emotion/style UI controls | 3hr |
| F3 | Audio format conversion & export | 2hr |
| F4 | Provider health dashboard | 3hr |
| F5 | Text preprocessing pipeline | 3hr |
| F6 | Keyboard shortcuts | 2hr |
| F7 | WCAG 2.1 AA accessibility | 4hr |
| F8 | Webhook event expansion | 2hr |
| F9 | Light Docker image (cloud-only) | 2hr |
| F10 | Optional monitoring stack | 3hr |

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| A5 (race condition fix) breaks provider behavior | High | Extensive provider-level testing before/after. Feature flag to revert |
| B7 (encryption) makes existing configs unreadable | High | Migration script that encrypts existing plain-text configs. Backup DB first |
| C1 (streaming) introduces memory leaks | Medium | Load test with 100 concurrent streams. Monitor container memory |
| E1-E8 (new features) scope creep | Medium | Strict acceptance criteria per PRD. Ship MVP, iterate later |
| Docker image size increases | Low | Track image size in CI. Alert if > 6GB |

---

## Validation Checklist

### Pre-Implementation
- [x] PRD created and reviewed
- [x] Audit findings documented with file paths
- [x] Codebase patterns researched
- [x] Implementation plan created

### Per-Phase
- [ ] Phase A: All critical fixes pass validation gate
- [ ] Phase B: Zero high-severity security findings
- [ ] Phase C: Streaming synthesis works for 4+ providers
- [ ] Phase D: Zero TypeScript `any`, all stores standardized
- [ ] Phase E: Pronunciation, analytics, batch features functional
- [ ] Phase F: CI passes, accessibility audit clean

### Post-Implementation
- [ ] All P0 requirements from PRD complete
- [ ] All tests passing (`make test-all`)
- [ ] Docker stack builds and runs (`make docker-up`)
- [ ] 80%+ test coverage on critical paths
- [ ] Documentation updated

---

## Success Criteria (from PRD)

- [ ] Zero critical or high-severity security vulnerabilities
- [ ] All 9 providers fully functional in Docker
- [ ] Voice library shows 353+ voices (DONE)
- [ ] All frontend routes functional
- [ ] Concurrent synthesis without race conditions
- [ ] Docker builds < 5 min with cache
- [ ] Pronunciation dictionary, batch synthesis, usage analytics available
- [ ] 80%+ test coverage on critical paths

---

*Generated by Claude Code PRP Framework. Each task references exact file paths and line numbers from the 6-agent audit for direct implementation.*
