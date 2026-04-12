# Provider Guides

Atlas Vox supports 9 TTS providers spanning cloud APIs, local CPU models, and local GPU models. Each provider has different strengths, requirements, and trade-offs.

## Provider Overview

| Provider | Type | Voice Count | Description |
|----------|------|-------------|-------------|
| [Kokoro](kokoro.md) | Local (CPU) | 54 built-in voices | Lightweight, fast TTS with 54 built-in voices. CPU-only, no GPU required. Default provider in Atlas Vox. |
| [Piper](piper.md) | Local (CPU) | 100+ downloadable voice models across 30+ languages | Fast, local TTS optimized for Raspberry Pi and Home Assistant. ONNX-based with many pre-trained voices across 30+ languages. |
| [ElevenLabs](elevenlabs.md) | Cloud API | Thousands of voices, plus custom voice cloning | Industry-leading cloud TTS with the most natural-sounding voices. Supports instant voice cloning and 29 languages. |
| [Azure Speech](azure_speech.md) | Cloud API | 400+ neural voices across 140+ languages | Microsoft Azure Cognitive Services TTS with 400+ neural voices, full SSML support, and enterprise reliability. |
| [Coqui XTTS v2](coqui_xtts.md) | Local (GPU) | Unlimited via voice cloning (any reference audio) | State-of-the-art voice cloning from just 6 seconds of audio. Supports 17 languages with zero-shot synthesis. |
| [StyleTTS2](styletts2.md) | Local (GPU) | Style transfer from reference audio (unlimited) | Style diffusion and adversarial training for human-level speech quality. Zero-shot voice transfer with the highest MOS scores. |
| [CosyVoice](cosyvoice.md) | Local (GPU) | Built-in voices + voice cloning | Alibaba's multilingual TTS with natural prosody. Supports 9 languages with ~150ms streaming latency on GPU. |
| [Dia](dia.md) | Local (GPU) | 2 built-in dialogue speakers ([S1] and [S2]) | Nari Labs dialogue TTS with 1.6B parameters. Generates natural multi-speaker conversations with non-verbal sounds. |
| [Dia2](dia2.md) | Local (GPU) | 2 built-in dialogue speakers ([S1] and [S2]) | Next-gen dialogue model with 2B parameters and streaming support. Real-time conversation generation with improved quality. |
