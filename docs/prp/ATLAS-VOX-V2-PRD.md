# PRD: Atlas Vox v2.0 — Production Hardening, Feature Completion & Competitive Parity

**Created:** 2026-04-05
**Author:** Claude Code (PRP Framework) via 6-Agent Deep Audit
**Status:** Draft
**Version:** 1.0
**Archon Project:** `f8f125bb-e15e-4632-a4f4-03b6b0870687`
**Audit Reference:** `docs/prp/AUDIT-AND-ROADMAP.md`

---

## Executive Summary

Atlas Vox is an intelligent voice training and TTS customization platform aggregating 9 providers (Kokoro, Coqui XTTS, Piper, ElevenLabs, Azure Speech, StyleTTS2, CosyVoice, Dia, Dia2) across 4 interfaces (Web UI, CLI, REST API, MCP). A comprehensive 6-agent audit identified **166 findings** spanning critical security vulnerabilities, broken features, incomplete implementations, infrastructure gaps, and competitive feature deficits.

This PRD defines the complete scope for taking Atlas Vox from its current ~85% state to a production-ready, security-hardened v2.0 release with competitive parity against ElevenLabs, Play.ht, and Azure Speech Studio.

**Total effort estimate:** 12-18 sessions across 6 phases.

---

## 1. Goal

### Primary Objective
Ship a production-ready Atlas Vox v2.0 that is secure, complete, and competitive — eliminating all critical/high-severity issues (26 items), completing partially-built features (10 items), and adding the 8 highest-impact features identified by competitive analysis.

### Success Metrics
- [ ] Zero critical or high-severity security vulnerabilities (currently 18)
- [ ] All 9 providers fully functional in Docker deployment (currently Piper/Kokoro broken)
- [ ] Voice library shows all 353+ voices from all providers (FIXED)
- [ ] All frontend routes functional with no dead links or blank pages (currently 3 broken)
- [ ] Backend handles concurrent synthesis without race conditions (currently broken)
- [ ] Docker builds complete in <5 min with proper caching (currently ~10 min, broken caching)
- [ ] Pronunciation dictionary, batch synthesis, and usage analytics available
- [ ] 80%+ test coverage on critical paths (currently untested: healing, 7/9 providers, CLI)

---

## 2. Why

### Business Value
- **Market positioning:** Atlas Vox's unique 9-provider aggregation needs security and polish to justify self-hosting vs. using ElevenLabs/Azure directly
- **Enterprise readiness:** Auth gaps, missing rate limits, and root containers block any production deployment
- **Competitive differentiation:** Pronunciation dictionaries, usage analytics, and batch processing are table-stakes features all commercial TTS platforms offer

### User Value
- Users can trust the platform won't corrupt their voice profiles (version compare mutation bug)
- Users can navigate all pages without hitting blank screens (broken routes, missing 404)
- Users get consistent behavior across providers (voice settings race condition fixed)
- Users can process bulk workloads (batch synthesis) and track costs (usage analytics)

### Technical Value
- Eliminates 22 TypeScript `any` types and 7 duplicated type definitions
- Consolidates 4 audio player implementations into 1
- Fixes Docker layer caching (10x faster rebuilds)
- Removes 447-line code duplication between ProviderConfigCard and ProvidersPage

### Risks of Not Implementing
- **Security breach:** Unauthenticated provider config endpoints allow API key theft TODAY
- **Data corruption:** Version comparison silently mutates active profile versions
- **Provider race condition:** Concurrent synthesis produces wrong voice output under load
- **User churn:** Broken navigation, missing 404 pages, and stale data create poor UX

---

## 3. What

### User-Visible Behavior

**Before (v1.x):**
- Voice library truncated to 100 voices (Azure/ElevenLabs missing) *(FIXED)*
- Clicking "Browse Voice Library" from profile dialog → blank page
- Comparing model versions silently changes active version
- Settings page defaults (provider, format) ignored by Synthesis Lab
- No batch synthesis, no usage tracking, no pronunciation dictionary
- Docker containers start without Kokoro/Piper models

**After (v2.0):**
- Full 353+ voice catalog from all 9 providers *(DONE)*
- All navigation links work, 404 page catches unknown routes
- Version comparison is non-destructive
- Settings page defaults applied everywhere
- Batch synthesis with CSV import, usage dashboard with cost breakdown, custom pronunciation dictionary
- Docker containers reliably start with all local models pre-loaded

---

### Functional Requirements

#### Phase A: Critical Fixes (P0 — Must Ship)

