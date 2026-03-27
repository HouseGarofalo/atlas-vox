# Atlas Vox — Open Tasks

## Priority 1: GPU Providers (High Impact)

- [ ] **T1: Fish Speech — download model + test synthesis**
  - Download fishaudio/fish-speech-1.5 weights (~4GB)
  - Test synthesis via GPU service
  - Test voice cloning with Jarvis samples
  - Verify RemoteProvider routes correctly

- [ ] **T2: Chatterbox — install + test**
  - Install in GPU service venv
  - Download model weights
  - Test synthesis + voice cloning

- [ ] **T3: F5-TTS — install + test**
  - Install in GPU service venv
  - Download model weights
  - Test zero-shot cloning

- [ ] **T4: OpenVoice v2 — install + test**
  - Install in GPU service venv (git clone required)
  - Test tone cloning

- [ ] **T5: Orpheus TTS — install + test**
  - Install in GPU service venv
  - Download Llama-3B weights (~8GB)
  - Test emotion tags

- [ ] **T6: Piper Training — install + test**
  - Install piper-train in GPU service venv
  - Test fine-tuning with sample data
  - Verify ONNX output works with Piper provider

## Priority 2: Docker Hardening (Medium Impact)

- [ ] **T7: Bake numpy fix into Dockerfile**
  - Ensure numpy 2.x is final install step
  - Test Kokoro healthy after fresh build without manual fix

- [ ] **T8: Bake XTTS + StyleTTS2 models into storage volume**
  - Add model download to Dockerfile or startup script
  - Models should persist in storage_data volume

- [ ] **T9: Clean up stale test profiles**
  - Remove "Train Test *" profiles stuck in training status
  - Or add bulk cleanup endpoint

## Priority 3: Code Quality (Medium Impact)

- [ ] **T10: Add ESLint config for frontend**
  - Create eslint.config.js with flat config
  - Fix any lint issues
  - CI lint step should pass

- [ ] **T11: Add backend tests for new features**
  - Voice library endpoint tests
  - RemoteProvider tests (mock HTTP)
  - Training flow tests
  - Provider config persistence tests

- [ ] **T12: Update documentation**
  - GPU service setup guide
  - Updated provider list (15 providers)
  - Training flow changes
  - Voice library workflow
  - In-app help/docs pages

## Priority 4: Polish (Low Impact)

- [ ] **T13: Download remaining Piper ONNX models**
  - Add download-on-demand UI or batch download script

- [ ] **T14: Download remaining Kokoro voice .pt files**
  - Non-English voices (Japanese, Chinese, etc.)

Last Updated: 2026-03-27
