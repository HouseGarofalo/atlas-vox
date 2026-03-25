# Implementation Plan: Atlas Vox

**PRD Reference:** docs/prp/PRD.md
**Created:** 2026-03-25
**Author:** Claude Code (PRP Framework)
**Status:** Draft
**Estimated Effort:** 10-14 sessions (Phases 2-6)

---

## Overview

Atlas Vox is a self-hosted voice training and customization platform with 9 TTS providers, 4 interfaces (Web UI, CLI, REST API, MCP), and a full training pipeline. Phase 1 (Foundation) is complete — this plan covers Phases 2-6 from scaffolded state to production-ready.

---

## Current State (Post-Phase 1)

### Completed
- Project scaffolding (86 files)
- Backend core: config, logging, database (async SQLAlchemy + aiosqlite), security (JWT + Argon2id)
- 9 SQLAlchemy models + 8 Pydantic schema modules
- TTSProvider ABC + KokoroTTSProvider (first provider)
- ProviderRegistry + ProfileService
- API endpoints: health, profiles CRUD, providers
- FastAPI app with lifespan + CORS
- CLI entry point (atlas-vox via Typer)
- Celery + Alembic configuration stubs
- Frontend shell: Vite + React + Tailwind + Zustand + 8 page stubs + layout

### Not Yet Implemented
- Audio processing pipeline
- Training infrastructure (Celery tasks, WebSocket progress)
- 8 remaining TTS providers
- Synthesis service (chunking, streaming, batch, comparison)
- Full frontend pages (currently stubs)
- CLI commands (currently entry point only)
- MCP server
- Tests, Docker, documentation

---

## Prerequisites

### Before Starting Phase 2
- [x] Phase 1 complete and verified
- [x] Python 3.11+ environment with pyproject.toml
- [x] Node.js 18+ with frontend package.json
- [ ] Redis running locally (for Celery broker)
- [ ] espeak-ng installed (required by Kokoro, StyleTTS2, Piper)

### System Dependencies
| Dependency | Required For | Install |
|------------|-------------|---------|
| Redis 7+ | Celery broker/backend | `docker run -d -p 6379:6379 redis:7-alpine` |
| espeak-ng | Kokoro, StyleTTS2, Piper | `choco install espeak-ng` or OS package manager |
| FFmpeg | Audio format conversion | `choco install ffmpeg` or OS package manager |
| NVIDIA Container Toolkit | GPU Docker providers | Optional, for Docker GPU mode |

---

## Implementation Phases

### Phase 2: Audio Pipeline & Training Infrastructure [Sessions 1-3]

**Objective:** Upload audio, preprocess it, queue training jobs, track progress via WebSocket, version models. Add Coqui XTTS and Piper providers.

#### Tasks

##### 2.1 Audio Processor Service
- **Description:** Implement `services/audio_processor.py` — the shared preprocessing pipeline used by all providers before training.
- **Files:** `backend/app/services/audio_processor.py`
- **Dependencies:** noisereduce, pydub, librosa, numpy
- **Estimated Time:** 2-3 hours
- **Implementation:**
  - `preprocess_audio(input_path, output_path, config)` → noise reduction, normalization, silence trimming, format conversion to WAV 16kHz mono
  - `analyze_audio(path)` → pitch contour (f0 via librosa), energy envelope, duration, sample rate, spectral centroid
  - Config: noise reduction strength, silence threshold, target sample rate, target format
  - All operations async-friendly (run in executor for CPU-bound work)
- **Validation:**
  - [ ] Preprocesses WAV/MP3/FLAC to normalized WAV 16kHz mono
  - [ ] Returns pitch/energy analysis for a sample file
  - [ ] Handles corrupt/empty audio gracefully

##### 2.2 Samples API Endpoints
- **Description:** Multipart upload, list, delete, analysis, and preprocessing trigger for audio samples.
- **Files:** `backend/app/api/v1/endpoints/samples.py`, update `api/v1/router.py`
- **Estimated Time:** 2 hours
- **Implementation:**
  - `POST /api/v1/profiles/{id}/samples` — multipart file upload (multiple files), validate format, store in `storage/samples/`, create AudioSample records
  - `GET /api/v1/profiles/{id}/samples` — list samples with metadata
  - `DELETE /api/v1/profiles/{id}/samples/{sample_id}` — delete sample + file
  - `GET /api/v1/profiles/{id}/samples/{sample_id}/analysis` — return audio analysis (pitch, energy, duration)
  - `POST /api/v1/profiles/{id}/samples/preprocess` — trigger preprocessing Celery task