| ID | Requirement | Files | Effort |
|----|------------|-------|--------|
| A1 | Add `CurrentUser` dependency to ALL unauthenticated endpoints: providers (6 endpoints), healing (5 endpoints), telemetry (1 endpoint), voices list (1 endpoint), voice preview (1 endpoint) | `providers.py`, `healing/endpoints.py`, `main.py`, `voices.py` | 2hr |
| A2 | Fix VersionCompareModal to synthesize without calling `activateVersion()` — pass `version_id` as query param to synthesis endpoint, restore original active version after compare | `ProfilesPage.tsx:480-484`, `synthesis.py` | 1hr |
| A3 | Fix broken navigation: `navigate("/voice-library")` → `navigate("/library")` | `ProfilesPage.tsx:191` | 10min |
| A4 | Add `<Route path="*" element={<NotFoundPage />} />` catch-all 404 route | `App.tsx`, new `NotFoundPage.tsx` | 15min |
| A5 | Fix provider singleton race condition: pass `voice_settings` as synthesis param instead of mutating shared provider config. Remove `provider.configure()` call from `synthesis_service.synthesize()` | `synthesis_service.py:160-163`, `base.py` | 2hr |
| A6 | Fix Dockerfile model downloads: extract inline `python3 -c` to `docker/scripts/download_piper_model.py` and `docker/scripts/download_kokoro_model.py` | `Dockerfile.backend:53-91` | 1hr |
| A7 | Create `.dockerignore`: `.git`, `.env`, `storage/`, `node_modules/`, `*.db`, `temp/`, `audit-*.png`, `.claude/`, `.playwright-mcp/`, `e2e-screenshots/` | New file at project root | 15min |
| A8 | Fix Docker layer caching: in builder stage, COPY `pyproject.toml` → `pip install` → COPY `app/` (currently copies app before install, invalidating cache) | `Dockerfile.backend:3-6` | 30min |
| A9 | Fix GPU service broken imports: wrap `f5_tts_provider`, `fish_speech`, `openvoice_provider`, `orpheus_provider`, `piper_training_provider` imports in try/except | `gpu-service/app/providers/__init__.py` | 30min |
| A10 | Add Docker health checks to all services + resource limits (backend: 4GB, worker: 8GB, frontend: 256MB, redis: 512MB) | `docker-compose.yml` | 30min |
| A11 | Generate random JWT secret at startup if none provided. Add `JWT_SECRET_KEY` to docker-compose env with `${JWT_SECRET_KEY:-}` pattern. Add minimum length validator (32 chars) | `config.py:36`, `docker-compose.yml` | 30min |
| A12 | Add DB backup script (`scripts/backup-db.sh`), add warning to `make docker-reset`, document PostgreSQL for production | New script, `Makefile` | 1hr |
| A13 | `git add` and commit all untracked Audio Design files (page, store, schemas, tests, timeline component) | 9 untracked files | 15min |
| A14 | Add to `.gitignore`: `.claude/`, `.playwright-mcp/`, `e2e-screenshots/`, `audit-*.png`, `*.db-shm`, `*.db-wal` | `.gitignore` | 10min |
| A15 | Change `output_format: str` to `OutputFormat` enum (`wav`, `mp3`, `ogg`, `flac`) in `SynthesisRequest`, `BatchSynthesisRequest`, `SpeechRequest` | `schemas/synthesis.py`, `openai_compat.py` | 30min |
| A16 | Add `VOICE_SETTINGS_WHITELIST` per provider (e.g., `speed`, `pitch`, `stability`). Reject unknown keys in `voice_settings`. Never allow `api_key`, `subscription_key`, `model_id` | `synthesis_service.py:162`, `schemas/synthesis.py` | 30min |

**Phase A total: ~10.5 hours (2-3 sessions)**

---

#### Phase B: Security Hardening (P0 — Must Ship)

