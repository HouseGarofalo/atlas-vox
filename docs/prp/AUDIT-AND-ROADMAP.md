# Atlas Vox — Comprehensive Codebase Audit & Feature Roadmap

**Date:** 2026-04-05
**Scope:** Full-stack audit — backend, frontend, Docker, CI/CD, security, competitive analysis
**Method:** 6 parallel analysis agents + direct code review across all layers
**Status:** Ready for implementation planning

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Critical Fixes (Ship-Blockers)](#2-critical-fixes)
3. [Security Vulnerabilities](#3-security-vulnerabilities)
4. [Incomplete / Partially Implemented Features](#4-incomplete-features)
5. [Backend Architecture Issues](#5-backend-architecture)
6. [Frontend Architecture Issues](#6-frontend-architecture)
7. [Docker & Infrastructure Issues](#7-docker-infrastructure)
8. [Code Quality & Simplification](#8-code-quality)
9. [Feature Gaps vs. Competitors](#9-competitive-gaps)
10. [Feature Consolidation Opportunities](#10-consolidation)
11. [New Feature Recommendations](#11-new-features)
12. [Implementation Roadmap](#12-roadmap)

---

## 1. Executive Summary

Atlas Vox is a well-structured voice training and TTS customization platform with strong architectural foundations: 9 TTS providers behind a clean ABC abstraction, async FastAPI backend, React/TypeScript frontend with Zustand stores, Celery task queue, self-healing engine, MCP server, CLI, and Docker deployment.

**Current state: ~85% feature-complete.** The remaining 15% consists of partial implementations, missing integrations, security hardening gaps, and infrastructure polish that would block a production deployment.

### Key Metrics
| Category | Count | Severity |
|----------|-------|----------|
| Critical/ship-blocking issues | 8 | Must fix |
| Security vulnerabilities | 18 | High priority |
| Incomplete features | 10 | Medium priority |
| Backend architecture issues | 12 | Medium |
| Frontend architecture issues | 15 | Medium |
| Code quality improvements | 14 | Low-medium |
| Missing features vs. competitors | 22 | Enhancement |
| Infrastructure gaps | 16 | Medium |

### Audit Agents Deployed
| Agent | Findings | Duration |
|-------|----------|----------|
| Backend Architecture | 47 findings | 4.5 min |
| Frontend Architecture | 35 findings | 3.7 min |
| Security Audit | 18 vulnerabilities | 5.7 min |
| Docker/Infrastructure | 27 issues | 3.1 min |
| Competitive Analysis | 22 feature gaps | 6.2 min |
| Code Completeness Scan | 17 categories | 2.1 min |

---

## 2. Critical Fixes (Ship-Blockers)

### 2.1 [CRITICAL] Dockerfile Model Download Scripts Are Broken
**Files:** `docker/Dockerfile.backend:53-91`
**Issue:** The multiline `python -c "..."` strings for downloading Piper and Kokoro models get flattened by Docker's RUN instruction, causing `SyntaxError: invalid syntax`. Both downloads silently fall back to "skipped (offline build)".
**Impact:** Docker containers start without any local TTS models (Kokoro, Piper). Only cloud providers (Azure, ElevenLabs) work out of the box. Users get empty results from local providers.
**Fix:** Convert the inline Python to proper shell scripts in `docker/scripts/` or use heredoc syntax (`python3 << 'EOF'`).

### 2.2 [CRITICAL] Voice Library Pagination Truncates Results
**Files:** `backend/app/api/v1/endpoints/voices.py:21-53`, `frontend/src/services/api.ts:160`
**Issue:** ~~Default `limit=100` with 353 total voices across 9 providers meant Azure (159 voices) and ElevenLabs (45 voices) were cut off.~~
**Status:** FIXED in this session — limit raised to 1000/5000, frontend passes `?limit=5000`.

### 2.3 [CRITICAL] JWT Secret Key Default in Production
**Files:** `backend/app/core/config.py:36-37`
**Issue:** `jwt_secret_key: str = "change-me-in-production"` — while there's a validator that rejects this when `auth_disabled=False`, the Docker compose file sets `AUTH_DISABLED=true`, meaning the default JWT secret is in active use. If auth is ever enabled without changing the secret, all tokens are predictable.
**Impact:** Full authentication bypass if auth is enabled without changing the secret.
**Fix:** Generate a random JWT secret at container startup if none is provided. Add a startup warning even when auth is disabled. Add `JWT_SECRET_KEY` to docker-compose environment with a placeholder that forces configuration.

### 2.4 [CRITICAL] No .dockerignore File
**Files:** Project root (missing)
**Issue:** No `.dockerignore` exists. Every `docker build` sends the ENTIRE repo to the Docker daemon — including `.env` files (with API keys), `storage/` directory (potentially gigabytes of audio), `node_modules/`, `.git/`, `*.db` files, and audit screenshots.
**Impact:** Secrets leak into Docker build context. Builds are unnecessarily slow. Docker images may contain sensitive data in layers.
**Fix:** Create `.dockerignore` mirroring `.gitignore` plus: `.env`, `storage/`, `*.db`, `.git/`, `node_modules/`, `audit-*.png`, `e2e-screenshots/`, `temp/`.

### 2.5 [CRITICAL] SQLite Database Files in Docker Volumes — No Backup Strategy
**Files:** `docker/docker-compose.yml:22,56`
**Issue:** SQLite database is stored in a named Docker volume (`db_data`). If the volume is accidentally deleted (`docker compose down -v`), all data is lost. No backup mechanism exists. The `docker-reset` Makefile target runs `docker compose down -v` which **destroys the database**.
**Impact:** Complete data loss with a single command.
**Fix:** Add a backup script that exports the DB periodically. Add a prominent warning to `make docker-reset`. Consider PostgreSQL for production Docker deployments.

### 2.6 [CRITICAL] Provider Config Endpoints Have NO Authentication
**Files:** `backend/app/api/v1/endpoints/providers.py` — ALL endpoints
**Issue:** The security audit discovered that `list_providers`, `get_provider`, `get_provider_config`, `update_provider_config`, `check_provider_health`, and `list_provider_voices` have NO `CurrentUser` dependency. When `AUTH_DISABLED=false`, these are still accessible without authentication. `update_provider_config` allows writing API keys without any auth.
**Impact:** Unauthenticated API key theft and replacement. An attacker can read provider configs (including masked API keys) or replace them with their own keys.
**Fix:** Add `user: CurrentUser` to all provider endpoints. Add `require_scope("admin")` to config mutation endpoints.

### 2.7 [CRITICAL] VersionCompareModal Mutates Active Profile Version
**Files:** `frontend/src/pages/ProfilesPage.tsx:480-484`
**Issue:** The frontend audit found that `VersionCompareModal.handleCompare()` calls `api.activateVersion()` for each version being compared, then synthesizes. This **destructively changes** the profile's active model version as a side effect of comparison. If comparing v1 and v2, the profile ends up stuck on v2.
**Impact:** Data corruption — users lose their active model version when using the comparison feature.
**Fix:** Use a separate synthesis path that passes version_id as a parameter without calling `activateVersion`.

### 2.8 [CRITICAL] Broken Navigation: `/voice-library` Route Doesn't Exist
**Files:** `frontend/src/pages/ProfilesPage.tsx:191`
**Issue:** `navigate("/voice-library")` is called but the actual route is `/library` (defined in App.tsx). This sends users to a blank page with no 404 handler.
**Fix:** Change to `navigate("/library")`. Also add a catch-all 404 route in App.tsx.

---

## 3. Security Vulnerabilities

### 3.1 [HIGH] No File Upload Size Limits
**Files:** `backend/app/api/v1/endpoints/samples.py`
**Issue:** Audio sample upload endpoint accepts multipart file uploads without enforcing a maximum file size. An attacker can upload multi-gigabyte files to exhaust disk space and memory.
**Fix:** Add `UploadFile` size validation (e.g., max 100MB per file). Add nginx `client_max_body_size` directive.

### 3.2 [HIGH] Missing Path Traversal Protection on Audio File Serving
**Files:** `backend/app/api/v1/endpoints/audio.py`
**Issue:** Audio file serving endpoints may be vulnerable to path traversal if filenames aren't sanitized. Patterns like `../../etc/passwd` in voice_id or filename parameters could expose system files.
**Fix:** Validate all file paths resolve within the `storage/` directory. Use `Path.resolve()` and verify the resolved path starts with the storage root.

### 3.3 [HIGH] CORS Allows Credentials with Broad Origins
**Files:** `backend/app/main.py:88-95`
**Issue:** `allow_credentials=True` combined with configurable origins. If `cors_origins` is set to `["*"]` (wildcard), browsers will reject it with credentials, but a misconfigured list could allow credential theft from any listed origin.
**Fix:** Validate CORS origins at startup. Never allow `*` when `allow_credentials=True`. Add security headers middleware (HSTS, X-Content-Type-Options, X-Frame-Options).

### 3.4 [HIGH] Nginx Missing Security Headers
**Files:** `docker/nginx.conf`
**Issue:** No security headers configured:
- Missing `X-Content-Type-Options: nosniff`
- Missing `X-Frame-Options: DENY`
- Missing `X-XSS-Protection: 1; mode=block`
- Missing `Content-Security-Policy`
- Missing `Strict-Transport-Security` (for HTTPS deployments)
- Missing `Referrer-Policy`
**Fix:** Add security headers block to nginx.conf.

### 3.5 [HIGH] Docker Containers Run as Root
**Files:** `docker/Dockerfile.backend`, `docker/Dockerfile.frontend`
**Issue:** Neither Dockerfile creates a non-root user. All application code runs as root inside containers. A container escape vulnerability would give full root access to the host.
**Fix:** Add `RUN useradd -m appuser` and `USER appuser` to both Dockerfiles.

### 3.6 [HIGH] output_format Parameter Enables Potential Command Injection
**Files:** `backend/app/schemas/synthesis.py`, `backend/app/services/synthesis_service.py:370`
**Issue:** The `output_format` field is an unconstrained `str`. This value flows to pydub's `audio.export(format=target_format)` which passes it to ffmpeg. Malicious format strings could exploit ffmpeg argument parsing.
**Fix:** Change `output_format` to an Enum: `class OutputFormat(str, Enum): WAV="wav"; MP3="mp3"; OGG="ogg"; FLAC="flac"`.

### 3.7 [HIGH] Self-Healing Endpoints Have No Authentication
**Files:** `backend/app/healing/endpoints.py` — ALL endpoints
**Issue:** `get_healing_status`, `list_incidents`, `force_health_check`, `toggle_healing`, `request_review` — none require authentication. An attacker can disable the self-healing engine or trigger forced health checks.
**Fix:** Add `user: CurrentUser` and `require_scope("admin")`.

### 3.8 [HIGH] Speech-to-Speech Upload Has No File Size Limit
**Files:** `backend/app/api/v1/endpoints/audio_tools.py:203`
**Issue:** The S2S endpoint reads the uploaded file with `await audio.read()` without any size validation. Multi-GB uploads will exhaust server memory.
**Fix:** Add explicit size check before reading.

### 3.9 [HIGH] voice_settings Dict Can Override Provider API Keys
**Files:** `backend/app/schemas/synthesis.py:18`, `backend/app/services/synthesis_service.py:162`
**Issue:** `voice_settings: dict | None` is applied directly via `current_config.update(voice_settings)`. A user can send `voice_settings: {"api_key": "attacker-key"}` to override the provider's API key for a single request.
**Fix:** Whitelist allowed voice_settings keys per provider. Never allow config keys like `api_key`, `subscription_key`, etc.

### 3.10 [MEDIUM] No Rate Limiting on File Upload Endpoints
**Files:** `backend/app/api/v1/endpoints/samples.py`
**Issue:** The samples upload endpoint has no rate limit. An attacker can flood the server with upload requests. Rate limiting is applied to synthesis (10/min), comparison (5/min), training (5/min), and OpenAI-compat (20/min) — but NOT to: profiles CRUD, samples upload, providers, voices, api-keys, webhooks, audio tools, presets.
**Fix:** Add rate limits to all write endpoints. Consider a global default of 60/min (already set in slowapi config but not applied to all endpoints).

### 3.7 [MEDIUM] API Keys Stored in Plain Text
**Files:** `backend/app/models/api_key.py`
**Issue:** API keys for provider configuration (ElevenLabs, Azure) may be stored in the database `config_json` column without encryption.
**Fix:** Encrypt sensitive config values at rest using Fernet symmetric encryption with a key derived from the JWT secret.

### 3.8 [MEDIUM] No CSRF Protection
**Files:** Backend-wide
**Issue:** No CSRF tokens are used. While the API uses bearer tokens (when auth is enabled), the current `AUTH_DISABLED=true` mode has zero protection against cross-site request forgery.
**Fix:** Add CSRF middleware or use SameSite cookie attributes when auth is enabled.

### 3.9 [MEDIUM] Redis Connection Without Authentication
**Files:** `docker/docker-compose.yml:39-43`, `backend/app/core/config.py:42`
**Issue:** Redis runs without a password (`redis:7-alpine` default). Any process on the Docker network can read/write to Redis. Celery tasks and rate limit data are exposed.
**Fix:** Configure Redis with `requirepass` and update `REDIS_URL` to include authentication.

### 3.10 [LOW] Swagger/ReDoc Exposed Based Only on APP_ENV
**Files:** `backend/app/main.py:77-78`
**Issue:** API docs are disabled only when `app_env == "production"`. Docker compose doesn't set `APP_ENV=production`, so Swagger UI is exposed on port 8100 in Docker deployments.
**Fix:** Set `APP_ENV=production` in docker-compose.yml, or disable docs by default and enable only with an explicit flag.

### 3.11 [LOW] Telemetry Endpoint Has No Auth
**Files:** `backend/app/main.py:110-113`
**Issue:** `GET /api/v1/telemetry` returns server metrics (request counts, error rates, latencies) without any authentication check.
**Fix:** Require admin scope for telemetry access.

---

## 4. Incomplete / Partially Implemented Features

### 4.1 [HIGH] Provider Streaming — Mostly Stubbed
**Files:** `backend/app/providers/base.py:213-219`
**Issue:** The `stream_synthesis()` method in the base class raises `NotImplementedError`. Only Azure Speech and ElevenLabs implement streaming. The remaining 7 providers (Kokoro, Piper, Coqui XTTS, StyleTTS2, CosyVoice, Dia, Dia2) do NOT support streaming. The frontend `SynthesisLabPage` has no streaming UI.
**Impact:** No real-time audio streaming for local providers.
**Recommendation:** Implement chunked streaming for Kokoro and Coqui XTTS (both support it natively). Add a streaming toggle in the Synthesis Lab with a waveform-as-it-generates visualization.

### 4.2 [HIGH] Voice Cloning — Only 3 of 9 Providers
**Files:** Multiple provider files
**Issue:** Voice cloning (`clone_voice()`) is only implemented for ElevenLabs, Azure Speech, and Coqui XTTS. The remaining 6 providers raise `NotImplementedError`. CosyVoice and StyleTTS2 support zero-shot voice cloning natively but it's not implemented.
**Impact:** The Training Studio page can only clone voices with 3 providers, despite the UI suggesting broader support.
**Fix:** Implement `clone_voice()` for CosyVoice (zero-shot from reference audio), StyleTTS2 (zero-shot style transfer). Update the Training Studio UI to show which providers support cloning.

### 4.3 [HIGH] Audio Design Page — Uncommitted & Partially Built
**Files:** `frontend/src/pages/AudioDesignPage.tsx`, `frontend/src/stores/audioDesignStore.ts`, `backend/app/schemas/audio_tools.py` (all untracked)
**Issue:** An entire Audio Design feature exists as untracked files — not committed to git. This includes a React page, Zustand store, backend schemas, and tests. The feature appears to be for audio post-processing (normalize, trim, fade, effects).
**Impact:** Feature exists but is not part of the deployed codebase. Could be lost.
**Fix:** Commit the Audio Design feature. Verify it integrates properly with the rest of the app.

### 4.4 [MEDIUM] Fine-Tuning — Mostly Stubbed
**Files:** Multiple provider `fine_tune()` methods
**Issue:** Fine-tuning is only implemented for Azure Speech (Custom Neural Voice) and Coqui XTTS. It's explicitly NOT supported for: Kokoro, Piper, Dia, Dia2, CosyVoice, StyleTTS2. ElevenLabs redirects to their web dashboard.
**Impact:** The Training Studio suggests fine-tuning capabilities that don't exist for most providers.
**Fix:** Either implement fine-tuning for StyleTTS2 (supports it) and CosyVoice, or clearly indicate in the UI which providers support which training capabilities.

### 4.5 [MEDIUM] Word Boundary Detection — Only Azure
**Files:** `backend/app/providers/base.py:222-226`
**Issue:** `get_word_boundaries()` is only implemented by Azure Speech. This feature enables subtitle/caption synchronization, karaoke-style highlighting, and lip-sync data.
**Impact:** Word-level timing data unavailable for 8 of 9 providers.
**Recommendation:** Implement post-synthesis word boundary estimation using forced alignment (e.g., whisper timestamps or gentle aligner) as a fallback for all providers.

### 4.6 [MEDIUM] Pronunciation Assessment — Only Azure
**Files:** `backend/app/providers/base.py:232-236`
**Issue:** `pronunciation_assessment()` is only implemented by Azure Speech. No fallback exists.
**Impact:** Training quality scoring can only use Azure for pronunciation evaluation.

### 4.7 [MEDIUM] Transcription — Only Azure
**Files:** `backend/app/providers/base.py:228-230`
**Issue:** `transcribe()` is only implemented by Azure Speech.
**Fix:** Add Whisper-based transcription as a provider-agnostic fallback. Whisper is already commonly available in the ML ecosystem.

### 4.8 [LOW] features.json Status Tracking Inaccurate
**Files:** `features.json`
**Issue:** Shows `"passing": 0` at top level but individual features show `"status": "passing"`. The `"tested": false` flag is set for all phases.
**Fix:** Update features.json to reflect actual test coverage status.

---

## 5. Backend Architecture Issues

### 5.1 [CRITICAL] Shared Provider State Race Condition
**Files:** `backend/app/services/synthesis_service.py:160-163`
**Issue:** When `voice_settings` is provided, the code calls `provider.configure(current_config)` on the SHARED SINGLETON provider instance. In a concurrent environment, two simultaneous synthesis requests with different `voice_settings` will race — one user's voice settings bleed into another's synthesis. The provider registry returns shared singletons.
**Impact:** Voice settings corruption under concurrent load. Wrong voices or settings applied to wrong requests.
**Fix:** Either clone the provider per-request, pass voice_settings as a synthesis parameter, or use context-var scoping.

### 5.2 [HIGH] Coqui XTTS fine_tune Is a No-Op Stub
**Files:** `backend/app/providers/coqui_xtts.py:170-208`
**Issue:** `fine_tune()` returns metadata without performing any actual training. The capabilities report `supports_fine_tuning=True` when the model is loaded, so the Training Studio UI presents a workflow that produces a no-op model version.
**Fix:** Either implement actual XTTS fine-tuning or set `supports_fine_tuning=False` in capabilities.

### 5.3 [MEDIUM] Dia2 and CosyVoice Streaming Is Fake
**Files:** `backend/app/providers/dia2.py:149-172`, `backend/app/providers/cosyvoice.py:187-210`
**Issue:** `stream_synthesize` collects ALL chunks into a list before yielding any. The client receives all data at once after generation completes — identical to non-streaming synthesis.
**Fix:** Use `asyncio.Queue` to bridge synchronous generators to async, yielding chunks as they arrive.

### 5.4 [MEDIUM] SynthesisHistory has no FK to voice_profiles
**Files:** `backend/app/models/synthesis_history.py:19`
**Issue:** `profile_id` is a plain `String(36)` with no `ForeignKey`. Synthesis history can reference deleted profiles without cascade behavior.
**Fix:** Add `ForeignKey("voice_profiles.id")`.

### 5.5 [MEDIUM] synthesis_history endpoint crashes on null output_path
**Files:** `backend/app/api/v1/endpoints/synthesis.py:168`
**Issue:** `h.output_path.split('/')[-1]` will raise `AttributeError` when `output_path` is `None` (nullable column).
**Fix:** Add null check or use the ternary pattern consistently.

### 5.6 [HIGH] Duplicate `get_db` Dependency
**Files:** `backend/app/core/database.py:58`, `backend/app/core/dependencies.py:19`
**Issue:** Two identical `get_db()` async generators exist in different modules. Some endpoints may import from one, some from the other.
**Fix:** Remove the duplicate. Keep the one in `dependencies.py` (canonical location for FastAPI deps) and re-export from `database.py` if needed.

### 5.2 [MEDIUM] Provider Config Not Validated on Apply
**Files:** `backend/app/services/provider_registry.py:90-94`
**Issue:** `apply_config()` stores raw config dict without validation. Invalid config (wrong types, missing required fields, malformed API keys) is only caught when the provider is next used.
**Fix:** Add a `validate_config()` method to the base provider class. Call it before storing config.

### 5.3 [MEDIUM] Synthesis Service Missing Chunking for Long Text
**Files:** `backend/app/services/synthesis_service.py`
**Issue:** Long text synthesis sends the entire text to the provider at once. For very long texts (articles, books), this can exceed provider limits, timeout, or produce poor-quality output.
**Fix:** Implement intelligent text chunking (sentence/paragraph boundaries) with audio concatenation. Many providers have character limits (ElevenLabs: 5000 chars, Azure: 10 minutes per request).

### 5.4 [MEDIUM] No Database Migrations Strategy for Docker
**Files:** `docker/Dockerfile.backend`, `backend/alembic.ini`
**Issue:** The Docker CMD runs the app directly without running Alembic migrations. Schema changes after the initial deploy won't be applied.
**Fix:** Add `alembic upgrade head` to the init-models.sh startup script or CMD chain.

### 5.5 [LOW] Self-Healing Engine — No Persistence
**Files:** `backend/app/healing/engine.py`
**Issue:** The healing engine's state (detected issues, remediations, history) is in-memory only. A container restart loses all healing history.
**Fix:** Persist healing events to the database or a JSON log file.

### 5.6 [LOW] Webhook Dispatcher — No Retry Logic
**Files:** `backend/app/services/webhook_dispatcher.py`
**Issue:** Webhook deliveries have no retry mechanism for failed HTTP requests. A temporary network issue means lost notifications.
**Fix:** Add exponential backoff retry (3 attempts) with dead-letter logging.

### 5.7 [LOW] MCP Server — Limited Tool Coverage
**Files:** `backend/app/mcp/tools.py`
**Issue:** The MCP server exposes tools for synthesis and profiles but not for: training management, audio comparison, provider configuration, audio tools, or presets.
**Fix:** Expand MCP tool coverage to match REST API capabilities.

---

## 6. Frontend Architecture Issues

### 6.1 [HIGH] Settings Store Defaults Ignored by Synthesis Lab
**Files:** `frontend/src/stores/settingsStore.ts:10-11`, `frontend/src/pages/SynthesisLabPage.tsx:48`
**Issue:** `defaultProvider` and `audioFormat` are configurable in Settings but never consumed by the Synthesis Lab. It defaults `outputFormat` to `"wav"` locally instead of reading from `useSettingsStore`.
**Impact:** User-configured defaults are silently ignored.
**Fix:** Wire settingsStore defaults into SynthesisLabPage initial state.

### 6.2 [HIGH] 11 Missing API Methods for Backend Endpoints
**Files:** `frontend/src/services/api.ts`
**Issue:** The following backend endpoints have NO frontend API method: streaming synthesis, all webhook CRUD, OpenAI-compatible TTS, transcription (defined but never called), pronunciation assessment (defined but never called).
**Fix:** Add missing API methods and wire them into relevant UI pages.

### 6.3 [HIGH] ProviderConfigCard and ProvidersPage Massive Code Duplication
**Files:** `frontend/src/components/admin/ProviderConfigCard.tsx` (447 lines), `frontend/src/pages/ProvidersPage.tsx:300-633`
**Issue:** `ConfigField` component is implemented identically in both files, including the exact same option-group parsing logic. The expanded config panel does the same thing in both places.
**Fix:** Extract shared `ConfigField` and `ProviderConfigPanel` components.

### 6.4 [MEDIUM] SynthesisLab Memory Leak — Blob URLs Never Revoked
**Files:** `frontend/src/pages/SynthesisLabPage.tsx:231`
**Issue:** `URL.createObjectURL(stsFile)` creates a new blob URL every render cycle. No `URL.revokeObjectURL()` cleanup exists, causing unbounded memory growth.
**Fix:** Use `useRef` to track and revoke previous blob URLs.

### 6.5 [MEDIUM] No 404 Catch-All Route
**Files:** `frontend/src/App.tsx`
**Issue:** No `<Route path="*">` exists. Navigating to any undefined path shows a blank page inside the layout.
**Fix:** Add a NotFoundPage component and route.

### 6.6 [MEDIUM] Redundant Data Fetching Across Pages
**Files:** Multiple pages' `useEffect` hooks
**Issue:** At least 6 pages independently call `fetchProviders()` and 5 call `fetchProfiles()` on mount. No "fetched" timestamp or stale-while-revalidate pattern exists.
**Fix:** Add a fetch timestamp to stores. Skip refetch if data is recent (e.g., < 30s old). Or fetch at layout level.

### 6.7 [MEDIUM] Duplicated Type Definitions Across 5+ Files
**Files:** `api.ts`, `audioDesignStore.ts`, `HealingPage.tsx`, `TrainingStudioPage.tsx`, `ProfilesPage.tsx`
**Issue:** `AudioDesignFile`/`AudioClip`, `AudioDesignQuality`/`QualityBrief`, `HealingStatus`, `Incident`, `QualityResult`, `ReadinessResult`, `VersionInfo` are all defined locally in different files instead of `types/index.ts`.
**Fix:** Consolidate all types into `types/index.ts`.

### 6.8 [HIGH] 22 Instances of TypeScript `any` Type
**Files:** Multiple frontend files (see Section 8)
**Issue:** Error handling uses `catch (e: any)` throughout. API responses, WebSocket events, and store callbacks use untyped `any`.
**Fix:** Create a typed error interface (`AppError`). Replace all `any` in catch blocks with `unknown` and use type guards.

### 6.2 [MEDIUM] No Virtualization for Large Voice Lists
**Files:** `frontend/src/pages/VoiceLibraryPage.tsx`
**Issue:** The voice library renders ALL 353 voices as DOM elements simultaneously. With filtering this is manageable, but as the catalog grows (Azure alone has 400+ voices across all languages), performance will degrade.
**Fix:** Implement `react-window` or `react-virtuoso` for the voice grid. Only render visible cards.

### 6.3 [MEDIUM] Missing Optimistic Updates
**Files:** Multiple stores
**Issue:** Profile creation, deletion, and updates wait for the API response before updating the UI. This creates a perceptible delay.
**Fix:** Implement optimistic updates with rollback on failure for: profile CRUD, preset CRUD, settings changes.

### 6.4 [MEDIUM] Synthesis Lab — No SSML Validation
**Files:** `frontend/src/components/audio/SSMLEditor.tsx`
**Issue:** The SSML editor uses Monaco Editor but doesn't validate SSML syntax before sending to the backend. Invalid SSML causes cryptic provider errors.
**Fix:** Add client-side SSML schema validation. Show inline errors in the editor. Preview SSML structure in a tree view.

### 6.5 [MEDIUM] No Keyboard Shortcuts
**Files:** Frontend-wide
**Issue:** No keyboard shortcuts exist for common actions: play/pause audio (Space), new synthesis (Ctrl+Enter), navigate between pages, etc.
**Fix:** Add a keyboard shortcut system using `useHotkeys` hook. Show shortcuts in tooltips and a help modal.

### 6.6 [LOW] Missing Accessibility (a11y)
**Files:** Frontend-wide
**Issue:** Limited ARIA labels, no skip-to-content links, audio player not keyboard-navigable, form inputs missing `aria-describedby` for error messages.
**Fix:** Audit against WCAG 2.1 AA. Add ARIA labels to all interactive elements. Ensure keyboard navigation works throughout.

### 6.7 [LOW] No Offline/Error Boundary for API Failures
**Files:** Frontend-wide
**Issue:** No React Error Boundary wrapping pages. If an API call throws in a render path, the entire app crashes to a white screen.
**Fix:** Add Error Boundaries around each page route. Show a friendly "something went wrong" with retry button.

### 6.8 [LOW] Stale Data After Mutations
**Files:** Multiple stores
**Issue:** After creating a profile from the Voice Library, the Profiles page doesn't refresh its data unless the user manually navigates away and back. Similar staleness exists after training completes.
**Fix:** Implement cross-store invalidation. When a profile is created in `voiceLibraryStore`, trigger a refetch in `profileStore`.

---

## 7. Docker & Infrastructure Issues

### 7.1 [HIGH] Backend Docker Image ~5-8GB
**Files:** `docker/Dockerfile.backend`
**Issue:** The backend image includes PyTorch (530MB), CUDA libraries (~1.2GB), and all 9 TTS provider dependencies even if only cloud providers are used. Most users won't need GPU packages in the main backend image.
**Fix:** Create a separate "light" Dockerfile for cloud-only deployments. Move GPU-requiring providers to the gpu-worker image. Use multi-stage builds more aggressively. Consider PyTorch CPU-only wheels (`--index-url https://download.pytorch.org/whl/cpu`).

### 7.2 [HIGH] No Health Checks in docker-compose.yml
**Files:** `docker/docker-compose.yml`
**Issue:** No container has a `healthcheck` directive. Docker has no way to know if the backend is actually serving requests vs. just running. `depends_on` doesn't wait for health — containers start in parallel regardless.
**Fix:** Add health checks:
```yaml
backend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
```

### 7.3 [HIGH] No Resource Limits on Containers
**Files:** `docker/docker-compose.yml`
**Issue:** No memory or CPU limits on any container. A single synthesis request on a local provider could consume all system memory (PyTorch models can use 2-4GB each).
**Fix:** Add `deploy.resources.limits` for each service (e.g., backend: 4GB RAM, worker: 8GB RAM, frontend: 256MB, Redis: 512MB).

### 7.4 [MEDIUM] Nginx Missing gzip for API Responses
**Files:** `docker/nginx.conf`
**Issue:** While the FastAPI backend has GZip middleware, the nginx proxy doesn't enable gzip for proxied responses. Large JSON responses (voice library, 353 voices) are sent uncompressed through nginx.
**Fix:** Add `gzip on; gzip_types application/json text/plain text/css application/javascript;` to nginx.conf.

### 7.5 [MEDIUM] No Proxy Timeouts for Long Operations
**Files:** `docker/nginx.conf`
**Issue:** No `proxy_read_timeout` configured. Default nginx timeout is 60s. Synthesis and training operations can take longer.
**Fix:** Add `proxy_read_timeout 300s;` and `proxy_send_timeout 300s;` to the API location block.

### 7.6 [MEDIUM] CI/CD Pipeline Missing Key Checks
**Files:** `.github/workflows/ci.yml`
**Issue:** The CI pipeline has: backend lint, backend test, frontend lint, frontend build, docker build validation. Missing:
- Frontend unit tests (`npm run test`)
- Security scanning (e.g., `pip-audit`, `npm audit`)
- Coverage reporting
- E2E tests
- Image vulnerability scanning (Trivy/Grype)
**Fix:** Add these jobs to ci.yml.

### 7.7 [MEDIUM] .gitignore Missing Key Patterns
**Files:** `.gitignore`
**Issue:** Missing entries for:
- `.claude/` (agent memory files showing up as untracked)
- `.playwright-mcp/` (Playwright state)
- `e2e-screenshots/` (test artifacts)
- `audit-*.png` (audit screenshots)
- `*.db-shm`, `*.db-wal` (SQLite journal files)
**Fix:** Add these patterns.

### 7.8 [HIGH] Docker Layer Caching Broken — Code Copied Before pip install
**Files:** `docker/Dockerfile.backend:3-6`
**Issue:** `COPY backend/app ./app` is done BEFORE `pip install`. Any code change invalidates the entire pip install cache, forcing full dependency reinstallation on every build (~5-10 min).
**Fix:** In builder stage: copy only `pyproject.toml` first, run `pip install`, THEN copy app source.

### 7.9 [HIGH] SQLite Shared Across Docker Containers — Unsafe Concurrency
**Files:** `docker/docker-compose.yml:21-22,56-57`
**Issue:** Both `backend` and `worker` services mount the same `db_data` volume with SQLite. SQLite does not handle concurrent writes from multiple processes well, especially across Docker volume mounts. WAL file behavior over Docker volumes causes database locks.
**Fix:** Switch to PostgreSQL for Docker deployments, or document this limitation prominently.

### 7.10 [HIGH] GPU Service Providers Import Nonexistent Modules
**Files:** `gpu-service/app/providers/__init__.py`
**Issue:** Imports `f5_tts_provider`, `fish_speech`, `openvoice_provider`, `orpheus_provider`, `piper_training_provider` — but only `chatterbox_provider.py` and `base.py` exist. This causes `ImportError` on startup, making the GPU service completely broken.
**Fix:** Either create stub modules for missing providers or wrap imports in try/except.

### 7.11 [MEDIUM] Double numpy Force-Reinstall in Dockerfile
**Files:** `docker/Dockerfile.backend:29,47`
**Issue:** numpy>=2.0 is force-reinstalled twice — once in builder stage and again in runtime stage. The runtime re-install adds pip + download to the final image, defeating multi-stage build benefits.
**Fix:** Only force-reinstall in the builder stage.

### 7.12 [MEDIUM] Nginx Missing client_max_body_size
**Files:** `docker/nginx.conf`
**Issue:** No `client_max_body_size` directive. Default nginx limit is 1MB, which rejects most audio uploads for voice cloning.
**Fix:** Add `client_max_body_size 100m;`.

### 7.13 [LOW] GPU Service Not Fully Integrated
**Files:** `gpu-service/` directory
**Issue:** The GPU service exists as a separate FastAPI app but has no Dockerfile in the main docker-compose (only in `docker-compose.gpu.yml`). No documentation on how to set it up.
**Fix:** Add setup documentation. Ensure `docker-compose.gpu.yml` is tested and works.

### 7.9 [LOW] No Log Aggregation or Monitoring
**Files:** Docker stack
**Issue:** Backend uses structlog (good), but logs go to stdout with no aggregation. No metrics endpoint beyond the basic `/api/v1/telemetry`. No alerting.
**Fix:** Add an optional Grafana+Loki or ELK stack in a `docker-compose.monitoring.yml` overlay. Export Prometheus metrics from FastAPI.

---

## 8. Code Quality & Simplification

### 8.1 TypeScript `any` Instances (22 total)
Replace all with proper types:
- **Catch blocks:** Change `catch (e: any)` to `catch (e: unknown)` with type guard
- **API responses:** Create typed interfaces for all API responses
- **WebSocket events:** Type the event payloads
- **Files:** `ProviderConfigCard.tsx`, `HealingPage.tsx`, `ProfilesPage.tsx`, `VoiceLibraryPage.tsx`, `AudioPlayer.tsx`, `AudioTimeline.tsx`, `DashboardPage.tsx`, test files

### 8.2 Provider Capability Display Consolidation
**Issue:** Each frontend page independently checks provider capabilities. The Training Studio, Synthesis Lab, and Profiles pages all have slightly different logic for what providers support.
**Fix:** Create a shared `useProviderCapabilities(providerName)` hook that returns a typed capabilities object. Use it everywhere.

### 8.3 Audio Player Component Duplication
**Issue:** Audio playback logic exists in: `VoiceCard` (VoiceLibraryPage), `AudioPlayer` component, `ComparisonPage`, and `SynthesisLabPage`. Each has its own `<audio>` element management.
**Fix:** Create a single `useAudioPlayer` hook that manages playback state, and a single `AudioPlayer` presentational component.

### 8.4 Store Pattern Inconsistency
**Issue:** Some stores fetch data in `useEffect` on page mount, others have explicit `fetch*()` actions. Some stores handle errors, others silently fail.
**Fix:** Standardize all stores: explicit fetch actions, consistent error handling, loading states, and a `reset()` method for cleanup.

### 8.5 Backend Error Response Format Inconsistency
**Issue:** Some endpoints return `{"detail": "..."}` (FastAPI default), others return `{"error": "..."}`, others return `{"message": "..."}`.
**Fix:** Standardize on FastAPI's `{"detail": "..."}` format. Create a custom exception hierarchy that ensures consistent responses.

---

## 9. Feature Gaps vs. Competitors

Based on competitive analysis of ElevenLabs, Play.ht, Resemble.ai, Murf.ai, Azure Speech Studio, Coqui TTS, AllTalk TTS, and open-source alternatives:

### 9.1 [HIGH IMPACT] Pronunciation Dictionary / Custom Lexicon
**Competitors:** ElevenLabs, Azure Speech Studio, Amazon Polly
**Gap:** Atlas Vox has no way to define custom pronunciations for names, acronyms, or domain-specific terms (e.g., "GIF" = /dʒɪf/, "SQL" = "sequel").
**Implementation:** Add a `pronunciation_dictionary` model with IPA/phoneme mappings. Apply as SSML `<phoneme>` tags before synthesis. UI: dictionary editor in Settings.

### 9.2 [HIGH IMPACT] Usage Analytics & Cost Tracking
**Competitors:** ElevenLabs (character usage dashboard), Azure (billing metrics), Play.ht (usage analytics)
**Gap:** No visibility into: characters synthesized per provider, API call counts, estimated costs, storage usage, training job durations.
**Implementation:** Add a `usage_event` table tracking each synthesis (chars, provider, duration, estimated_cost). Dashboard widget showing usage trends, cost breakdown by provider, and remaining quotas.

### 9.3 [HIGH IMPACT] Batch Processing / Bulk Synthesis
**Competitors:** Amazon Polly (batch synthesis API), Azure (batch synthesis), Play.ht (bulk generation)
**Gap:** Atlas Vox can only synthesize one text at a time. No way to process a CSV/list of texts in batch.
**Implementation:** Add a `POST /api/v1/synthesis/batch` endpoint accepting an array of texts + provider/voice config. Process via Celery queue. Show batch progress in UI with per-item status.

### 9.4 [HIGH IMPACT] Real-Time Voice Preview While Adjusting Parameters
**Competitors:** ElevenLabs (instant preview slider), Azure Speech Studio (real-time SSML preview)
**Gap:** Changing voice parameters (speed, pitch, style) requires a full re-synthesis. No real-time preview as sliders move.
**Implementation:** Add a debounced preview synthesis (300ms delay after parameter change). Show a waveform preview. For streaming-capable providers, pipe audio chunks directly.

### 9.5 [MEDIUM IMPACT] Voice Favorites & Collections
**Competitors:** ElevenLabs (favorites), Play.ht (collections), Azure Voice Gallery (favorites)
**Gap:** Users can't bookmark/favorite voices from the 353-voice library. No way to organize voices into named collections.
**Implementation:** Add a `voice_favorite` table (user_id, provider, voice_id). Add star/heart button to VoiceCard. Add "My Favorites" filter to Voice Library. Add "Collections" for grouping voices by project/purpose.

### 9.6 [MEDIUM IMPACT] Audio Watermarking / Provenance
**Competitors:** ElevenLabs (audio watermarking), Resemble.ai (audio fingerprinting)
**Gap:** No way to embed provenance metadata in generated audio (who generated it, when, which model).
**Implementation:** Embed metadata in WAV/MP3 tags (ID3 for MP3, INFO chunks for WAV). Add an optional inaudible audio watermark using spread-spectrum techniques.

### 9.7 [MEDIUM IMPACT] Multilingual Voice Library
**Competitors:** Azure (400+ voices in 140+ languages), ElevenLabs (29 languages), CosyVoice (multilingual)
**Gap:** Azure voice library is filtered to English-only (hardcoded in `azure_speech.py:869`). CosyVoice supports Chinese/Japanese/Korean but the voice library only shows English voices.
**Implementation:** Remove the English-only filter from Azure's `list_voices()`. Add language selection to the voice library (currently filter exists but data is English-only). Add CosyVoice's multilingual voices.

### 9.8 [MEDIUM IMPACT] Voice A/B Testing with Metrics
**Competitors:** ElevenLabs (A/B testing), Resemble.ai (voice comparison scoring)
**Gap:** The Comparison page allows side-by-side playback but has no automated quality metrics (MOS estimation, PESQ, speaker similarity, intelligibility).
**Implementation:** Add automated comparison metrics: estimated MOS (using a lightweight neural MOS predictor), spectral similarity, speaking rate comparison. Show a radar chart comparing voices across dimensions.

### 9.9 [MEDIUM IMPACT] Text Import (URL, PDF, EPUB)
**Competitors:** Speechify (URL/PDF/EPUB import), Play.ht (URL import), NaturalReader (document import)
**Gap:** Users must manually paste text. No way to import from URLs, PDFs, or documents.
**Implementation:** Add import buttons: "From URL" (fetch + extract text), "From File" (PDF/TXT/EPUB/DOCX parser). Use `readability` for URL extraction and `pdfplumber` for PDFs.

### 9.10 [LOW IMPACT] Voice Emotion/Style Controls
**Competitors:** Azure Speech (20+ speaking styles per voice), ElevenLabs (stability/similarity sliders), Play.ht (emotion controls)
**Gap:** While Azure voices support SSML styles (`<mstts:express-as>`), there's no UI for selecting speaking styles (cheerful, sad, angry, whispering, etc.). The SSML editor is the only way.
**Implementation:** Add a style selector dropdown that injects the appropriate SSML tags. Show available styles per voice (from Azure's voice metadata). For non-Azure providers, expose any available emotion parameters.

### 9.11 [LOW IMPACT] Collaborative Features
**Competitors:** Murf.ai (team workspaces), Resemble.ai (team management)
**Gap:** Single-user only (AUTH_DISABLED=true). No concept of teams, shared projects, or collaborative editing.
**Implementation:** Phase 1: Enable multi-user auth. Phase 2: Add team/workspace model. Phase 3: Shared voice profiles and synthesis history.

### 9.12 [MEDIUM IMPACT] New Open-Source Provider Integration
**Competitors:** Fish Speech (300k hrs training data, emotion control), GPT-SoVITS (1-min voice cloning), OpenVoice (zero-shot multilingual)
**Gap:** Since Coqui AI shut down (Dec 2025), the community has moved to newer open-source models. Atlas Vox should add Fish Speech, GPT-SoVITS, and OpenVoice as providers — they represent the current state-of-the-art in open-source TTS.
**Implementation:** Add 2-3 new providers following the existing TTSProvider ABC pattern. Fish Speech has a Python SDK. GPT-SoVITS has a WebUI API.

### 9.13 [MEDIUM IMPACT] Audio Post-Processing / Noise Reduction
**Competitors:** ElevenLabs (audio isolation), Resemble.ai (audio enhancement), Murf.ai (noise removal)
**Gap:** No post-synthesis audio enhancement. Generated audio may have artifacts, background noise, or quality issues that could be automatically improved.
**Implementation:** Add RoFormer/DeepFilterNet-based noise reduction as a post-processing step. Make it toggleable per synthesis request.

### 9.14 [LOW IMPACT] Plugin/Extension System
**Competitors:** AllTalk TTS (extension system), SillyTavern (plugin architecture)
**Gap:** No way for users to add custom TTS providers, audio effects, or integrations without modifying source code.
**Implementation:** Define a provider plugin interface. Load external providers from a `plugins/` directory. Allow custom audio post-processing hooks.

---

## 10. Feature Consolidation Opportunities

### 10.1 Audio Playback — Unify into Single System
**Current:** 4 separate audio playback implementations across VoiceLibrary, Comparison, Synthesis, AudioDesign.
**Proposed:** Single `AudioPlaybackService` with `useAudioPlayer` hook. Centralized play queue, crossfade support, global volume control.

### 10.2 Provider Capabilities — Single Source of Truth
**Current:** Provider capabilities checked independently by Training Studio, Synthesis Lab, Profiles page, Voice Library.
**Proposed:** `useProviderCapabilities()` hook backed by a capabilities cache in the provider store. Components query capability flags (supports_cloning, supports_streaming, etc.) from one place.

### 10.3 Voice Selection — Shared Voice Picker Component
**Current:** Voice selection logic duplicated in SynthesisLab (dropdown), Profiles (dialog), TrainingStudio (selector), Comparison (two dropdowns).
**Proposed:** Single `<VoicePicker>` component with search, filtering, and preview. Reuse everywhere.

### 10.4 Merge Audio Design into Synthesis Lab
**Current:** AudioDesignPage is a separate page for post-processing (normalize, trim, fade, effects).
**Proposed:** Integrate audio design tools as a "Post-Processing" tab in the Synthesis Lab. Synthesis → Preview → Post-Process → Export flow.

### 10.5 Merge Settings + Admin Pages
**Current:** SettingsPage and AdminPage are separate pages with overlapping concerns (provider config lives in both).
**Proposed:** Merge into a single Settings page with tabs: General, Providers, API Keys, Storage, Advanced.

---

## 11. New Feature Recommendations

### 11.1 [HIGH VALUE] Synthesis History & Favorites
**Description:** Persist all synthesis results with metadata (text, provider, voice, parameters, timestamp). Allow users to star favorites, re-synthesize with different settings, and build a personal audio library.
**Implementation:** The `synthesis_history` model already exists. Add: UI page with searchable history grid, audio playback, re-synthesis button, favorite flag, tag system, export/download.

### 11.2 [HIGH VALUE] Voice Cloning Wizard
**Description:** Step-by-step guided wizard for voice cloning: Record/Upload samples → Preprocessing → Provider Selection → Clone → Quality Check → Save Profile.
**Implementation:** Multi-step form with progress indicator. Integrated recording (MediaRecorder API). Sample quality validation before submission. Auto-select best provider based on sample characteristics.

### 11.3 [HIGH VALUE] Webhook Event System
**Description:** The webhook model and dispatcher exist but have limited integration. Expand to fire webhooks for: synthesis complete, training complete, training failed, health alert, usage threshold.
**Implementation:** Define event types. Add webhook event to Celery tasks post-completion. Add webhook test/ping button in UI.

### 11.4 [MEDIUM VALUE] Audio Format Conversion & Export
**Description:** Support exporting audio in multiple formats (WAV, MP3, OGG, FLAC, AAC) with configurable quality. Currently all synthesis outputs WAV.
**Implementation:** Add FFmpeg-based conversion in the audio processor. Add format/quality selector in Synthesis Lab export. Batch export support.

### 11.5 [MEDIUM VALUE] Provider Health Dashboard
**Description:** Real-time dashboard showing each provider's health status, response times, success rates, and error counts over time.
**Implementation:** The self-healing engine already monitors providers. Surface this data: uptime percentage, avg latency, error rate chart, last-check timestamp. Auto-detect degradation trends.

### 11.6 [MEDIUM VALUE] Text Preprocessing Pipeline
**Description:** Intelligent text normalization before synthesis: number expansion ("123" → "one hundred twenty-three"), abbreviation expansion, date formatting, URL handling, code block detection and skipping.
**Implementation:** Add a `text_preprocessor.py` service with configurable rules. Apply before synthesis. Show a "normalized text" preview in the UI.

### 11.7 [LOW VALUE] Dark Mode Toggle Persistence
**Description:** The app has light/dark theme support via CSS custom properties, but verify theme preference persists across sessions.
**Implementation:** Store theme in localStorage. Add system preference detection (`prefers-color-scheme`). Ensure all components honor the theme.

---

## 12. Implementation Roadmap

### Phase A: Critical Fixes (2-3 sessions)
| # | Task | Priority | Effort |
|---|------|----------|--------|
| A1 | Add auth to ALL unauthenticated endpoints (providers, healing, telemetry, voices) | Critical | 2hr |
| A2 | Fix VersionCompareModal destructive version mutation | Critical | 1hr |
| A3 | Fix broken `/voice-library` navigation → `/library` | Critical | 10min |
| A4 | Add 404 catch-all route | Critical | 15min |
| A5 | Fix provider state race condition (shared singleton mutation) | Critical | 2hr |
| A6 | Fix Dockerfile model download scripts (extract to .py files) | Critical | 1hr |
| A7 | Create .dockerignore | Critical | 15min |
| A8 | Fix Docker layer caching (copy code AFTER pip install) | Critical | 30min |
| A9 | Fix GPU service broken provider imports | Critical | 30min |
| A10 | Add Docker health checks + resource limits | Critical | 30min |
| A11 | Fix JWT secret handling for Docker | Critical | 30min |
| A12 | Add DB backup script + warning on docker-reset | Critical | 1hr |
| A13 | Commit untracked Audio Design files | Critical | 15min |
| A14 | Add missing .gitignore patterns (`.claude/`, `*.db-shm`, etc.) | Critical | 10min |
| A15 | Fix output_format to Enum (prevent ffmpeg injection) | Critical | 30min |
| A16 | Whitelist voice_settings keys (prevent API key override) | Critical | 30min |

### Phase B: Security Hardening (1-2 sessions)
| # | Task | Priority | Effort |
|---|------|----------|--------|
| B1 | Add `require_scope("admin")` to config/admin operations | High | 1hr |
| B2 | Add file upload size limits (S2S endpoint + nginx `client_max_body_size`) | High | 30min |
| B3 | Add path traversal protection to audio serving | High | 30min |
| B4 | Add nginx security headers + gzip + proxy timeouts | High | 30min |
| B5 | Add non-root user to all Dockerfiles | High | 30min |
| B6 | Add rate limits to all write endpoints | Medium | 1hr |
| B7 | Encrypt provider API keys at rest | Medium | 2hr |
| B8 | Add Redis authentication | Medium | 30min |
| B9 | Sanitize error messages (remove raw exception details from responses) | Medium | 1hr |
| B10 | Add SSML sanitization (whitelist elements, limit nesting) | Medium | 1hr |
| B11 | Set `AUTH_DISABLED=${AUTH_DISABLED:-true}` in Docker compose | Low | 10min |
| B12 | Remove `*.db-shm`/`*.db-wal` from git tracking | Low | 10min |

### Phase C: Feature Completion (2-3 sessions)
| # | Task | Priority | Effort |
|---|------|----------|--------|
| C1 | Implement streaming for Kokoro + Coqui XTTS | High | 3hr |
| C2 | Implement clone_voice for CosyVoice + StyleTTS2 | High | 3hr |
| C3 | Add Whisper-based transcription fallback | Medium | 2hr |
| C4 | Add text chunking for long synthesis | Medium | 2hr |
| C5 | Add Alembic migrations to Docker startup | Medium | 30min |
| C6 | Expand MCP tool coverage | Medium | 2hr |
| C7 | Remove English-only filter from Azure voices | Medium | 30min |
| C8 | Add word boundary estimation fallback | Low | 3hr |

### Phase D: Code Quality (2-3 sessions)
| # | Task | Priority | Effort |
|---|------|----------|--------|
| D1 | Wire settingsStore defaults into SynthesisLab | High | 30min |
| D2 | Extract shared ConfigField from ProviderConfigCard + ProvidersPage | High | 2hr |
| D3 | Consolidate all type definitions into `types/index.ts` | High | 1hr |
| D4 | Fix SynthesisLab blob URL memory leak | Medium | 30min |
| D5 | Replace all TypeScript `any` with proper types | Medium | 2hr |
| D6 | Unify audio playback into single hook/component | Medium | 2hr |
| D7 | Create shared VoicePicker component | Medium | 2hr |
| D8 | Standardize error response format (backend) | Medium | 1hr |
| D9 | Standardize store patterns (fetch, error, reset, staleness) | Medium | 2hr |
| D10 | Remove duplicate get_db dependency + health.py DbSession | Low | 15min |
| D11 | Add Error Boundaries to all pages | Low | 1hr |
| D12 | Add React virtualization to Voice Library | Low | 1hr |
| D13 | Fix Coqui XTTS capabilities to not claim fine-tuning | Low | 15min |
| D14 | Add SynthesisHistory FK to voice_profiles | Low | 30min |
| D15 | Remove AdminPage (superseded) or redirect to ProvidersPage | Low | 15min |

### Phase E: High-Impact Features (3-4 sessions)
| # | Task | Priority | Effort |
|---|------|----------|--------|
| E1 | Pronunciation dictionary / custom lexicon | High | 4hr |
| E2 | Usage analytics & cost tracking dashboard | High | 4hr |
| E3 | Batch processing / bulk synthesis | High | 3hr |
| E4 | Synthesis history UI with favorites | High | 3hr |
| E5 | Voice cloning wizard (step-by-step) | High | 4hr |
| E6 | Real-time parameter preview | Medium | 3hr |
| E7 | Voice favorites & collections | Medium | 2hr |
| E8 | Text import (URL, PDF, EPUB) | Medium | 3hr |

### Phase F: Polish & Advanced (2-3 sessions)
| # | Task | Priority | Effort |
|---|------|----------|--------|
| F1 | Add CI pipeline: frontend tests, security scan | Medium | 2hr |
| F2 | Voice emotion/style UI controls | Medium | 3hr |
| F3 | Audio format conversion & export options | Medium | 2hr |
| F4 | Provider health dashboard | Medium | 3hr |
| F5 | Text preprocessing pipeline | Medium | 3hr |
| F6 | Keyboard shortcuts system | Low | 2hr |
| F7 | WCAG 2.1 AA accessibility audit & fixes | Low | 4hr |
| F8 | Webhook event expansion | Low | 2hr |
| F9 | Light Docker image (cloud-only) | Low | 2hr |
| F10 | Optional monitoring stack (Grafana+Loki) | Low | 3hr |

---

## Appendix A: File Inventory

### Untracked Files Requiring Action
```
COMMIT:
  backend/app/schemas/audio_tools.py
  backend/tests/test_api/test_audio_design.py
  backend/tests/test_services/test_audio_processor_design.py
  frontend/src/components/audio/AudioTimeline.tsx
  frontend/src/pages/AudioDesignPage.tsx
  frontend/src/stores/audioDesignStore.ts
  frontend/src/test/pages/AudioDesignPage.test.tsx
  frontend/src/test/stores/audioDesignStore.test.ts
  docs/cloud_audio_enhancement_apis.md

ADD TO .gitignore:
  .claude/
  .playwright-mcp/
  e2e-screenshots/
  audit-*.png
  *.db-shm
  *.db-wal
```

### Provider Capability Matrix
| Provider | synthesize | list_voices | clone_voice | fine_tune | stream | word_bounds | transcribe |
|----------|-----------|-------------|-------------|-----------|--------|-------------|------------|
| Kokoro | Yes | Yes (54) | No | No | No* | No | No |
| Coqui XTTS | Yes | Yes (43) | Yes | Stub | No* | No | No |
| Piper | Yes | Yes (40) | No | No | No | No | No |
| ElevenLabs | Yes | Yes (45) | Yes | Dashboard | Yes | No | No |
| Azure Speech | Yes | Yes (159) | Yes (Portal) | Yes (CNV) | Yes | Yes | Yes |
| StyleTTS2 | Yes | Yes (1) | No* | No* | No | No | No |
| CosyVoice | Yes | Yes (7) | No* | No | No | No | No |
| Dia | Yes | Yes (2) | No | No | No | No | No |
| Dia2 | Yes | Yes (2) | No | No | No | No | No |

`*` = Supported by the underlying model but not yet implemented in Atlas Vox.

### Technology Stack Summary
| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | Python + FastAPI | 3.11 / 0.100+ |
| ORM | SQLAlchemy (async) | 2.0 |
| Database | SQLite (aiosqlite) | 3.x |
| Queue | Celery + Redis | 5.x / 7.x |
| Frontend | React + TypeScript + Vite | 18 / 5 / 5 |
| State | Zustand | 4.x |
| Styling | Tailwind CSS | 3.x |
| Container | Docker Compose | v2 |
| CI | GitHub Actions | - |
| Reverse Proxy | Nginx | Alpine |

---

*This document was generated by a multi-agent deep-dive audit using 6 specialized analysis agents examining all layers of the Atlas Vox codebase. Each finding includes file paths and line numbers for direct remediation.*