- **Validation:**
  - [ ] Upload WAV/MP3/FLAC via multipart form
  - [ ] List returns all samples for a profile
  - [ ] Analysis returns pitch/energy data
  - [ ] Delete removes file and DB record

##### 2.3 Celery Task Infrastructure
- **Description:** Configure Celery app properly, implement preprocessing and training task skeletons.
- **Files:** `backend/app/tasks/celery_app.py` (update), `backend/app/tasks/preprocessing.py`, `backend/app/tasks/training.py`
- **Estimated Time:** 2 hours
- **Implementation:**
  - `celery_app.py`: Configure broker (Redis), result backend (Redis), task serializer (JSON), task routes
  - `preprocessing.py`: `preprocess_samples` task — iterate profile samples, run audio_processor, update sample status
  - `training.py`: `train_model` task — dispatch to provider-specific training, report progress, create model version on success
  - Both tasks send progress updates via Celery task metadata (polled by WebSocket)
- **Validation:**
  - [ ] Celery worker starts and connects to Redis
  - [ ] Preprocessing task processes samples and updates DB
  - [ ] Training task dispatches to correct provider

##### 2.4 Training Service
- **Description:** Orchestrate the full training flow: validate samples → preprocess → train → version.
- **Files:** `backend/app/services/training_service.py`
- **Estimated Time:** 2 hours
- **Implementation:**
  - `start_training(profile_id, provider_name, config)` → create TrainingJob, queue Celery task, return job
  - `get_job_status(job_id)` → return current status + progress percentage
  - `cancel_job(job_id)` → revoke Celery task
  - `create_model_version(profile_id, job_id, artifacts)` → create ModelVersion, optionally activate
  - Validate: profile has enough samples, provider supports training, samples are preprocessed
- **Validation:**
  - [ ] Start training creates job and queues task
  - [ ] Status returns progress from Celery
  - [ ] Cancel revokes the task

##### 2.5 Training API Endpoints
- **Description:** REST endpoints for training operations + WebSocket for live progress.
- **Files:** `backend/app/api/v1/endpoints/training.py`, update `api/v1/router.py`
- **Estimated Time:** 2-3 hours
- **Implementation:**
  - `POST /api/v1/profiles/{id}/train` — start training job
  - `GET /api/v1/training/jobs` — list all training jobs (filterable by status, profile)
  - `GET /api/v1/training/jobs/{job_id}` — get job details
  - `POST /api/v1/training/jobs/{job_id}/cancel` — cancel running job
  - `WS /api/v1/training/jobs/{job_id}/progress` — WebSocket streaming progress updates (poll Celery task state, push JSON frames)
- **Validation:**
  - [ ] POST starts a training job, returns job ID
  - [ ] WebSocket sends progress updates
  - [ ] Cancel stops a running job

##### 2.6 Model Versioning Logic
- **Description:** Immutable version creation on training success, version activation, A/B readiness.
- **Files:** Update `services/training_service.py`, add version endpoints to `api/v1/endpoints/profiles.py`
- **Estimated Time:** 1 hour
- **Implementation:**
  - `GET /api/v1/profiles/{id}/versions` — list model versions for a profile
  - `POST /api/v1/profiles/{id}/activate-version/{version_id}` — set active version
  - Each training success creates a new ModelVersion with artifacts path, metrics, and timestamp
  - Profile's `active_version_id` points to the currently deployed model
- **Validation:**
  - [ ] Training success creates a version record
  - [ ] Activate sets the profile's active version
  - [ ] Versions list shows all training outputs

##### 2.7 Coqui XTTS v2 Provider
- **Description:** Voice cloning + fine-tuning provider with configurable GPU/CPU mode.
- **Files:** `backend/app/providers/coqui_xtts.py`
- **Estimated Time:** 3 hours
- **Dependencies:** `TTS` package from coqui-ai/TTS
- **Implementation:**
  - `synthesize()`: `tts.tts_to_file(text, speaker_wav=reference)` → WAV output
  - `clone_voice()`: Use XTTS inference with speaker_wav reference (6s minimum audio)
  - `fine_tune()`: Use TTS training recipes for extended training
  - `get_capabilities()`: cloning=True, fine_tuning=True, streaming=True, gpu_mode="configurable"
  - GPU mode: detect Docker NVIDIA runtime or fall back to CPU
