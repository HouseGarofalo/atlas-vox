# User Guide

Overview of every section in the Atlas Vox interface.

---

## Dashboard

The Dashboard is your operational overview. It shows four stats cards (total profiles, active training jobs, recent syntheses, active providers), a provider health grid with live status badges, a list of active training jobs with progress bars, and a scrollable recent synthesis history. The health grid auto-refreshes and links to each provider's detail page.

## Voice Profiles

Voice Profiles are identities bound to a specific provider. Each profile has a lifecycle: pending (created, no training), training (job in progress), ready (usable for synthesis), error (training failed), and archived (soft-deleted). You can create profiles manually or from a Voice Library entry. Profiles store metadata like language, description, and the provider-specific voice ID. The Training tab on each profile shows version history.

## Voice Library

The Voice Library aggregates all available voices across all healthy providers (400+ voices). Filter by provider, language, or gender. Preview a voice with one click. Click 'Use Voice' to jump to the Synthesis Lab pre-configured, or 'Create Profile' to create a persistent profile from that voice.

## Training Studio

The Training Studio manages the full voice-cloning pipeline: upload audio samples (WAV, MP3, FLAC, OGG, M4A) or record directly in the browser, run preprocessing (noise reduction, normalization, silence trimming), configure training parameters (epochs, learning rate, batch size), then launch training. Progress updates arrive via WebSocket in real-time with epoch-level granularity. Completed models appear as new versions on the parent profile.

## Synthesis Lab

The primary synthesis interface. Enter plain text or switch to the Monaco-based SSML editor (Azure only). Select a profile and adjust speed (0.5-2.0x), pitch (-20 to +20), and volume (0.0-2.0). Choose an output format (WAV, MP3, OGG). Use persona presets for quick parameter tuning. Results play inline with a wavesurfer.js waveform and can be downloaded.

## Comparison

Select 2-5 voice profiles, enter the same text, and generate synthesis results side-by-side. Each result shows the waveform, latency, and audio format. Useful for A/B testing providers, evaluating training quality, or selecting the best voice for a project.

## Providers

Lists all 9 TTS providers with capabilities, health status, and configuration. Expand a provider to see its settings form (API keys for cloud, GPU toggle for local), run a health check, or trigger a test synthesis. Provider cards show supported features: streaming, SSML, voice cloning, multi-language, and emotion control.

## API Keys

Create scoped API keys for programmatic access. Available scopes: read (list/get resources), write (create/update/delete), synthesize (run synthesis), train (start training), admin (full access). Keys use the format `avx_*` and are hashed with Argon2id on the server. When `AUTH_DISABLED=true` (default for local dev), API keys are not enforced.

## Settings

Toggle between light and dark themes, set your default TTS provider and audio output format. Preferences are persisted in browser localStorage and apply immediately.

## Design System

Customize the look and feel of Atlas Vox in real time with 15 design tokens: accent hue, accent saturation, font family (system, Inter, monospace, serif), font size, density, sidebar width, content max width, border radius, card style (bordered, raised, flat, glassmorphism), and animation toggles. Choose from 8 theme presets (Blue, Emerald, Violet, Sunset, Rose, Mono, Minimal, Spacious Serif) or create your own combination. All changes persist across sessions.

## Self-Healing System

The self-healing subsystem continuously monitors provider health and system resources. It uses configurable detection rules (consecutive failures, latency thresholds, error rate windows) to identify problems, then runs automated remediation actions (restart provider, clear cache, switch to fallback). The incident log shows all detected issues and their resolution. An MCP bridge exposes self-healing status to external agents.

## Docs Page

An in-app documentation browser with provider-specific guides (setup, capabilities, pricing), architecture diagrams, and configuration reference. Content is rendered from markdown and stays in sync with the repository docs/ folder.

## Help Center

Seven tabs covering getting started, feature guides, step-by-step walkthroughs, CLI reference, troubleshooting FAQ, API reference, and project information.

## Admin (Legacy)

The legacy admin page provides a raw view of system state: database stats, Redis connection, Celery workers, and task queue depth. It is superseded by the Dashboard and Self-Healing pages but remains available for debugging.

---

## Persona Presets Reference

Six built-in persona presets for the Synthesis Lab:

| Preset | Speed | Pitch | Volume | Character |
|--------|-------|-------|--------|-----------|
| Friendly | 1.0x | +2 | 1.0 | Warm and approachable |
| Professional | 0.95x | 0 | 1.0 | Clear and authoritative |
| Energetic | 1.15x | +5 | 1.1 | Upbeat and enthusiastic |
| Calm | 0.85x | -3 | 0.9 | Soothing and relaxed |
| Authoritative | 0.9x | -5 | 1.15 | Commanding and confident |
| Soothing | 0.8x | -2 | 0.85 | Gentle and comforting |

Presets apply immediately when selected and can be fine-tuned with the sliders.

---

## Voice Profile Lifecycle

```
pending -> training -> ready -> archived
                    \-> error
```

Profiles start as pending, transition to training when a job is submitted, become ready on success, or error on failure. Archived profiles are soft-deleted and can be restored.