| ID | Requirement | Files | Effort |
|----|------------|-------|--------|
| B1 | Add `require_scope("admin")` to: `update_provider_config`, `delete_provider_config`, `toggle_healing`, `request_review`, API key CRUD, webhook CRUD. Add `require_scope("write")` to: profile mutation, sample upload, training start | All endpoint files | 1hr |
| B2 | Add file size validation: samples upload max 100MB, S2S upload max 50MB, audio design upload max 50MB. Add `client_max_body_size 100m` to nginx | `samples.py`, `audio_tools.py:203`, `audio_tools.py:389`, `nginx.conf` | 30min |
| B3 | Add path traversal protection: validate `Path(filename).resolve()` starts with storage root. Validate file extension is audio format (`.wav`, `.mp3`, `.ogg`, `.flac`, `.opus`). Block `..`, `\`, `/` in raw filenames | `audio.py:28,52,75` | 30min |
| B4 | Add nginx security headers (`X-Content-Type-Options`, `X-Frame-Options`, `CSP`, `Referrer-Policy`, `Permissions-Policy`). Add gzip (`gzip on; gzip_types application/json text/css application/javascript`). Add proxy timeouts (`proxy_read_timeout 300s`) | `nginx.conf` | 30min |
| B5 | Add non-root user to Dockerfiles: `RUN addgroup --system app && adduser --system --ingroup app app` + `USER app`. Use `nginx:unprivileged` variant for frontend | `Dockerfile.backend`, `Dockerfile.frontend`, `Dockerfile.gpu-worker` | 30min |
| B6 | Add `@limiter.limit()` to all write endpoints missing rate limits: profiles CRUD, samples upload, providers config, api-keys, webhooks, audio tools, presets, voice preview | 8 endpoint files | 1hr |
| B7 | Encrypt `config_json` values at rest using Fernet symmetric encryption. Key derived from `JWT_SECRET_KEY` via HKDF. Decrypt on read, encrypt on write. Migrate existing plain-text configs | `provider_registry.py`, `providers.py` endpoint, new `app/core/encryption.py` | 2hr |
| B8 | Add Redis password: configure `requirepass` in docker compose, update `REDIS_URL` to include auth, mask password in startup logs | `docker-compose.yml`, `main.py:40` | 30min |
| B9 | Sanitize all error responses: create `SafeHTTPException` that logs full detail server-side but returns generic message to client. Replace all `detail=str(e)` with sanitized messages | `synthesis.py:71`, `audio_tools.py:193`, `samples.py:281`, `providers.py:323` | 1hr |
| B10 | Add SSML sanitization: whitelist allowed elements (`speak`, `voice`, `prosody`, `break`, `emphasis`, `say-as`, `phoneme`, `sub`, `p`, `s`, `mstts:express-as`). Strip unknown elements. Limit nesting depth to 10 | New `app/services/ssml_sanitizer.py`, `synthesis_service.py` | 1hr |
| B11 | Change `AUTH_DISABLED=true` to `AUTH_DISABLED=${AUTH_DISABLED:-true}` in docker-compose. Set `APP_ENV=production` in docker env | `docker-compose.yml:14` | 10min |
| B12 | Remove tracked `*.db-shm`/`*.db-wal` from git: `git rm --cached backend/atlas_vox.db-shm backend/atlas_vox.db-wal` | Git operation | 10min |

**Phase B total: ~8.5 hours (1-2 sessions)**

---

#### Phase C: Feature Completion (P1 — Should Ship)

| ID | Requirement | Files | Effort |
|----|------------|-------|--------|
| C1 | **Implement real streaming for Kokoro + Coqui XTTS:** Use `asyncio.Queue` bridge pattern — sync generator → queue → async generator. Fix fake streaming in Dia2 and CosyVoice (batch-then-yield → real chunk streaming). Add `POST /api/v1/synthesis/stream` SSE endpoint. Add streaming toggle in Synthesis Lab UI | `kokoro_tts.py`, `coqui_xtts.py`, `dia2.py:149-172`, `cosyvoice.py:187-210`, `synthesis.py`, `SynthesisLabPage.tsx` | 4hr |
| C2 | **Implement clone_voice for CosyVoice + StyleTTS2:** CosyVoice: use zero-shot from reference audio (already supported by model). StyleTTS2: use zero-shot style transfer from reference. Update Training Studio UI to show per-provider capability badges (clone/fine-tune/stream) | `cosyvoice.py`, `styletts2.py`, `TrainingStudioPage.tsx` | 3hr |
| C3 | **Add Whisper-based transcription fallback:** Install `openai-whisper` or `faster-whisper`. Implement `transcribe()` in base provider as fallback when provider doesn't have native transcription. Wire into Training Studio for sample transcription | New `app/services/whisper_transcriber.py`, `base.py:228-230` | 2hr |
| C4 | **Add text chunking for long synthesis:** Implement `TextChunker` service that splits text at sentence/paragraph boundaries respecting provider limits (ElevenLabs: 5000 chars, Azure: 10 min). Auto-concatenate audio chunks with crossfade. Show chunking progress in UI | New `app/services/text_chunker.py`, `synthesis_service.py` | 2hr |
| C5 | **Add Alembic migrations to Docker startup:** Add `alembic upgrade head` to `init-models.sh` before app launch. Handle first-run (no migration history) gracefully | `docker/scripts/init-models.sh` | 30min |
| C6 | **Expand MCP tool coverage:** Add tools for: training management (`start_training`, `get_training_status`, `cancel_training`), comparison (`compare_voices`), provider config (`list_providers`, `configure_provider`), audio tools (`normalize`, `trim`, `effects`) | `mcp/tools.py` | 2hr |
| C7 | **Remove English-only filter from Azure voices:** Delete the `if locale.startswith("en")` filter in `azure_speech.py:869`. Add all 400+ Azure voices across 140+ languages. Update frontend language filter to show all available languages | `azure_speech.py:869`, `VoiceLibraryPage.tsx` language map | 30min |
| C8 | **Add word boundary estimation fallback:** Use `faster-whisper` with `word_timestamps=True` to generate word-level timing from synthesized audio. Return as `word_boundaries` in synthesis response for non-Azure providers | New `app/services/word_boundary_estimator.py`, `synthesis_service.py` | 3hr |

**Phase C total: ~17 hours (2-3 sessions)**

---

#### Phase D: Code Quality (P1 — Should Ship)

| ID | Requirement | Files | Effort |
|----|------------|-------|--------|
| D1 | Wire `settingsStore.defaultProvider` and `settingsStore.audioFormat` into SynthesisLabPage initial state | `SynthesisLabPage.tsx:48`, `settingsStore.ts` | 30min |
| D2 | Extract shared `ConfigField` and `ProviderConfigPanel` components from the two duplicate implementations. Delete AdminPage or redirect `/admin` → `/providers` | `ProviderConfigCard.tsx`, `ProvidersPage.tsx:300-633`, `AdminPage.tsx`, new `components/providers/ConfigField.tsx` | 2hr |
| D3 | Move all locally-defined types to `types/index.ts`: `AudioDesignFile`, `AudioClip` → `AudioFile`; `AudioDesignQuality`, `QualityBrief` → `AudioQuality`; `HealingStatus`, `Incident`, `QualityResult`, `ReadinessResult`, `VersionInfo` | `types/index.ts`, `api.ts`, `audioDesignStore.ts`, `HealingPage.tsx`, `TrainingStudioPage.tsx`, `ProfilesPage.tsx` | 1hr |
| D4 | Fix blob URL memory leak: use `useRef` to track previous URL, call `URL.revokeObjectURL()` in cleanup. Apply same pattern to AudioDesignPage if applicable | `SynthesisLabPage.tsx:231` | 30min |
| D5 | Replace all 22 `catch (e: any)` with `catch (e: unknown)`. Create `getErrorMessage(e: unknown): string` utility. Apply across: `ProviderConfigCard.tsx`, `HealingPage.tsx`, `ProfilesPage.tsx`, `VoiceLibraryPage.tsx`, `AudioPlayer.tsx`, `AudioTimeline.tsx`, `DashboardPage.tsx` | 7 files + new `utils/errors.ts` | 2hr |
| D6 | Create `useAudioPlayer` hook + `AudioPlayer` component. Replace 4 separate implementations in VoiceLibraryPage (VoiceCard), ComparisonPage, SynthesisLabPage, AudioDesignPage. Support: play/pause/stop, seek, volume, playback rate | New `hooks/useAudioPlayer.ts`, `components/audio/AudioPlayerUnified.tsx` | 2hr |
| D7 | Create `<VoicePicker>` component with search, provider/language/gender filters, preview button. Replace voice selection in: SynthesisLab (dropdown), Profiles (dialog), TrainingStudio (selector), Comparison (two dropdowns) | New `components/voice/VoicePicker.tsx` | 2hr |
| D8 | Standardize backend error responses: create `AppException` hierarchy extending `HTTPException`. All endpoints return `{"detail": "...", "code": "..."}`. Remove `{"error": ...}` and `{"message": ...}` variants | New `app/core/exceptions.py`, update all endpoint files | 1hr |
| D9 | Standardize store pattern: every store gets `loading`, `error`, `lastFetchedAt` fields + `fetch*()`, `reset()` actions. Add staleness check: skip refetch if `lastFetchedAt` < 30s ago. Apply to all 10 stores | All 10 store files | 2hr |
| D10 | Remove duplicate `get_db()` from `database.py:58`. Update `health.py:19` to import `DbSession` from `dependencies.py`. Update all imports to use canonical location | `database.py`, `health.py`, `providers.py` endpoint | 15min |
| D11 | Add `<ErrorBoundary>` wrapper around each `<Route>` element in App.tsx. Create `ErrorFallback` component with "Something went wrong" message + retry button | `App.tsx`, new `components/ErrorFallback.tsx` | 1hr |
| D12 | Add `react-virtuoso` to Voice Library page for virtual scrolling. Only render visible cards. Maintain current filter/search functionality | `VoiceLibraryPage.tsx`, `package.json` | 1hr |
| D13 | Set `supports_fine_tuning=False` in Coqui XTTS `get_capabilities()`. Change `fine_tune()` to raise `NotImplementedError` | `coqui_xtts.py:170-208` | 15min |
| D14 | Add `ForeignKey("voice_profiles.id")` to `SynthesisHistory.profile_id`. Add null check for `output_path` in synthesis history endpoint | `synthesis_history.py:19`, `synthesis.py:168` | 30min |
| D15 | Delete `AdminPage.tsx` or change route to redirect: `<Route path="/admin" element={<Navigate to="/providers" replace />} />` | `App.tsx`, optionally delete `AdminPage.tsx` | 15min |

**Phase D total: ~16 hours (2-3 sessions)**

---

#### Phase E: High-Impact Features (P2 — Should Ship)

| ID | Requirement | Spec | Effort |
|----|------------|------|--------|
| E1 | **Pronunciation Dictionary / Custom Lexicon** | New `pronunciation_entry` model (word, ipa, phoneme, language, provider_hint). CRUD API at `/api/v1/pronunciation`. Apply as SSML `<phoneme>` tags before synthesis. UI: dictionary editor page accessible from Settings. Import/export as CSV. Per-profile overrides | 4hr |
| E2 | **Usage Analytics & Cost Tracking** | New `usage_event` table (timestamp, provider, chars, duration_ms, estimated_cost_usd, profile_id). Record on every synthesis. Dashboard widget: total chars this month, cost by provider (bar chart), daily usage (line chart), top voices. Provider cost config (cents per 1K chars) in Settings. Export as CSV | 4hr |
| E3 | **Batch Processing / Bulk Synthesis** | `POST /api/v1/synthesis/batch` accepts `{lines: string[], provider, voice_id, output_format}`. Celery task processes each line. WebSocket progress updates. UI: "Batch Mode" tab in Synthesis Lab with textarea (one line per synthesis) or CSV upload. Show per-line status (pending/processing/done/error). Download all as ZIP | 3hr |
| E4 | **Synthesis History UI** | New page at `/history`. Table with columns: text (truncated), provider, voice, duration, created_at. Audio playback inline. Filter by provider/date range. Star favorites. "Re-synthesize" button pre-fills Synthesis Lab. "Download" button. Pagination (50 per page). Delete old entries | 3hr |
| E5 | **Voice Cloning Wizard** | Multi-step form at `/training/clone`: Step 1: Record audio (MediaRecorder API) or upload files. Step 2: Automatic preprocessing (noise reduction, normalization) with quality score. Step 3: Provider selection (auto-recommend based on sample quality + provider capabilities). Step 4: Clone execution with progress. Step 5: Quality check (A/B comparison with original). Step 6: Save as profile | 4hr |
| E6 | **Real-Time Parameter Preview** | Debounced preview (300ms) when adjusting speed/pitch/style sliders in Synthesis Lab. Use short preview text (first sentence or custom). For streaming providers: pipe chunks directly. Show mini-waveform during preview. Cache recent previews | 3hr |
| E7 | **Voice Favorites & Collections** | New `voice_favorite` table (user_id, provider, voice_id, collection_id). Heart/star button on every VoiceCard. "My Favorites" filter in Voice Library. Named collections ("Project Alpha voices", "Audiobook narrators"). Drag-and-drop collection management | 2hr |
| E8 | **Text Import (URL, PDF, EPUB)** | "Import" button in Synthesis Lab. Three sources: URL (fetch + readability extraction), File upload (PDF via pdfplumber, TXT, EPUB via ebooklib, DOCX via python-docx). Show extracted text in editor. Handle pagination for long documents. Strip images/tables | 3hr |

**Phase E total: ~26 hours (3-4 sessions)**

---

#### Phase F: Polish & Advanced (P2 — Nice to Have)

| ID | Requirement | Spec | Effort |
|----|------------|------|--------|
| F1 | **CI Pipeline Enhancement** | Add `frontend-test` job running `npm run test`. Add `pip-audit` + `npm audit --audit-level=high`. Add coverage reporting with `--cov-fail-under=50`. Add Trivy container scan on Docker images. Add `gpu-service-lint` job | `.github/workflows/ci.yml` | 2hr |
| F2 | **Voice Emotion/Style Controls** | Style selector dropdown in Synthesis Lab. Populate from Azure voice metadata (`StyleList`). For Azure: inject `<mstts:express-as style="...">`. For ElevenLabs: map to stability/similarity_boost. For others: show available params. Show style preview audio | 3hr |
| F3 | **Audio Format Conversion & Export** | Format selector in Synthesis Lab (WAV, MP3, OGG, FLAC, AAC). Quality presets (low/medium/high/lossless). FFmpeg-based conversion. Batch export from history. Show file size estimate | 2hr |
| F4 | **Provider Health Dashboard** | Surface self-healing engine data: provider uptime %, avg latency chart (7d), error rate trend, last health check timestamp. Auto-detect degradation. Show recommended actions. Link to provider config for remediation | 3hr |
| F5 | **Text Preprocessing Pipeline** | Number expansion (123 → "one hundred twenty-three"), abbreviation expansion, date formatting (2026-04-05 → "April fifth, twenty twenty-six"), URL handling (skip or read domain), code block detection (skip). Configurable rules in Settings. Show "normalized text" preview in Synthesis Lab | 3hr |
| F6 | **Keyboard Shortcuts** | `Space` = play/pause audio. `Ctrl+Enter` = synthesize. `Ctrl+K` = quick voice search. `Ctrl+S` = save profile. `Escape` = close modal. `/` = focus search. `?` = show shortcuts help. Use `useHotkeys` hook. Show in tooltips | 2hr |
| F7 | **WCAG 2.1 AA Accessibility** | Add ARIA labels to all interactive elements. Add `skip-to-content` link. Ensure keyboard navigation for audio player, voice cards, modals. Add `aria-describedby` for form errors. Add `role="alert"` for toasts. Test with screen reader (NVDA) | 4hr |
| F8 | **Webhook Event Expansion** | Define event types: `synthesis.complete`, `training.complete`, `training.failed`, `health.alert`, `usage.threshold`. Fire from Celery tasks and healing engine. Add webhook test/ping button in UI. Add webhook history log | 2hr |
| F9 | **Light Docker Image** | Create `Dockerfile.backend-light` with only cloud provider deps (ElevenLabs SDK, Azure SDK). No PyTorch, no local models. ~500MB vs ~5GB. Document use case: "Cloud-only mode for minimal resource deployments" | 2hr |
| F10 | **Monitoring Stack** | Optional `docker-compose.monitoring.yml` overlay with Prometheus + Grafana. Add `/metrics` endpoint using `prometheus-fastapi-instrumentator`. Pre-built Grafana dashboard: request rate, latency percentiles, error rate, provider health, queue depth | 3hr |

**Phase F total: ~26 hours (2-3 sessions)**

---

### Non-Functional Requirements

| Category | Requirement | Target |
|----------|------------|--------|
| **Performance** | Voice library page load (353 voices) | < 2s |
| **Performance** | Synthesis latency (Kokoro, short text) | < 3s |
| **Performance** | Docker build time (with cache hit) | < 2 min |
| **Performance** | Docker build time (cold, no cache) | < 10 min |
| **Security** | All endpoints require authentication when enabled | 100% coverage |
| **Security** | No raw exception details in API responses | 100% coverage |
| **Security** | Containers run as non-root | All 4 services |
| **Security** | Provider API keys encrypted at rest | Fernet encryption |
| **Reliability** | Docker health checks detect unhealthy containers | < 60s detection |
| **Reliability** | Database backup before destructive operations | Automated |
| **Scalability** | Concurrent synthesis requests without race conditions | 10+ concurrent |
| **Accessibility** | WCAG 2.1 AA compliance | All interactive elements |
| **Testing** | Critical path test coverage | > 80% |
| **Testing** | Provider integration test coverage | All 9 providers |

---

## 4. Context

### Codebase Architecture
```
atlas-vox/
├── backend/app/
│   ├── api/v1/endpoints/   # 14 endpoint modules
│   ├── providers/          # 9 TTS providers + base + remote
│   ├── services/           # 8 service modules
│   ├── models/             # 9 SQLAlchemy models
│   ├── schemas/            # 10 Pydantic schema modules
│   ├── healing/            # Self-healing engine (8 modules)
│   ├── mcp/                # MCP server (3 modules)
│   └── cli/commands/       # 7 CLI command modules
├── frontend/src/
│   ├── pages/              # 15 React pages
│   ├── stores/             # 10 Zustand stores
│   ├── components/         # UI components (audio, admin, layout, ui, providers)
│   ├── services/api.ts     # Centralized API client
│   └── types/index.ts      # TypeScript interfaces
├── docker/
│   ├── Dockerfile.backend  # Multi-stage Python build
│   ├── Dockerfile.frontend # Multi-stage Node + nginx
│   ├── docker-compose.yml  # 4-service stack
│   └── nginx.conf          # Reverse proxy
└── gpu-service/            # Standalone GPU provider service
```

### Key Dependencies
| Dependency | Purpose | Version |
|-----------|---------|---------|
| FastAPI | API framework | 0.100+ |
| SQLAlchemy (async) | ORM | 2.0 |
| Celery + Redis | Task queue | 5.x / 7.x |
| React + TypeScript | Frontend | 18 / 5 |
| Zustand | State management | 4.x |
| PyTorch | Local TTS models | 2.11 |
| slowapi | Rate limiting | Latest |
| structlog | Logging | Latest |

### Constraints
- **Platform:** Windows 11 Enterprise (Intune-managed) — cannot modify security software
- **Database:** SQLite default, PostgreSQL optional — no breaking schema changes
- **Docker:** Must work with Docker Desktop on Windows (WSL2 backend)
- **Backward compatibility:** Existing voice profiles, synthesis history, and provider configs must be preserved through all changes

---

## 5. User Stories

### Story A1: Secure Provider Configuration
**As a** platform administrator,
**I want to** ensure only authenticated admins can view or modify provider API keys,
**so that** my ElevenLabs and Azure credentials can't be stolen by unauthenticated requests.

**Acceptance Criteria:**
- [ ] `GET /providers/{name}/config` returns 401 without valid auth token
- [ ] `PUT /providers/{name}/config` requires admin scope
- [ ] Provider API keys are encrypted at rest in the database
- [ ] Error messages don't leak internal details or API keys

### Story A2: Non-Destructive Version Comparison
**As a** voice profile owner,
**I want to** compare two model versions side-by-side,
**so that** I can choose the best version without changing my active version.

**Acceptance Criteria:**
- [ ] Clicking "Compare" in version modal does NOT call `activateVersion()`
- [ ] Both versions synthesize correctly using version_id parameter
- [ ] Active version remains unchanged after comparison completes
- [ ] A/B playback works with synchronized controls

### Story C1: Streaming Synthesis
**As a** user synthesizing long text,
**I want to** hear audio as it generates in real-time,
**so that** I don't have to wait for the entire synthesis to complete before hearing anything.

**Acceptance Criteria:**
- [ ] Toggle "Streaming" in Synthesis Lab enables SSE-based audio delivery
- [ ] Kokoro and Coqui XTTS deliver real audio chunks (not batch-then-yield)
- [ ] Waveform updates progressively as chunks arrive
- [ ] Fallback to non-streaming for providers that don't support it

### Story E1: Pronunciation Dictionary
**As a** content creator working with domain-specific terminology,
**I want to** define custom pronunciations for words like "GIF", "SQL", or brand names,
**so that** synthesized audio pronounces them correctly every time.

**Acceptance Criteria:**
- [ ] Dictionary editor page accessible from Settings
- [ ] CRUD for pronunciation entries (word, IPA, language)
- [ ] Entries automatically applied as SSML `<phoneme>` before synthesis
- [ ] Import/export as CSV
- [ ] Per-profile pronunciation overrides

### Story E2: Usage Analytics
**As a** platform administrator,
**I want to** see how many characters each provider has synthesized and estimated costs,
**so that** I can optimize my provider mix and budget.

**Acceptance Criteria:**
- [ ] Dashboard widget showing: total chars this month, cost breakdown by provider
- [ ] Daily usage chart (line graph) with provider breakdown
- [ ] Top 10 most-used voices
- [ ] Configurable cost per 1K characters per provider
- [ ] Export usage data as CSV

### Story E3: Batch Synthesis
**As a** audiobook producer,
**I want to** submit a list of 100+ text segments for synthesis,
**so that** I can process an entire chapter overnight without manual intervention.

**Acceptance Criteria:**
- [ ] "Batch Mode" tab in Synthesis Lab
- [ ] Accept text list (one per line) or CSV upload
- [ ] Process via Celery queue with progress updates
- [ ] Per-line status indicators (pending/processing/done/error)
- [ ] Download all results as ZIP
- [ ] Cancel batch operation mid-flight

---

## 6. Technical Considerations

### Architecture Impact
- **Phase A:** No architectural changes. Primarily adding auth dependencies and fixing existing patterns
- **Phase B:** New `encryption.py` module for Fernet encryption. New `ssml_sanitizer.py` service
- **Phase C:** New streaming SSE endpoint. New `text_chunker.py` and `whisper_transcriber.py` services
- **Phase D:** Shared component extraction. Store pattern standardization. No backend changes
- **Phase E:** 3 new database models (`pronunciation_entry`, `usage_event`, `voice_favorite`). 2 new API endpoint modules. 2 new frontend pages
- **Phase F:** Optional monitoring overlay. CI/CD expansion. No core architecture changes

### Data Model Changes

**New Models (Phase E):**

```python
class PronunciationEntry(Base):
    __tablename__ = "pronunciation_entries"
    id = Column(String(36), primary_key=True)
    word = Column(String(255), nullable=False, index=True)
    ipa = Column(String(500), nullable=False)
    language = Column(String(10), default="en")
    profile_id = Column(String(36), ForeignKey("voice_profiles.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)

class UsageEvent(Base):
    __tablename__ = "usage_events"
    id = Column(String(36), primary_key=True)
    provider_name = Column(String(50), nullable=False, index=True)
    profile_id = Column(String(36), nullable=True)
    voice_id = Column(String(255))
    characters = Column(Integer, nullable=False)
    duration_ms = Column(Integer)
    estimated_cost_usd = Column(Float)
    event_type = Column(String(20))  # "synthesis", "clone", "training"
    created_at = Column(DateTime, default=utcnow, index=True)

class VoiceFavorite(Base):
    __tablename__ = "voice_favorites"
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    voice_id = Column(String(255), nullable=False)
    collection_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)
```

**Modified Models:**
- `SynthesisHistory`: Add `ForeignKey("voice_profiles.id")` to `profile_id` (Phase D)

### API Changes

**New Endpoints:**
| Method | Path | Phase | Description |
|--------|------|-------|-------------|
| POST | `/api/v1/synthesis/stream` | C | SSE streaming synthesis |
| GET | `/api/v1/pronunciation` | E | List pronunciation entries |
| POST | `/api/v1/pronunciation` | E | Create entry |
| PUT | `/api/v1/pronunciation/{id}` | E | Update entry |
| DELETE | `/api/v1/pronunciation/{id}` | E | Delete entry |
| POST | `/api/v1/pronunciation/import` | E | Import CSV |
| GET | `/api/v1/pronunciation/export` | E | Export CSV |
| GET | `/api/v1/usage` | E | Usage analytics |
| GET | `/api/v1/usage/export` | E | Export CSV |
| POST | `/api/v1/synthesis/batch` | E | Batch synthesis |
| GET | `/api/v1/synthesis/batch/{id}` | E | Batch status |
| DELETE | `/api/v1/synthesis/batch/{id}` | E | Cancel batch |
| GET | `/api/v1/favorites` | E | List favorites |
| POST | `/api/v1/favorites` | E | Add favorite |
| DELETE | `/api/v1/favorites/{id}` | E | Remove favorite |
| POST | `/api/v1/synthesis/import-text` | E | Import text from URL/file |

**Modified Endpoints:**
| Method | Path | Phase | Change |
|--------|------|-------|--------|
| ALL | `/api/v1/providers/*` | A | Add `CurrentUser` dependency |
| ALL | `/api/v1/healing/*` | A | Add `CurrentUser` + admin scope |
| GET | `/api/v1/telemetry` | A | Add `CurrentUser` + admin scope |
| POST | `/api/v1/synthesis/synthesize` | A | Validate `output_format` enum, whitelist `voice_settings` |

### Security Considerations
- **Encryption key management:** Fernet key derived from JWT_SECRET_KEY via HKDF. If JWT secret changes, stored encrypted configs become unreadable. Migration path: re-encrypt with new key
- **Rate limit bypass:** slowapi uses IP-based limiting. Behind nginx proxy, must use `X-Forwarded-For` header. Verify `get_remote_address` reads the correct header
- **SSML injection:** The sanitizer must handle Azure-specific SSML extensions (`mstts:*`) carefully — allow known-safe elements while blocking potentially dangerous ones

---

## 7. Out of Scope

Explicitly NOT included in this PRD:
- Multi-tenant SaaS deployment (shared infrastructure for multiple organizations)
- Payment processing or billing integration
- Mobile app (iOS/Android)
- Real-time voice conversation (full-duplex streaming)
- Custom TTS model training from scratch (only fine-tuning and cloning)
- GPU auto-scaling (manual GPU service configuration only)
- Migration from SQLite to PostgreSQL (documented as optional, not automated)
- New TTS provider integrations (Fish Speech, GPT-SoVITS, OpenVoice) — deferred to v2.1
- Plugin/extension system — deferred to v3.0

---

## 8. Open Questions

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should we switch Docker deployments to PostgreSQL by default instead of SQLite? The SQLite concurrency issue (Finding 7.9) is a real problem with backend + worker sharing a volume | Phase A | Architect |
| 2 | How should the Fernet encryption key be managed when the JWT secret changes? Re-encrypt all stored configs? | Phase B | Security |
| 3 | Should the pronunciation dictionary be applied globally or per-request? Global auto-apply could surprise users | Phase E | Product |
| 4 | For batch synthesis, what's the maximum batch size? 100? 1000? Need to balance Celery queue depth with user expectations | Phase E | Product |
| 5 | Should voice favorites sync across devices (requires auth) or be browser-local (localStorage)? | Phase E | Product |
| 6 | Is the Audio Design page a standalone feature or should it be merged into Synthesis Lab as a "Post-Processing" tab? | Phase D | UX |
| 7 | Should the GPU service provider imports be fixed (try/except wrapping) or should the missing providers (Fish Speech, OpenVoice, etc.) be implemented now? | Phase A | Engineering |

---

## 9. Timeline Estimate

| Phase | Sessions | Hours | Description |
|-------|----------|-------|-------------|
| **A: Critical Fixes** | 2-3 | ~10.5 | Auth gaps, broken navigation, race condition, Docker fixes |
| **B: Security Hardening** | 1-2 | ~8.5 | Scopes, upload limits, headers, non-root, encryption |
| **C: Feature Completion** | 2-3 | ~17 | Streaming, cloning, transcription, chunking |
| **D: Code Quality** | 2-3 | ~16 | Types, components, stores, error handling |
| **E: High-Impact Features** | 3-4 | ~26 | Pronunciation, analytics, batch, history, wizard |
| **F: Polish & Advanced** | 2-3 | ~26 | CI, emotion controls, format export, monitoring |
| **Total** | **12-18** | **~104** | |

### Phase Dependencies
```
Phase A ──→ Phase B ──→ Phase C ──┐
                                  ├──→ Phase E ──→ Phase F
Phase A ──→ Phase D ──────────────┘
```

Phases A and D can run in parallel after A completes (D has no security dependencies).
Phase E requires B (auth for new endpoints) and C (streaming for batch) to be complete.
Phase F is independently implementable after A.

---

## 10. Approval

| Role | Name | Status | Date |
|------|------|--------|------|
| Product Owner | | Pending | |
| Tech Lead | | Pending | |
| Security | | Pending | |

---

## Appendix A: Provider Capability Matrix

| Provider | synthesize | list_voices | clone_voice | fine_tune | stream | word_bounds | transcribe |
|----------|-----------|-------------|-------------|-----------|--------|-------------|------------|
| Kokoro | Yes | Yes (54) | No | No | **Planned C1** | No | **Fallback C3** |
| Coqui XTTS | Yes | Yes (43) | Yes | **Stub (fix D13)** | **Planned C1** | No | **Fallback C3** |
| Piper | Yes | Yes (40) | No | No | No | No | **Fallback C3** |
| ElevenLabs | Yes | Yes (45) | Yes | Dashboard | Yes | No | **Fallback C3** |
| Azure Speech | Yes | Yes (159→400+ C7) | Yes (Portal) | Yes (CNV) | Yes | Yes | Yes |
| StyleTTS2 | Yes | Yes (1) | **Planned C2** | No | No | No | **Fallback C3** |
| CosyVoice | Yes | Yes (7) | **Planned C2** | No | **Fix fake C1** | No | **Fallback C3** |
| Dia | Yes | Yes (2) | No | No | No | No | **Fallback C3** |
| Dia2 | Yes | Yes (2) | No | No | **Fix fake C1** | No | **Fallback C3** |

**Bold** = Changes in this PRD. Normal = Existing state.

## Appendix B: Competitive Analysis Summary

| Feature | Atlas Vox | ElevenLabs | Azure Studio | Play.ht | Murf.ai |
|---------|----------|------------|-------------|---------|---------|
| Multi-provider | **9 providers** | 1 | 1 | 1 | 1 |
| Self-hosted | **Yes** | No | No | No | No |
| Voice library | **353+ voices** | 1200+ | 400+ | 900+ | 200+ |
| Pronunciation dict | **Planned E1** | Yes | Yes | No | No |
| Usage analytics | **Planned E2** | Yes | Yes | Yes | Yes |
| Batch synthesis | **Planned E3** | No | Yes | Yes | No |
| Streaming | Partial→**C1** | Yes | Yes | Yes | No |
| Voice cloning | 3/9→**5/9 C2** | Yes | Yes | Yes | No |
| A/B comparison | **Yes** | No | No | No | No |
| SSML editor | **Yes** | No | Yes | No | No |
| Voice favorites | **Planned E7** | Yes | No | Yes | No |
| Text import | **Planned E8** | No | No | No | Yes |
| Emotion controls | **Planned F2** | Yes | Yes | Yes | No |
| Cost transparency | **Planned E2** | Limited | Azure Portal | No | No |

## Appendix C: Files Referenced

### Critical Fix Files
```
backend/app/api/v1/endpoints/providers.py    — Missing auth (A1)
backend/app/healing/endpoints.py             — Missing auth (A1)
backend/app/main.py                          — Telemetry auth (A1)
frontend/src/pages/ProfilesPage.tsx          — Version mutation (A2), broken nav (A3)
frontend/src/App.tsx                         — 404 route (A4)
backend/app/services/synthesis_service.py    — Race condition (A5)
docker/Dockerfile.backend                    — Model downloads (A6), caching (A8)
docker/docker-compose.yml                    — Health checks (A10), JWT (A11)
backend/app/schemas/synthesis.py             — output_format (A15), voice_settings (A16)
```

### Security Files
```
docker/nginx.conf                            — Headers (B4), body size (B2)
docker/Dockerfile.backend                    — Non-root (B5)
backend/app/api/v1/endpoints/audio.py        — Path traversal (B3)
backend/app/core/encryption.py               — NEW: Fernet encryption (B7)
backend/app/services/ssml_sanitizer.py       — NEW: SSML sanitizer (B10)
```

### New Feature Files (Phase E)
```
backend/app/models/pronunciation_entry.py    — NEW
backend/app/models/usage_event.py            — NEW
backend/app/models/voice_favorite.py         — NEW
backend/app/api/v1/endpoints/pronunciation.py — NEW
backend/app/api/v1/endpoints/usage.py        — NEW
backend/app/api/v1/endpoints/favorites.py    — NEW
frontend/src/pages/HistoryPage.tsx           — NEW
frontend/src/pages/PronunciationPage.tsx     — NEW
frontend/src/stores/historyStore.ts          — NEW
frontend/src/stores/pronunciationStore.ts    — NEW
frontend/src/stores/usageStore.ts            — NEW
frontend/src/stores/favoritesStore.ts        — NEW
```

---

*Generated by Claude Code PRP Framework via 6-agent comprehensive audit. All findings include file paths and line numbers for direct implementation.*