- **Validation:**
  - [ ] Synthesize produces audio with default voice
  - [ ] Clone voice from reference audio works
  - [ ] Health check reports GPU/CPU mode correctly

##### 2.8 Piper TTS Provider
- **Description:** Lightweight ONNX-based provider for Home Assistant compatibility.
- **Files:** `backend/app/providers/piper_tts.py`
- **Estimated Time:** 1.5 hours
- **Dependencies:** `piper-tts`
- **Implementation:**
  - `synthesize()`: `piper.synthesize(text)` → WAV bytes
  - `list_voices()`: Enumerate available Piper ONNX models
  - `get_capabilities()`: cloning=False, fine_tuning=True (via separate training pipeline), streaming=False, gpu_mode="none"
  - Model management: download ONNX models from Piper repository on first use
- **Validation:**
  - [ ] Synthesize produces clean WAV audio
  - [ ] List voices returns available models
  - [ ] Health check passes without GPU

#### Phase 2 Verification
```bash
# Upload samples to a profile
curl -X POST localhost:8000/api/v1/profiles/{id}/samples -F "files=@sample.wav"
# Trigger preprocessing
curl -X POST localhost:8000/api/v1/profiles/{id}/samples/preprocess
# Start training (Coqui XTTS)
curl -X POST localhost:8000/api/v1/profiles/{id}/train -d '{"provider":"coqui_xtts"}'
# Monitor progress via WebSocket
wscat -c ws://localhost:8000/api/v1/training/jobs/{job_id}/progress
# Verify model version created
curl localhost:8000/api/v1/profiles/{id}/versions
```

---

### Phase 3: All Providers & Full Synthesis Pipeline [Sessions 4-6]

**Objective:** Implement remaining 6 providers, synthesis service with chunking/streaming/batch, comparison, presets, API keys.

#### Tasks

##### 3.1 ElevenLabs Provider
- **Files:** `backend/app/providers/elevenlabs.py`
- **Estimated Time:** 2 hours
- **Implementation:**
  - Use official `elevenlabs` Python SDK
  - `synthesize()`: POST `/text-to-speech/{voice_id}`, return audio bytes
  - `clone_voice()`: POST `/voices/ivc/create` with audio samples
  - `stream_synthesize()`: WebSocket streaming endpoint
  - `list_voices()`: GET `/voices` from ElevenLabs API
  - Store `voice_id` in `model_versions.provider_model_id`
  - Capabilities: cloning=True, streaming=True, gpu_mode="none" (cloud)

##### 3.2 Azure AI Speech Provider
- **Files:** `backend/app/providers/azure_speech.py`
- **Estimated Time:** 2 hours
- **Implementation:**
  - Use `azure-cognitiveservices-speech` SDK
  - `synthesize()`: SSML-aware synthesis via `SpeechSynthesizer.SpeakSsmlAsync`
  - `list_voices()`: GET available Neural voices
  - `clone_voice()`: Custom Neural Voice API (requires Azure portal setup)
  - Capabilities: ssml=True, cloning=True (CNV), streaming=True, gpu_mode="none" (cloud)

##### 3.3 StyleTTS2 Provider
- **Files:** `backend/app/providers/styletts2.py`
- **Estimated Time:** 2.5 hours
- **Implementation:**
  - Import from yl4579/StyleTTS2 module
  - `synthesize()`: Zero-shot via diffusion model, multi-speaker with reference audio
  - `fine_tune()`: Training recipes from StyleTTS2 repo
  - Capabilities: zero_shot=True, fine_tuning=True, gpu_mode="configurable"
  - Requires espeak-ng

##### 3.4 CosyVoice Provider
- **Files:** `backend/app/providers/cosyvoice.py`
- **Estimated Time:** 2 hours
- **Implementation:**
  - Import from FunAudioLLM/CosyVoice
  - `synthesize()`: `cosyvoice.inference_sft(text, speaker)` for preset voices
  - `clone_voice()`: `cosyvoice.inference_zero_shot(text, prompt_text, prompt_audio)`
  - `stream_synthesize()`: Generator-based streaming (150ms latency)
  - Capabilities: cloning=True, streaming=True, zero_shot=True, languages=9, gpu_mode="configurable"

