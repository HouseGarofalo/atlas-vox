# 📖 Atlas Vox User Guide

> **Atlas Vox** is a self-hosted, intelligent voice training and customization platform that unifies **9 TTS engines** behind a single interface.

---

## Table of Contents

- [Introduction](#-introduction)
- [System Requirements](#-system-requirements)
- [Quick Start](#-quick-start)
- [First-Time Setup](#-first-time-setup)
- [Dashboard](#-dashboard)
- [Voice Library](#-voice-library)
- [Voice Profiles](#-voice-profiles)
- [Providers](#-providers)
  - [Kokoro](#kokoro)
  - [Piper](#piper)
  - [ElevenLabs](#elevenlabs)
  - [Azure Speech](#azure-speech)
  - [Coqui XTTS v2](#coqui-xtts-v2)
  - [StyleTTS2](#styletts2)
  - [CosyVoice](#cosyvoice)
  - [Dia](#dia)
  - [Dia2](#dia2)
- [Training Studio](#-training-studio)
- [Synthesis Lab](#-synthesis-lab)
- [Comparison](#-comparison)
- [API Keys](#-api-keys)
- [Settings](#-settings)
- [Keyboard Shortcuts & Tips](#-keyboard-shortcuts--tips)

---

## 🎯 Introduction

Atlas Vox brings together cloud-based and locally-hosted text-to-speech engines into one unified platform. Whether you are building a podcast, creating an AI assistant, localizing content, or experimenting with voice cloning, Atlas Vox gives you:

- **9 TTS providers** — 2 cloud and 7 local (Docker)
- **290+ voices** browsable in the Voice Library with preview playback
- **4 interfaces**: Web UI, REST API, CLI, and MCP server
- **Voice cloning** from as little as 6 seconds of audio
- **Training pipeline** with audio preprocessing, noise reduction, and normalization
- **Side-by-side comparison** of voices across providers
- **Persona presets** for consistent voice output (Friendly, Professional, Energetic, etc.)
- **GPU flexibility** — run models on CPU or GPU per provider

All data stays on your machine. No audio is sent to third parties unless you explicitly configure a cloud provider.

---

## 💻 System Requirements

### Minimum (CPU-only)

| Component | Requirement |
|-----------|-------------|
| **OS** | Linux, macOS, or Windows (with WSL2 for Docker) |
| **CPU** | 4 cores recommended |
| **RAM** | 8 GB minimum, 16 GB recommended |
| **Disk** | 10 GB free (models download on first use) |
| **Docker** | Docker Engine 24+ with Compose v2 |
| **Node.js** | 20+ (only for local development) |
| **Python** | 3.11+ (only for local development) |

### Recommended (GPU)

| Component | Requirement |
|-----------|-------------|
| **GPU** | NVIDIA GPU with 6 GB+ VRAM (8 GB+ for Dia/Dia2) |
| **Driver** | NVIDIA Driver 525+ |
| **CUDA** | 12.1+ |
| **Docker** | NVIDIA Container Toolkit installed |

> 📋 **Note:** GPU is optional. CPU-only providers (Kokoro, Piper) work perfectly without a GPU. Cloud providers (ElevenLabs, Azure) run remotely and also need no GPU.

### Port Requirements

| Service | Default Port | Configurable Via |
|---------|-------------|-----------------|
| Frontend (Web UI) | `3100` (Docker) / `3000` (dev) | `FRONTEND_PORT` |
| Backend (API) | `8100` (Docker) / `8000` (dev) | `BACKEND_PORT` |
| Redis | `6379` (internal) | Not exposed externally |

---

## 🚀 Quick Start

### Option A: Docker Compose (Recommended)

This is the simplest way to get everything running. Docker handles all dependencies, model downloads, and service orchestration.

```bash
# 1. Clone the repository
git clone https://github.com/HouseGarofalo/atlas-vox.git
cd atlas-vox

# 2. Start all services (backend, frontend, Redis, Celery worker)
make docker-up
```

That is it. Open your browser to **http://localhost:3100** and you are ready to go.

#### With GPU Support

If you have an NVIDIA GPU and want to run local models faster:

```bash
make docker-gpu-up
```

This adds a GPU-enabled Celery worker with CUDA 12.1 support for training and synthesis with Coqui XTTS, StyleTTS2, CosyVoice, Dia, and Dia2.

### Option B: Local Development

```bash
# 1. Clone and install dependencies
git clone https://github.com/HouseGarofalo/atlas-vox.git
cd atlas-vox
make install

# 2. Start Redis (required for training jobs)
# macOS: brew install redis && redis-server
# Linux: sudo apt install redis-server && sudo systemctl start redis
# Windows: use WSL2 or Docker for Redis

# 3. Start development servers
make dev
```

This starts the FastAPI backend on `http://localhost:8100` and the React frontend on `http://localhost:3000`.

### Verify Installation

After starting, verify everything is working:

| Check | URL | Expected |
|-------|-----|----------|
| Web UI | http://localhost:3100 | Dashboard loads |
| API Health | http://localhost:8100/api/v1/health | `{"status":"healthy"}` |
| Swagger Docs | http://localhost:8100/docs | Interactive API docs |

---

## 🎬 First-Time Setup

When you first access Atlas Vox, the system automatically:

1. **Creates the database** — SQLite by default, zero configuration needed
2. **Seeds providers** — All 9 TTS providers are registered in the database
3. **Loads provider configs** — Environment variables and DB settings are merged
4. **Downloads default models** — Piper's English model is downloaded during Docker build

### Recommended First Steps

1. **Check the Dashboard** — See which providers are healthy
2. **Configure cloud providers** (optional) — Go to Providers and add your ElevenLabs API key or Azure Speech credentials
3. **Browse the Voice Library** — Discover available voices across all providers
4. **Create your first Voice Profile** — Pick a voice and create a profile
5. **Try the Synthesis Lab** — Enter some text and generate speech

---

## 📊 Dashboard

The Dashboard is your command center. It shows a real-time overview of the entire system.

### Stats Cards

Four summary cards appear at the top:

| Card | What It Shows |
|------|--------------|
| **Voice Profiles** | Total profiles and how many are in "ready" state |
| **Active Training Jobs** | Number of jobs currently queued, preprocessing, or training |
| **Recent Syntheses** | Count of recent synthesis operations |
| **Providers Active** | How many providers are enabled out of the total 9 |

### Provider Health Grid

A 9-cell grid showing every provider with its current health status:

| Badge | Meaning |
|-------|---------|
| 🟢 **healthy** | Provider passed its health check |
| 🔴 **unhealthy** | Provider failed health check (hover for details) |
| 🟡 **pending** | Health check has not run yet |

Health checks verify that the provider can be reached and that required dependencies (models, API keys, runtimes) are available.

### Active Training Jobs

If any training jobs are running, they appear in a list showing:
- Profile ID (truncated)
- Provider name
- Progress bar (0-100%)
- Status badge (queued / preprocessing / training)

### Recent Synthesis

A table of the most recent synthesis operations showing the text snippet, provider used, latency in milliseconds, and timestamp.

---

## 📚 Voice Library

The Voice Library aggregates **290+ voices** from all available providers into a single, searchable catalog with preview playback.

### Browsing Voices

Navigate to **Voice Library** in the sidebar. The page loads all voices from every healthy provider and displays them in a card grid.

Each voice card shows:
- Voice name
- Provider name and logo
- Language code (e.g., `en`, `zh`, `ja`)
- Provider badge (cloud / local / GPU)

### Preview Playback

Click the **Preview** button on any voice card to hear a short sample. Previews are synthesized on demand and cached for instant replay on subsequent plays. The preview uses a default phrase: "Hello, this is a preview of my voice." — you can also specify custom text via the API (`POST /api/v1/voices/preview`).

### Filtering

Use the dropdown filters at the top to narrow results:

| Filter | Options |
|--------|---------|
| **Provider** | All Providers, Kokoro, Piper, ElevenLabs, Azure Speech, etc. |
| **Language** | All Languages, en, zh, ja, de, fr, etc. |
| **Search** | Free-text search by voice name |

### Creating a Profile from a Voice

When you find a voice you like, click the **Create Profile** button on its card. This:
1. Creates a new Voice Profile linked to that provider
2. Sets the voice as the default for synthesis
3. Redirects you to the Voice Profiles page

---

## 🎤 Voice Profiles

Voice Profiles are the central concept in Atlas Vox. A profile represents a voice identity bound to a specific provider.

### Profile Status Lifecycle

```
pending ──> training ──> ready
                │
                └──> error
```

| Status | Meaning |
|--------|---------|
| **pending** | Profile created, no model trained yet. Can synthesize with provider default voices. |
| **training** | A training job is running for this profile |
| **ready** | Model trained and activated. Full synthesis available. |
| **error** | Training failed. Check training job logs for details. |
| **archived** | Profile is deactivated but retained for history |

### Creating a New Profile

There are two ways to create a profile:

**Mode 1: Library Voice (recommended for beginners)**
1. Go to **Voice Library** and browse the 290+ available voices
2. Find a voice you like and click **Create Profile** on its card
3. The profile is created with that voice pre-selected and ready for synthesis

**Mode 2: Custom Training**
1. Go to **Voice Profiles** in the sidebar
2. Click **Create Profile**
3. Fill in the form:
   - **Name** — A descriptive name (e.g., "Sarah - Customer Service")
   - **Description** — Optional notes about this voice
   - **Language** — Primary language code (default: `en`)
   - **Provider** — Select which TTS provider to use
   - **Tags** — Optional tags for organization
4. Click **Create**
5. Upload audio samples and train a custom voice model

The profile starts in `pending` status. You can immediately use it for synthesis with the provider's built-in voices, or upload audio samples and train a custom voice.

> **Note on Training:** Only **ElevenLabs**, **Coqui XTTS v2**, and **StyleTTS2** currently support voice training/cloning. Other providers use their built-in voices for synthesis.

### Managing Profiles

On the Voice Profiles page, each profile card shows:
- Name and description
- Provider (with logo)
- Status badge
- Sample count and version count
- Created date

**Actions available:**
- **Edit** — Update name, description, tags
- **Delete** — Permanently remove the profile and all its data
- **Train** — Go to Training Studio with this profile selected

### Model Versions

Each successful training run creates a new **Model Version**. You can:
- View all versions for a profile via the API: `GET /api/v1/profiles/{id}/versions`
- Activate a specific version: `POST /api/v1/profiles/{id}/activate-version/{version_id}`

The active version is used when synthesizing with that profile.

---

## 🔧 Providers

Atlas Vox supports **9 TTS providers** running inside Docker or locally. Each provider extends a common `TTSProvider` interface and declares its capabilities dynamically. The UI adapts automatically based on what each provider supports.

### Provider Types

| Type | Meaning | Examples |
|------|---------|---------|
| **Cloud** | Runs on external servers, requires API key | ElevenLabs, Azure Speech |
| **Local CPU** | Runs entirely on your machine, no GPU needed | Kokoro, Piper |
| **Local GPU** | Runs locally, optional GPU acceleration | Coqui XTTS, StyleTTS2, CosyVoice, Dia, Dia2 |

### GPU Modes (for configurable providers)

| Mode | Environment Variable Example | Description |
|------|------------------------------|-------------|
| `host_cpu` | `COQUI_XTTS_GPU_MODE=host_cpu` | Run on host CPU (default, always works) |
| `docker_gpu` | `COQUI_XTTS_GPU_MODE=docker_gpu` | Use NVIDIA GPU inside Docker container |
| `auto` | `COQUI_XTTS_GPU_MODE=auto` | Auto-detect GPU, fallback to CPU |

### Configuring Providers

1. Go to **Providers** in the sidebar
2. Click the **Settings** (gear) icon on a provider card to expand configuration
3. Enter required fields (API keys, model paths, etc.)
4. Click **Save**
5. Run a **Health Check** to verify the configuration
6. Optionally run a **Test Synthesis** to confirm audio output

### Provider Capabilities Matrix

| Provider | Cloning | Streaming | SSML | Batch | Zero-Shot | GPU |
|----------|:-------:|:---------:|:----:|:-----:|:---------:|-----|
| Kokoro | | | | | | CPU |
| Piper | | | | | | CPU |
| ElevenLabs | ✅ | ✅ | | ✅ | | Cloud |
| Azure Speech | ✅ | ✅ | ✅ | | | Cloud |
| Coqui XTTS v2 | ✅ | ✅ | | | ✅ | Configurable |
| StyleTTS2 | ✅ | | | | ✅ | Configurable |
| CosyVoice | ✅ | ✅ | | | | Configurable |
| Dia | ✅ | | | | | Configurable |
| Dia2 | | ✅ | | | | Configurable |

---

### Kokoro

**Type:** Local CPU | **Model:** 82M parameters, ONNX | **Voices:** 54 built-in

Kokoro is the default provider in Atlas Vox. It is lightweight, fast, and requires no GPU or API key.

**Key Features:**
- 54 built-in voices with American and British English accents
- CPU-only inference via ONNX runtime
- Ultra-fast synthesis (sub-second for short text)
- No internet connection required

**Configuration:**
- No configuration needed. Works out of the box.
- To disable: set `KOKORO_ENABLED=false`

**Best For:**
- Quick prototyping and testing
- Systems without GPU
- Low-latency requirements

**Tips:**
- Kokoro voices are named with prefixes: `af_` (American female), `am_` (American male), `bf_` (British female), `bm_` (British male)
- For best quality, keep text under 500 characters per synthesis call

---

### Piper

**Type:** Local CPU | **Model:** ONNX VITS | **Voices:** 100+ across 30+ languages

Piper is a fast, local TTS engine optimized for embedded devices like Raspberry Pi and Home Assistant.

**Key Features:**
- Very low resource usage (runs on Raspberry Pi)
- ONNX-based VITS models
- 30+ languages with pre-trained voices
- Home Assistant compatible

**Configuration:**
| Setting | Default | Description |
|---------|---------|-------------|
| `PIPER_ENABLED` | `true` | Enable/disable Piper |
| `PIPER_MODEL_PATH` | `./storage/models/piper` | Path to ONNX model files |

The default English model (`en_US-lessac-medium`) is downloaded automatically during Docker build.

**Adding More Voices:**
1. Download ONNX models from [Piper Voices](https://github.com/rhasspy/piper/blob/master/VOICES.md)
2. Place the `.onnx` and `.onnx.json` files in the Piper model directory
3. Restart the backend — new voices appear automatically

**Best For:**
- Multilingual applications
- Home automation
- Embedded/edge deployment

**Tips:**
- Use `medium` quality models for the best balance of speed and quality
- `low` quality models are faster but less natural
- `high` quality models sound great but are larger and slower

---

### ElevenLabs

**Type:** Cloud | **Pricing:** Freemium (free tier available) | **Quality:** Premium

ElevenLabs provides industry-leading voice synthesis with the most natural-sounding output available.

**Key Features:**
- Most natural and expressive voices in the market
- Instant voice cloning from short audio
- Streaming support for real-time applications
- 29 languages supported
- Voice design (create entirely new voices)

**Configuration:**
| Setting | Required | Description |
|---------|----------|-------------|
| `ELEVENLABS_API_KEY` | Yes | Your ElevenLabs API key |
| `ELEVENLABS_MODEL_ID` | No | Model to use (default: `eleven_multilingual_v2`) |

**Getting Your API Key:**
1. Sign up at [elevenlabs.io](https://elevenlabs.io)
2. Go to Profile Settings
3. Copy your API key
4. Enter it in the provider configuration page

**Free Tier Limits:**
- 10,000 characters per month
- 3 custom voices
- Basic voice cloning

**Best For:**
- Production-quality voiceovers
- Content creation
- When quality matters more than cost

**Tips:**
- The `eleven_multilingual_v2` model supports all 29 languages
- For English-only use, `eleven_monolingual_v1` is faster
- Use streaming mode for real-time applications
- Voice cloning works best with 1-5 minutes of clean audio

---

### Azure Speech

**Type:** Cloud | **Pricing:** Paid (free tier: 500K characters/month) | **Quality:** Enterprise

Microsoft Azure AI Speech provides enterprise-grade TTS with full SSML support and 400+ neural voices.

**Key Features:**
- Full SSML (Speech Synthesis Markup Language) support
- 400+ neural voices across 140+ languages
- Enterprise SLA and reliability
- Custom Neural Voice (CNV) for professional voice cloning
- Streaming support

**Configuration:**
| Setting | Required | Description |
|---------|----------|-------------|
| `AZURE_SPEECH_KEY` | Yes | Azure subscription key |
| `AZURE_SPEECH_REGION` | Yes | Azure region (default: `eastus`) |

**Getting Your Credentials:**
1. Create an Azure account at [azure.microsoft.com](https://azure.microsoft.com)
2. Create a Speech resource in the Azure Portal
3. Copy the Key and Region from the resource's Keys and Endpoint page
4. Enter them in the provider configuration page

**Free Tier:**
- 500,000 characters per month (neural voices)
- Standard and neural voices
- No voice cloning on free tier

**SSML Support:**

Azure is the only provider with full SSML support. You can use SSML tags to control:
```xml
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
  <voice name="en-US-JennyNeural">
    <prosody rate="+20%" pitch="+5%">
      This text will be spoken faster and higher.
    </prosody>
    <break time="500ms"/>
    <emphasis level="strong">This is important.</emphasis>
  </voice>
</speak>
```

**Best For:**
- Enterprise applications with SLA requirements
- Multilingual content (140+ languages)
- Fine-grained speech control via SSML
- Applications already on Azure

**Tips:**
- Use `en-US-JennyNeural` for natural conversational English
- The `eastus` region typically has the lowest latency for US users
- SSML mode must be enabled in the synthesis request (`ssml: true`)

---

### Coqui XTTS v2

**Type:** Local GPU (configurable) | **Model:** ~1.5B parameters | **Cloning:** 6 seconds of audio

XTTS v2 from Coqui AI is the leading open-source voice cloning model. It can clone a voice from just 6 seconds of reference audio.

**Key Features:**
- Voice cloning from 6 seconds of audio
- Zero-shot synthesis (no fine-tuning required)
- 17 languages supported
- Streaming support
- Fully local — no data leaves your machine

**Configuration:**
| Setting | Default | Description |
|---------|---------|-------------|
| `COQUI_XTTS_GPU_MODE` | `host_cpu` | GPU mode: `host_cpu`, `docker_gpu`, or `auto` |

**Hardware Requirements:**
- **CPU mode**: 16 GB RAM, synthesis takes 5-30 seconds per sentence
- **GPU mode**: 4 GB+ VRAM, synthesis takes 0.5-3 seconds per sentence

**Best For:**
- Voice cloning with minimal audio
- Multilingual voice cloning
- Privacy-sensitive applications

**Tips:**
- For best cloning results, provide clean audio without background noise
- 15-30 seconds of audio gives noticeably better results than the 6-second minimum
- GPU mode is strongly recommended for usable inference speed
- The model downloads automatically on first use (~1.8 GB)

---

### StyleTTS2

**Type:** Local GPU (configurable) | **Model:** ~200M parameters

StyleTTS2 uses style diffusion and adversarial training to achieve human-level speech quality with zero-shot style transfer.

**Key Features:**
- Human-level speech quality (MOS score comparable to human speech)
- Zero-shot voice cloning
- Style transfer between voices
- Relatively small model size (~200M parameters)

**Configuration:**
| Setting | Default | Description |
|---------|---------|-------------|
| `STYLETTS2_GPU_MODE` | `host_cpu` | GPU mode: `host_cpu`, `docker_gpu`, or `auto` |

**Dependencies:**
- Requires `espeak-ng` (installed automatically in Docker)
- NLTK `punkt` data (downloaded during Docker build)

**Best For:**
- Highest quality English TTS
- Style transfer experiments
- Research and evaluation

**Tips:**
- StyleTTS2 excels at English but is primarily English-only
- CPU mode is very slow — GPU is strongly recommended
- Style transfer lets you apply the speaking style of one voice to another voice's identity

---

### CosyVoice

**Type:** Local GPU (configurable) | **Model:** CosyVoice-300M-SFT

CosyVoice from Alibaba provides multilingual TTS with natural prosody and streaming support.

**Key Features:**
- 9 languages with natural prosody
- Streaming output with ~150ms latency
- Voice cloning support
- Compact model size (300M parameters)

**Configuration:**
| Setting | Default | Description |
|---------|---------|-------------|
| `COSYVOICE_GPU_MODE` | `host_cpu` | GPU mode: `host_cpu`, `docker_gpu`, or `auto` |

**Supported Languages:**
Chinese, English, Japanese, Korean, French, German, Spanish, Italian, Portuguese

**Best For:**
- Chinese and Asian language TTS
- Low-latency streaming applications
- Multilingual voice cloning

**Tips:**
- CosyVoice handles code-switching between languages naturally
- The streaming mode achieves ~150ms first-chunk latency on GPU
- Mandarin Chinese quality is particularly strong

---

### Dia

**Type:** Local GPU (configurable) | **Model:** 1.6B parameters

Dia from Nari Labs is a dialogue-focused TTS model that generates natural multi-speaker conversations with non-verbal sounds.

**Key Features:**
- Multi-speaker dialogue generation
- Non-verbal sounds (laughter, sighs, pauses)
- Voice cloning support
- 1.6B parameter model

**Configuration:**
| Setting | Default | Description |
|---------|---------|-------------|
| `DIA_GPU_MODE` | `host_cpu` | GPU mode: `host_cpu`, `docker_gpu`, or `auto` |

**Dialogue Format:**

Dia uses a special tag format for multi-speaker dialogue:
```
[S1] Hello, how are you today?
[S2] I'm doing great! (laughs) How about you?
[S1] Pretty good, thanks for asking.
```

**Best For:**
- Podcast and conversation generation
- Interactive dialogue systems
- Content that needs natural non-verbal sounds

**Tips:**
- Use `[S1]` and `[S2]` tags to mark different speakers
- Enclose non-verbal sounds in parentheses: `(laughs)`, `(sighs)`, `(clears throat)`
- GPU mode is strongly recommended — the 1.6B model is slow on CPU
- Requires 6 GB+ VRAM

---

### Dia2

**Type:** Local GPU (configurable) | **Model:** 2B parameters

Dia2 is the next-generation dialogue model from Nari Labs with streaming support and improved quality.

**Key Features:**
- 2B parameter model (larger than Dia)
- Streaming dialogue generation
- Real-time conversation output
- Improved prosody and naturalness

**Configuration:**
| Setting | Default | Description |
|---------|---------|-------------|
| `DIA2_GPU_MODE` | `host_cpu` | GPU mode: `host_cpu`, `docker_gpu`, or `auto` |

**Best For:**
- Real-time dialogue applications
- When Dia's quality is not sufficient
- Streaming conversation generation

**Tips:**
- Dia2 requires 8 GB+ VRAM for comfortable operation
- Streaming mode is the primary advantage over Dia
- The 2B parameter model downloads on first use (~4 GB)
- CPU mode is impractical for this model — use GPU

---

## 🎓 Training Studio

The Training Studio is where you upload audio samples and train custom voice models.

> **Important:** Only **ElevenLabs**, **Coqui XTTS v2**, and **StyleTTS2** currently support voice training. Other providers use their built-in or cloned voices for synthesis.

### Workflow

```
Select Profile ──> Upload Audio ──> Preprocess ──> Train ──> Ready
```

### Step 1: Select a Profile

Choose the voice profile you want to train from the dropdown. If you do not have one yet, create one in the Voice Profiles page first.

### Step 2: Upload Audio Samples

You can add audio samples in two ways:

**File Upload:**
- Click "Upload Files" or drag and drop
- Supported formats: WAV, MP3, FLAC, OGG, M4A
- Maximum 20 files per upload
- Maximum 50 MB per file

**Record Audio:**
- Click "Record" to capture audio directly in the browser
- Uses your microphone (browser will request permission)
- Click "Stop" when finished

**Audio Guidelines for Best Results:**

| Guideline | Recommendation |
|-----------|---------------|
| **Duration** | 5 minutes minimum, 15-30 minutes ideal |
| **Quality** | 16 kHz sample rate minimum, 44.1 kHz ideal |
| **Noise** | Quiet room, no background noise |
| **Content** | Varied sentences, natural speech patterns |
| **Consistency** | Same speaker, same microphone, same room |

### Step 3: Preprocess

Click **Preprocess** to prepare your audio:
- Noise reduction
- Volume normalization
- Resampling to 16 kHz
- Audio analysis (pitch, energy, spectral features)

Preprocessing runs as a background Celery task. You will see a task ID and can monitor progress.

### Step 4: Train

Click **Start Training** to begin. Training:
1. Creates a Celery task
2. Shows a progress bar via WebSocket
3. Creates a new Model Version on success
4. Updates the profile status to `ready`

### Monitoring Progress

The Training Studio shows real-time progress for active jobs:
- **queued** — Waiting for a Celery worker
- **preprocessing** — Audio is being prepared
- **training** — Model training in progress (with percent complete)
- **completed** — Training finished, model ready
- **failed** — Something went wrong (check error message)

You can **cancel** a running job at any time.

---

## 🔊 Synthesis Lab

The Synthesis Lab is where you turn text into speech.

### Basic Synthesis

1. Enter text in the text area (up to 10,000 characters)
2. Select a Voice Profile from the dropdown
3. Adjust parameters (optional):
   - **Speed**: 0.5x to 2.0x (default: 1.0x)
   - **Pitch**: -50 to +50 semitones (default: 0)
   - **Volume**: 0.0 to 2.0 (default: 1.0)
4. Click **Synthesize**
5. Listen to the result with the built-in audio player

### Persona Presets

Instead of manually adjusting speed, pitch, and volume, you can use persona presets:

| Preset | Speed | Pitch | Volume | Character |
|--------|-------|-------|--------|-----------|
| **Friendly** | 1.0x | +2 | 1.0 | Warm and approachable |
| **Professional** | 0.95x | 0 | 1.0 | Clear and authoritative |
| **Energetic** | 1.15x | +5 | 1.1 | Upbeat and enthusiastic |
| **Calm** | 0.85x | -3 | 0.9 | Soothing and relaxed |
| **Authoritative** | 0.9x | -5 | 1.15 | Commanding and confident |
| **Soothing** | 0.8x | -2 | 0.85 | Gentle and comforting |

You can create custom presets with your own parameter combinations.

### SSML Mode

For Azure Speech profiles, you can toggle SSML mode to use Speech Synthesis Markup Language for fine-grained control over pronunciation, pauses, emphasis, and more.

### Output Formats

| Format | Description |
|--------|-------------|
| **WAV** | Lossless, highest quality, larger files |
| **MP3** | Compressed, good quality, smaller files |
| **OGG** | Compressed, open format, small files |

### Synthesis History

The right panel shows your recent synthesis history with:
- Text snippet
- Provider used
- Latency (ms)
- Timestamp
- Playback link

### Batch Synthesis

Via the API, you can synthesize multiple lines in a single request:
```json
POST /api/v1/synthesize/batch
{
  "lines": ["First line.", "Second line.", "Third line."],
  "profile_id": "your-profile-id",
  "speed": 1.0
}
```

### Streaming Synthesis

For providers that support streaming (ElevenLabs, Azure, Coqui XTTS, CosyVoice, Dia2), you can use the streaming endpoint for lower time-to-first-audio:

```
POST /api/v1/synthesize/stream
```

Returns chunked transfer encoding with audio data.

---

## ⚖️ Comparison

The Comparison page lets you synthesize the same text with multiple voice profiles side by side.

### How to Compare

1. Go to **Comparison** in the sidebar
2. Enter the text you want to compare
3. Select 2 or more Voice Profiles
4. Adjust speed and pitch (optional)
5. Click **Compare**

### Understanding Results

Each result card shows:
- Profile name and provider
- Audio player for playback
- Duration and latency metrics

This is useful for:
- A/B testing different providers
- Comparing voice quality
- Finding the best voice for your use case
- Evaluating training results

---

## 🔑 API Keys

API Keys provide programmatic access to the Atlas Vox API.

### Creating a Key

1. Go to **API Keys** in the sidebar
2. Click **Create Key**
3. Enter a name (e.g., "Production App", "CI/CD Pipeline")
4. Select scopes:
   - **read** — List profiles, providers, voices, presets, history
   - **write** — Create/update/delete profiles, presets, webhooks
   - **synthesize** — Run synthesis and comparison
   - **train** — Start and manage training jobs
   - **admin** — Full access including API key management
5. Click **Create**

> ⚠️ **Important:** The full API key is shown only once. Copy it immediately and store it securely.

### Key Format

Keys follow the format: `avx_` + 48 random characters. Example:
```
avx_Tz2Kx8wY4mPqR7vN3jL6...
```

Only the first 12 characters (prefix) are stored and shown in the UI. The full key is hashed with Argon2id.

### Using API Keys

Pass the key in the `Authorization` header:
```bash
curl -H "Authorization: Bearer avx_your_key_here" \
  http://localhost:8100/api/v1/profiles
```

### Revoking Keys

Click the delete icon next to any key to deactivate it. Revoked keys immediately stop working.

> 📋 **Note:** When `AUTH_DISABLED=true` (the default), API keys are not required. All endpoints accept unauthenticated requests. Set `AUTH_DISABLED=false` for production use.

---

## ⚙️ Settings

The Settings page controls application-wide preferences.

### Appearance

**Theme** — Switch between Light and Dark mode. The selection persists in your browser's local storage.

### Defaults

| Setting | Options | Description |
|---------|---------|-------------|
| **Default Provider** | Any enabled provider | Pre-selected when creating new profiles |
| **Default Audio Format** | WAV, MP3, OGG | Pre-selected in Synthesis Lab |

### About

Shows version information:
- Atlas Vox v0.1.0
- 9 TTS providers
- 4 interfaces (Web UI, REST API, CLI, MCP Server)

---

## 💡 Keyboard Shortcuts & Tips

### Performance Tips

- **Use GPU mode** for Coqui XTTS, StyleTTS2, CosyVoice, Dia, and Dia2 — CPU mode is 10-50x slower
- **Kokoro and Piper** are the fastest providers on CPU
- **Batch synthesis** is more efficient than individual requests for multiple lines
- **Streaming synthesis** gives faster time-to-first-audio for supported providers

### Audio Quality Tips

- **Clean audio** is critical for voice cloning — use a good microphone in a quiet room
- **15-30 minutes** of audio gives the best training results
- **Varied content** (different sentences, emotions, pacing) produces more versatile models
- **Consistent recording conditions** (same mic, same room) improve model quality

### Organization Tips

- Use **tags** on voice profiles to organize by project, client, or purpose
- Create **custom presets** for recurring voice configurations
- Use **descriptive names** for profiles: "Sarah - Customer Service EN" is better than "Voice 1"

### Troubleshooting Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| Provider shows "unhealthy" | Check API key, run health check |
| Synthesis fails | Check provider health, verify profile has correct provider |
| Training stuck at "queued" | Ensure Redis is running, check Celery worker logs |
| No audio output | Check browser audio permissions, try WAV format |
| GPU not detected | Verify NVIDIA Container Toolkit, check GPU mode env var |
For detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

<div align="center">

**Need more help?** Check the [API Reference](API_REFERENCE.md) | [Deployment Guide](DEPLOYMENT.md) | [Architecture](ARCHITECTURE.md)

Atlas Vox v0.1.0

</div>
