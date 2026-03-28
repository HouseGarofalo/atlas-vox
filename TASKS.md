# Atlas Vox — Task Tracker

## Completed

- [x] **T1: Fish Speech** — Provider rewritten for OpenAudio S1 API. Needs gated HF model access (`fishaudio/openaudio-s1-mini`)
- [x] **T2: Chatterbox** — Installed, tested e2e through Atlas Vox (488KB WAV, voice cloning)
- [x] **T3: F5-TTS** — Installed, tested e2e through Atlas Vox (682KB WAV, 7.10s, zero-shot)
- [x] **T4: OpenVoice v2** — Installed, tested e2e (synthesis + tone cloning)
- [x] **T5: Orpheus TTS** — WebSocket client SDK installed (local vLLM is Linux-only)
- [x] **T6: Piper Training** — Linux-only, documented
- [x] **T7: Dockerfile numpy fix** — Runtime-stage reinstall + init-models.sh
- [x] **T8: Kokoro startup script** — init-models.sh copies from storage volume
- [x] **T9: Stale profile cleanup** — 8 test profiles deleted
- [x] **T10: ESLint config** — 0 errors, 15 warnings
- [x] **T11: Backend tests** — 20 new tests, all passing
- [x] **T12: Documentation update** — All docs updated for 15 providers
- [x] **T13: Fix stale test assertions** — Updated from ==9 to >=9 for provider/tool counts
- [x] **T14: GPU service auto-start** — install.bat + install-service.bat for Windows Task Scheduler
- [x] **T15: OpenAI-compatible API** — POST /v1/audio/speech, tested with OpenAI Python SDK
- [x] **T16: MCP quick-speak tool** — atlas_vox_speak + atlas_vox_list_available_voices
- [x] **T17: RemoteProvider bug fixes** — JSON body, clone field name, model map

## Known Limitations

- Fish Speech needs `huggingface-cli login` + access to `fishaudio/openaudio-s1-mini`
- Orpheus local inference requires Linux (vLLM), client SDK needs API key
- Piper Training (`piper-train`) only available on Linux
- Chatterbox requires voice clone before synthesis (no default voice)

## Provider Status (15 total)

| Provider | Synthesis | Cloning | Platform |
|----------|-----------|---------|----------|
| Kokoro | Working | No | Docker CPU |
| Piper | Working | No | Docker CPU |
| ElevenLabs | Working | Working | Cloud |
| Azure Speech | Working | Portal-only | Cloud |
| Coqui XTTS | Working | Working | Docker CPU/GPU |
| StyleTTS2 | Working | Working | Docker CPU |
| CosyVoice | Healthy | GPU worker only | Docker GPU |
| Dia | Healthy | GPU worker only | Docker GPU |
| Dia2 | Healthy | No | Docker GPU |
| Chatterbox | Working | Working | Host GPU |
| F5-TTS | Working | Working | Host GPU |
| OpenVoice v2 | Working | Working | Host GPU |
| Fish Speech | Needs model | Needs model | Host GPU |
| Orpheus | Client only | Client only | Cloud/Linux |
| Piper Training | Linux only | N/A | Linux GPU |

Last Updated: 2026-03-28