##### 3.5 Dia Provider (1.6B)
- **Files:** `backend/app/providers/dia.py`
- **Estimated Time:** 2 hours
- **Implementation:**
  - `pip install git+https://github.com/nari-labs/dia.git`
  - `synthesize()`: Dialogue generation with `[S1]`/`[S2]` tags, non-verbal `(laughs)` support
  - `clone_voice()`: Audio conditioning with 5-10s reference audio
  - Capabilities: cloning=True (audio conditioning), streaming=False, gpu_mode="configurable"
  - Requires CUDA 12.6+, ~4.4GB VRAM

##### 3.6 Dia2 Provider (2B)
- **Files:** `backend/app/providers/dia2.py`
- **Estimated Time:** 2 hours
- **Implementation:**
  - Import from nari-labs/Dia2-2B
  - `synthesize()`: Multi-speaker `[S1]`/`[S2]` dialogue
  - `stream_synthesize()`: Streaming generation (begins after initial words)
  - Capabilities: streaming=True, gpu_mode="configurable"
  - Requires CUDA 12.8+, up to 2min English output

##### 3.7 Synthesis Service
- **Files:** `backend/app/services/synthesis_service.py`
- **Estimated Time:** 3 hours
- **Implementation:**
  - `synthesize(text, profile_id, settings)` → dispatch to provider, apply persona/speed/pitch, return AudioResult
  - Text chunking: Split long text at sentence boundaries, synthesize chunks, concatenate audio
  - Streaming orchestration: For streaming providers, yield audio chunks as they arrive
  - Apply persona presets (map preset → provider-specific params)
  - Save to synthesis_history
  - Audio format conversion (WAV → MP3/OGG on request)

##### 3.8 Synthesis API Endpoints
- **Files:** `backend/app/api/v1/endpoints/synthesis.py`, `backend/app/api/v1/endpoints/audio.py`
- **Estimated Time:** 2 hours
- **Implementation:**
  - `POST /api/v1/synthesize` — single synthesis, return audio URL
  - `POST /api/v1/synthesize/stream` — chunked transfer encoding for streaming providers
  - `POST /api/v1/synthesize/batch` — process script file (one line per utterance)
  - `GET /api/v1/synthesis/history` — list past synthesis results
  - `GET /api/v1/audio/{filename}` — serve generated audio files from storage

##### 3.9 Comparison Service & API
- **Files:** `backend/app/services/comparison_service.py`, `backend/app/api/v1/endpoints/compare.py`
- **Estimated Time:** 2 hours
- **Implementation:**
  - `compare(text, profile_ids, settings)` → parallel synthesis across voices, return results with latency metrics
  - `POST /api/v1/compare` — side-by-side comparison, returns array of audio URLs + timing
  - Use `asyncio.gather` for parallel provider calls

##### 3.10 Presets API
- **Files:** `backend/app/api/v1/endpoints/presets.py`
- **Estimated Time:** 1.5 hours
- **Implementation:**
  - `GET/POST /api/v1/presets` — CRUD for persona presets
  - `PUT/DELETE /api/v1/presets/{id}`
  - Seed system defaults: Friendly, Professional, Energetic, Calm, Authoritative, Soothing
  - Each preset maps to speed/pitch/volume/emphasis parameters

##### 3.11 API Keys Endpoints
- **Files:** `backend/app/api/v1/endpoints/api_keys.py`
- **Estimated Time:** 1.5 hours
- **Implementation:**
  - `POST /api/v1/api-keys` — create key with scope selection (read, write, synthesize, train, admin)
  - `GET /api/v1/api-keys` — list keys (masked, show last 4 chars)
  - `DELETE /api/v1/api-keys/{id}` — revoke key
  - Key hashing with Argon2id (from security.py)

