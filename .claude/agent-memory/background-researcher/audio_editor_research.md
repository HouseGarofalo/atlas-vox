---
name: Audio Design Studio Library Research
description: Research on React/TS libraries for building an audio editor with waveform timeline, effects chain, and multi-format export
type: project
---

## Research Report: Audio Design Studio Libraries

**Date**: 2026-04-04
**Confidence**: High

### Recommended Architecture (3-Layer Stack)

**Layer 1 -- Waveform & Timeline: wavesurfer.js v7** (already in project)
Atlas Vox already depends on wavesurfer.js ^7.12.5. The v7 line provides: Regions plugin (drag/resize segments for trim/split/join), Timeline plugin (ruler with time markers), Zoom plugin, Spectrogram plugin, and an official `@wavesurfer/react` wrapper with hook-based API. This covers visualization and segment selection. No new dependency needed.

**Layer 2 -- Effects & Processing: Tone.js + Web Audio API**
Tone.js (written in TypeScript, last updated March 2026) provides a high-level effects chain: EQ3, Compressor, Reverb, Chorus, Noise Gate, and ~20 more. Connect nodes in series for a non-destructive effects pipeline. For operations Tone.js does not cover (silence detection, normalization), use the Web Audio API AnalyserNode and GainNode directly. Tone.js wraps Web Audio API, so the two interoperate cleanly.

**Layer 3 -- Multi-Format Export: ffmpeg.wasm**
The Web Audio API only renders to raw PCM. For MP3/OGG/FLAC encoding, use ffmpeg.wasm (WebAssembly build of FFmpeg). It supports WAV, MP3 (LAME), OGG (Vorbis), FLAC, Opus, and AAC. Runs entirely client-side. Alternative: lamejs for MP3-only export (lighter weight, 20x realtime).

### Alternative Considered: waveform-playlist v5

naomiaro/waveform-playlist is a full multi-track Audacity-style editor (1.6k stars, Tone.js integration, WAV export, React hooks). It would replace wavesurfer.js entirely. Rejected because: Atlas Vox already uses wavesurfer.js elsewhere (AudioPlayer component), the multi-track paradigm is heavier than needed for a single-voice design studio, and adopting it means replacing an existing dependency.

### Implementation Approach

1. Use `@wavesurfer/react` with Regions + Timeline + Zoom plugins for the editor canvas.
2. Build an effects rack component that maps UI controls to a Tone.js signal chain (EQ3 -> Compressor -> Reverb -> destination).
3. For trim/split/join, read region boundaries from wavesurfer, slice the underlying AudioBuffer, and concatenate with OfflineAudioContext.
4. For export, render the processed AudioBuffer via OfflineAudioContext, then pipe the result through ffmpeg.wasm for the target format.
5. Add format selector (WAV/MP3/OGG/FLAC) with quality/bitrate options per format.

### Key Dependencies

| Library | Purpose | Size | TS Support |
|---------|---------|------|------------|
| wavesurfer.js ^7 | Waveform, regions, timeline | ~40KB gzip | Yes |
| @wavesurfer/react | React hooks wrapper | ~3KB | Yes |
| Tone.js | Effects chain | ~150KB gzip | Native TS |
| @ffmpeg/ffmpeg | Multi-format export | ~25MB WASM | Yes |
| @ffmpeg/util | Helper utilities | ~5KB | Yes |

### Gotchas

- ffmpeg.wasm requires SharedArrayBuffer (COOP/COEP headers) for multi-threaded mode; single-threaded mode works without but is slower.
- Tone.js requires a user gesture to start AudioContext (call `Tone.start()` on first click).
- wavesurfer.js Regions plugin emits `region-updated` events on drag -- debounce these to avoid excessive re-renders.
- OfflineAudioContext rendering for long files can block; run in a Web Worker or show progress.
