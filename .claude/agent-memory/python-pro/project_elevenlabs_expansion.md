---
name: ElevenLabs Provider Expansion
description: Full ElevenLabs API feature set added to atlas-vox — audio isolation, STS, voice design, SFX, word boundary timestamps, voice settings
type: project
---

Expanded `backend/app/providers/elevenlabs.py` to support all major ElevenLabs API features.

**Why:** Provider needed to expose advanced ElevenLabs capabilities to the frontend and API layer.

**How to apply:** When adding new ElevenLabs SDK features, follow the `_get_client()` + `run_sync(_inner_fn)` pattern. All SDK calls block the thread, so they must be wrapped in `run_sync`.

## What was added

### Provider methods (elevenlabs.py)
- `_build_voice_settings()` — constructs `VoiceSettings` from runtime config (stability, similarity_boost, style, use_speaker_boost)
- `_get_model_id()` — reads model_id from config, supporting flash/turbo/multilingual
- `synthesize()` — updated to pass VoiceSettings on every call
- `stream_synthesize()` — updated to pass VoiceSettings
- `synthesize_with_word_boundaries()` — new; wraps `convert_with_timestamps`, returns `(AudioResult, list[WordBoundary])`
- `speech_to_speech()` — new; converts voice using `eleven_english_sts_v2`
- `isolate_audio()` — new; background noise removal via audio_isolation API
- `design_voice()` — new; generates previews from text description via text_to_voice API
- `generate_sound_effect()` — new; produces SFX MP3 via text_to_sound_effects API
- `clone_voice()` — updated to pass `remove_background_noise=True`
- `get_capabilities()` — updated to set `supports_word_boundaries=True`
- `_parse_word_boundaries()` — module-level helper; converts character-level ElevenLabs alignment into word-level `WordBoundary` objects

### Schema (schemas/provider.py)
- `ElevenLabsConfig` — added stability, similarity_boost, style, use_speaker_boost fields
- `PROVIDER_FIELD_DEFINITIONS["elevenlabs"]` — added UI fields for all new voice settings; model_id changed to select with flash/turbo/multilingual options

### API endpoint (api/v1/endpoints/audio_tools.py)
New router at `/api/v1/audio-tools` with:
- `POST /isolate` — noise removal for a stored sample (by profile_id + sample_id)
- `POST /speech-to-speech` — file upload conversion to target voice
- `POST /design-voice` — voice preview generation from description
- `POST /sound-effect` — SFX generation from text

### Router (api/v1/router.py)
Registered `audio_tools.router` after samples.

### Tests (tests/test_providers/test_elevenlabs.py)
53 tests covering all new methods, schema validation, field definitions, and the `_parse_word_boundaries` helper. All pass.