#### Phase 3 Verification
```bash
# Synthesize with each provider
for p in kokoro piper coqui_xtts elevenlabs azure_speech styletts2 cosyvoice dia dia2; do
  curl -X POST localhost:8000/api/v1/synthesize -d "{\"text\":\"Hello\",\"provider\":\"$p\"}"
done
# Compare two voices
curl -X POST localhost:8000/api/v1/compare -d '{"text":"Hello","profile_ids":["id1","id2"]}'
# Batch synthesis
curl -X POST localhost:8000/api/v1/synthesize/batch -F "script=@script.txt" -F "profile_id=..."
# Stream synthesis
curl -N localhost:8000/api/v1/synthesize/stream -d '{"text":"Long text...","provider":"dia2"}'
```

---

### Phase 4: Web UI — Complete React Frontend [Sessions 7-9]

**Objective:** All 8 pages fully functional with audio recording, waveform visualization, real-time progress, SSML editing.

#### Tasks

##### 4.1 API Client & Stores
- **Files:** `frontend/src/services/api.ts` (complete), `frontend/src/stores/*.ts`
- **Estimated Time:** 3 hours
- **Implementation:**
  - `api.ts`: Typed fetch wrapper with auth header injection, error handling, base URL config
  - `profileStore.ts`: profiles CRUD, samples management, version activation
  - `trainingStore.ts`: training jobs, WebSocket progress, job cancellation
  - `providerStore.ts`: provider list, config, health checks
  - `synthesisStore.ts`: synthesis trigger, history, comparison results, batch status
  - `authStore.ts`: API key management, JWT tokens

##### 4.2 Shared UI Components
- **Files:** `frontend/src/components/ui/*.tsx`
- **Estimated Time:** 2 hours
- **Implementation:**
  - Button, Input, TextArea, Select, Toggle, Slider, Badge, Card, Modal, Dropdown, Tabs, Tooltip
  - All with Tailwind + CSS custom properties for theme support
  - Framer Motion transitions with `prefers-reduced-motion` respect

##### 4.3 Audio Components
- **Files:** `frontend/src/components/audio/*.tsx`, `frontend/src/hooks/useAudioRecorder.ts`, `frontend/src/hooks/useAudioPlayer.ts`
- **Estimated Time:** 3 hours
- **Implementation:**
  - `WaveformDisplay.tsx`: wavesurfer.js integration, zoomable, color-coded regions
  - `AudioRecorder.tsx`: MediaRecorder API, live waveform, record/pause/stop, preview before upload
  - `AudioPlayer.tsx`: Play/pause, seek, volume, playback speed, waveform scrubbing
  - `useWebSocket.ts`: Generic WebSocket hook for training progress

##### 4.4 Dashboard Page
- **Files:** `frontend/src/pages/DashboardPage.tsx`
- **Estimated Time:** 2 hours
- **Implementation:**
  - Profile count card, active training jobs list, provider health grid (9 providers with status), recent synthesis history table

##### 4.5 Profiles Page
- **Files:** `frontend/src/pages/ProfilesPage.tsx`, `frontend/src/components/profiles/*.tsx`
- **Estimated Time:** 3 hours
- **Implementation:**
  - Card grid with status badges (pending/training/ready/error/archived)
  - Create/edit modal with form (name, description, language, provider, tags)
  - SampleUploader: drag-drop zone + in-browser audio recorder
  - Training trigger button (navigates to Training Studio with profile preselected)

##### 4.6 Training Studio Page
- **Files:** `frontend/src/pages/TrainingStudioPage.tsx`, `frontend/src/components/training/*.tsx`
- **Estimated Time:** 3 hours
- **Implementation:**
  - Audio recorder with live waveform (wavesurfer.js)
  - Sample list with individual waveform previews
  - Preprocessing toggle (enable/disable noise reduction, normalization)
  - Provider-specific training config form (adapts to `get_capabilities()` response)
  - WebSocket progress bar (connects to `/training/jobs/{id}/progress`)
  - Job history table

##### 4.7 Synthesis Lab Page
- **Files:** `frontend/src/pages/SynthesisLabPage.tsx`, `frontend/src/components/synthesis/*.tsx`
- **Estimated Time:** 3 hours
- **Implementation:**
  - Text area with character count and limit indicator
  - Voice selector (dropdown filtered by ready status)
  - Persona preset selector + speed/pitch/volume sliders
  - SSML toggle → Monaco Editor for SSML editing
  - Preview button → AudioPlayer with result
  - Batch tab: upload script file, process all lines, download zip

##### 4.8 Comparison Page
- **Files:** `frontend/src/pages/ComparisonPage.tsx`
- **Estimated Time:** 2 hours
- **Implementation:**
  - Multi-voice selector (checkboxes or chips)
  - Text input area
  - "Generate All" button → parallel synthesis
  - Side-by-side AudioPlayer cards with latency/timing metrics

##### 4.9 Providers Page
- **Files:** `frontend/src/pages/ProvidersPage.tsx`, `frontend/src/components/providers/*.tsx`
- **Estimated Time:** 2 hours
- **Implementation:**
  - ProviderCard per provider: status indicator (healthy/unhealthy/unconfigured), capability badges
  - ProviderConfig form: API keys (masked input), endpoints, model selection, GPU/CPU toggle for local
  - Health check button with live status update

##### 4.10 API Keys & Settings Pages
- **Files:** `frontend/src/pages/ApiKeysPage.tsx`, `frontend/src/pages/SettingsPage.tsx`
- **Estimated Time:** 2 hours
- **Implementation:**
  - ApiKeysPage: Create form with scope checkboxes, key list (masked), copy-to-clipboard, revoke
  - SettingsPage: Theme toggle (light/dark), default provider, audio format, webhook config

##### 4.11 Theming & Responsive
- **Files:** `frontend/src/styles/globals.css`, `frontend/tailwind.config.ts`
- **Estimated Time:** 1.5 hours
- **Implementation:**
  - CSS custom properties for light/dark themes
  - Tailwind dark mode via class strategy
  - Responsive breakpoints: mobile-first, sidebar collapses to hamburger menu
  - 44px min touch targets for accessibility

#### Phase 4 Verification
- [ ] Navigate all 8 pages without errors
- [ ] Create profile via UI form
- [ ] Upload audio via drag-drop
- [ ] Record audio in browser with waveform
- [ ] Start training and see live WebSocket progress bar
- [ ] Synthesize text and play audio in AudioPlayer
- [ ] Compare two voices side-by-side
- [ ] Configure provider with GPU/CPU toggle
- [ ] Toggle light/dark theme

---

### Phase 5: CLI & MCP Server [Sessions 9-11]

**Objective:** Full CLI tool with Rich output and MCP server for AI agent integration.

#### Tasks

##### 5.1 CLI Framework Setup
- **Files:** `backend/app/cli/main.py` (update)
- **Estimated Time:** 1 hour
- **Implementation:**
  - Typer app with subcommand groups
  - Rich console for formatted output
  - Shared config loading (read .env or config file)
  - HTTP client for API calls (CLI calls the REST API)

##### 5.2 CLI Commands (init, profiles, train, synthesize, providers, serve, compare, presets)
- **Files:** `backend/app/cli/commands/*.py` (8 files)
- **Estimated Time:** 6 hours total
- **Implementation per command:**
  - `init.py`: Create config, initialize DB, check system deps (espeak-ng, Redis, FFmpeg)
  - `profiles.py`: list (Rich table), create (interactive prompts), delete, export/import JSON
  - `train.py`: Upload samples from directory, start training, Rich progress bar polling
  - `synthesize.py`: TTS to file, `--play` flag for immediate playback, format selection
  - `providers.py`: List with health (Rich table), configure (interactive), GPU/CPU toggle
  - `serve.py`: Start uvicorn with optional `--mcp` flag for MCP server
  - `compare.py`: Multi-voice synthesis, Rich comparison table with file paths
  - `presets.py`: List, create, delete presets

##### 5.3 MCP Server
- **Files:** `backend/app/mcp/server.py`, `backend/app/mcp/tools.py`, `backend/app/mcp/transport.py`
- **Estimated Time:** 4 hours
- **Implementation:**
  - `server.py`: JSONRPC 2.0 handler, tool/resource registration, connection lifecycle
  - `tools.py`: 7 tool handlers — `atlas_vox_synthesize`, `atlas_vox_list_voices`, `atlas_vox_train_voice`, `atlas_vox_get_training_status`, `atlas_vox_manage_profile`, `atlas_vox_compare_voices`, `atlas_vox_provider_status`
  - `transport.py`: SSE transport layer with API key auth
  - Resources: `atlas-vox://profiles`, `atlas-vox://providers`

##### 5.4 Webhooks
- **Files:** `backend/app/api/v1/endpoints/webhooks.py`, `backend/app/services/webhook_dispatcher.py`
- **Estimated Time:** 2 hours
- **Implementation:**
  - `GET/POST /api/v1/webhooks` — CRUD for webhook subscriptions
  - `PUT/DELETE /api/v1/webhooks/{id}` — update/remove
  - `POST /api/v1/webhooks/{id}/test` — send test payload
  - `webhook_dispatcher.py`: Fire webhooks on training events (completed, failed), HMAC-signed payloads

#### Phase 5 Verification
```bash
# CLI commands
atlas-vox init
atlas-vox providers list
atlas-vox profiles create --name "Test" --provider kokoro
atlas-vox synthesize "Hello world" --voice "Test" --output test.wav
atlas-vox serve --port 8000 --mcp
# MCP test
# Connect MCP client → call atlas_vox_list_voices → verify response
# Webhook test
curl -X POST localhost:8000/api/v1/webhooks -d '{"url":"https://example.com/hook","events":["training.completed"]}'
```

---

### Phase 6: Testing, Docker, Documentation, Polish [Sessions 11-14]

**Objective:** Comprehensive tests, containerized deployment, full documentation.

#### Tasks

##### 6.1 Unit Tests — Providers
- **Files:** `backend/tests/test_providers/*.py` (9 test files)
- **Estimated Time:** 4 hours
- **Implementation:**
  - Mock HTTP calls with httpx/respx for cloud providers (ElevenLabs, Azure)
  - Mock GPU inference for local providers
  - Test synthesize, list_voices, capabilities, health_check per provider
  - Test error handling (API errors, timeouts, missing models)

##### 6.2 Unit Tests — Services
- **Files:** `backend/tests/test_services/*.py`
- **Estimated Time:** 3 hours
- **Implementation:**
  - `test_audio_processor.py`: Known WAV fixtures, verify normalization/noise reduction
  - `test_training_service.py`: Mock Celery tasks, verify orchestration flow
  - `test_synthesis_service.py`: Text chunking, streaming orchestration
  - `test_comparison_service.py`: Parallel synthesis mocking

##### 6.3 Integration Tests — API Endpoints
- **Files:** `backend/tests/test_api/*.py`
- **Estimated Time:** 4 hours
- **Implementation:**
  - pytest + httpx.AsyncClient + in-memory SQLite
  - Test all endpoint groups: profiles, samples, training, synthesis, compare, presets, api_keys, webhooks, providers, health
  - Test auth flows (API key, JWT, disabled auth)

##### 6.4 MCP & CLI Tests
- **Files:** `backend/tests/test_mcp/*.py`, `backend/tests/test_cli/*.py`
- **Estimated Time:** 2 hours
- **Implementation:**
  - MCP protocol compliance tests (JSONRPC 2.0 format, tool call/response)
  - CLI tests via Typer test runner (CliRunner)

##### 6.5 E2E Tests
- **Files:** `frontend/tests/e2e/*.spec.ts` or `backend/tests/e2e/*.py`
- **Estimated Time:** 3 hours
- **Implementation:**
  - Playwright for 5 critical flows: profile CRUD, training start/progress, synthesis playback, comparison, provider config

##### 6.6 Docker Configuration
- **Files:** `docker/Dockerfile.backend`, `docker/Dockerfile.frontend`, `docker/Dockerfile.gpu-worker`, `docker/docker-compose.yml`, `docker/docker-compose.gpu.yml`
- **Estimated Time:** 3 hours
- **Implementation:**
  - `Dockerfile.backend`: Multi-stage (build deps → slim runtime), Python 3.11-slim, espeak-ng
  - `Dockerfile.frontend`: Multi-stage (node build → nginx serve)
  - `Dockerfile.gpu-worker`: NVIDIA CUDA 12.1 base, PyTorch, Celery worker
  - `docker-compose.yml`: backend, frontend, redis, cpu-worker (4 services)
  - `docker-compose.gpu.yml`: Override adding gpu-worker with NVIDIA runtime

##### 6.7 Documentation
- **Files:** `README.md`, `docs/*.md`, `docs/provider-guides/*.md`
- **Estimated Time:** 4 hours
- **Implementation:**
  - `README.md`: Quickstart, architecture overview, provider comparison table, screenshots
  - `docs/architecture.md`: System design, data flow, key decisions
  - `docs/api-reference.md`: Link to auto-generated OpenAPI + key endpoint examples
  - `docs/mcp-integration.md`: Setup guide for Claude Code / ATLAS
  - `docs/cli-reference.md`: All commands with examples
  - `docs/provider-guides/*.md`: One per provider (9 files) — setup, config, capabilities, troubleshooting

##### 6.8 Makefile & Polish
- **Files:** `Makefile`
- **Estimated Time:** 1 hour
- **Implementation:**
  - Targets: `dev`, `test`, `lint`, `format`, `docker-up`, `docker-gpu-up`, `migrate`, `seed`
  - Ensure `make test` runs full suite
  - Ensure `make lint` runs Ruff (backend) + ESLint (frontend)
  - Ensure `make docker-up` starts full stack

#### Phase 6 Verification
```bash
make test           # All tests pass
make lint           # Ruff + ESLint clean
make docker-up      # Full stack starts from containers
# Playwright E2E
npx playwright test
# README quickstart works on clean machine
```

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| GPU provider setup complexity (CUDA versions, sm_120) | High | High | Docker GPU containers with pinned CUDA; CPU fallback always available |
| Cloud provider API changes (ElevenLabs, Azure) | Medium | Low | Pin SDK versions; mock in tests; graceful degradation |
| Celery/Redis availability for training | High | Medium | Clear setup docs; health checks; fallback to synchronous for simple tasks |
| Large audio files consuming disk/memory | Medium | Medium | Streaming processing; configurable storage limits; cleanup policies |
| WebSocket reliability for training progress | Medium | Medium | Polling fallback via REST endpoint; reconnection logic in frontend |
| espeak-ng availability across platforms | Medium | High | Document install per OS; Docker includes it; graceful error for missing |

---

## Validation Checklist

### Pre-Implementation (Phase 2)
- [ ] Redis running and accessible
- [ ] espeak-ng installed
- [ ] Phase 1 code reviewed and working
- [ ] All Python dependencies installable

### Per-Phase Gates
- [ ] Phase 2: Upload → preprocess → train → version flow works end-to-end
- [ ] Phase 3: All 9 providers synthesize; comparison works; API keys functional
- [ ] Phase 4: All 8 UI pages functional; audio recorder works; WebSocket progress shows
- [ ] Phase 5: CLI commands work; MCP tools callable; webhooks fire
- [ ] Phase 6: Tests pass; Docker runs; docs complete

### Final Acceptance
- [ ] `make test` — all passing, 80%+ coverage
- [ ] `make lint` — clean
- [ ] `make docker-up` — full stack starts
- [ ] E2E smoke test (10-step from PRD section "Verification Strategy") passes
- [ ] README quickstart reproducible on clean machine

---

## Archon Tasks

Tasks to create for tracking:

1. **Phase 2: Audio Pipeline & Training Infrastructure** — audio_processor, samples API, Celery tasks, training service/API, WebSocket progress, model versioning, Coqui XTTS + Piper providers
2. **Phase 3: All Providers & Full Synthesis** — 6 remaining providers, synthesis service (chunking/streaming/batch), comparison, presets, API keys
3. **Phase 4: Web UI** — API client, stores, shared components, audio components, 8 pages, theming
4. **Phase 5: CLI & MCP Server** — 8 CLI commands, MCP server (7 tools + SSE transport), webhooks
5. **Phase 6: Testing, Docker, Docs** — unit/integration/E2E tests, Docker configs, README + provider guides + reference docs, Makefile

---

## Success Criteria (from PRD)

- [ ] All 9 providers synthesize text correctly
- [ ] Voice cloning works for supported providers (ElevenLabs, Coqui XTTS, CosyVoice, Dia, StyleTTS2)
- [ ] Training pipeline: upload → preprocess → train → version → activate flow complete
- [ ] Web UI: all 8 pages functional with audio recording and playback
- [ ] CLI: all commands work (`atlas-vox init` through `atlas-vox serve --mcp`)
- [ ] MCP: AI agents can synthesize and manage voices programmatically
- [ ] Docker: `docker-compose up` starts full stack
- [ ] Tests: 80%+ coverage, all passing
- [ ] Performance: synthesis < 2s for short texts on GPU providers
