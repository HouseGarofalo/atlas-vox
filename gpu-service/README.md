# Atlas Vox GPU Service

A standalone FastAPI service that runs natively on your Windows host to provide GPU-accelerated TTS synthesis. The Dockerized Atlas Vox backend connects to this service via HTTP.

## Prerequisites

- **Python 3.11+** (3.10 minimum)
- **NVIDIA GPU** with CUDA support (CUDA 12.x recommended)
- **PyTorch** with CUDA — install from https://pytorch.org/get-started/locally/

## Quick Start

```bash
# 1. Create and activate a virtual environment
cd gpu-service
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/macOS

# 2. Install PyTorch with CUDA first (example for CUDA 12.4)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124

# 3. Install the GPU service
pip install -e .

# 4. (Optional) Download model weights ahead of time
python scripts/download_models.py --list       # See available models
python scripts/download_models.py --all        # Download everything
python scripts/download_models.py --provider fish_speech  # Just one

# 5. Start the service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8200 --reload
# Or use the convenience scripts:
scripts\start.bat          # CMD
.\scripts\start.ps1        # PowerShell
```

The service will be available at **http://localhost:8200**.

## Installing Individual Providers

Each provider has its own dependencies. Install only what you need:

| Provider | Install Command |
|----------|----------------|
| Fish Speech 1.5 | `pip install fish-speech` |
| Chatterbox | `git clone https://github.com/resemble-ai/chatterbox && cd chatterbox && pip install -e .` |
| F5-TTS | `pip install f5-tts` |
| OpenVoice v2 | `git clone https://github.com/myshell-ai/OpenVoice && cd OpenVoice && pip install -e .` |
| Orpheus TTS | See the Orpheus TTS repository for installation |
| Piper Training | `pip install piper-train` |

## Configuration

All settings use the `GPU_` environment variable prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `GPU_HOST` | `0.0.0.0` | Bind address |
| `GPU_PORT` | `8200` | Port number |
| `GPU_STORAGE_PATH` | `./storage` | Storage for cloned voices and temp files |
| `GPU_DEFAULT_DEVICE` | `cuda:0` | Default CUDA device |
| `GPU_DEVICE_MAP` | `{}` | JSON mapping provider name to device (e.g. `{"openvoice_v2": "cuda:1"}`) |
| `GPU_AUTO_LOAD_PROVIDERS` | `[]` | JSON list of providers to load on startup (e.g. `["fish_speech"]`) |
| `GPU_CORS_ORIGINS` | `["http://localhost:3000", "http://localhost:8000"]` | Allowed CORS origins |
| `GPU_LOG_LEVEL` | `INFO` | Log level |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health check |
| `GET` | `/providers` | List all providers with capabilities |
| `GET` | `/providers/{name}/voices` | List voices for a provider |
| `POST` | `/providers/{name}/load` | Load model into VRAM |
| `POST` | `/providers/{name}/unload` | Unload model from VRAM |
| `POST` | `/providers/{name}/synthesize` | Synthesize text to WAV audio |
| `POST` | `/providers/{name}/clone` | Clone voice from reference audio |
| `POST` | `/providers/{name}/health` | Provider health check |
| `GET` | `/gpu/status` | GPU utilization and device info |

### Example: Synthesize

```bash
# Load a provider first
curl -X POST http://localhost:8200/providers/fish_speech/load

# Synthesize
curl -X POST http://localhost:8200/providers/fish_speech/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from Atlas Vox!", "voice_id": "default"}' \
  --output output.wav
```

### Example: Clone a Voice

```bash
curl -X POST http://localhost:8200/providers/fish_speech/clone \
  -F "files=@reference.wav" \
  -F "voice_name=my_voice" \
  -F "language=en"
```

## Connecting Atlas Vox

In the main Atlas Vox backend, set the GPU service URL:

```env
GPU_SERVICE_URL=http://host.docker.internal:8200
```

When running Atlas Vox in Docker, `host.docker.internal` resolves to the Windows host where this GPU service runs.

## Multi-GPU Setup

Assign providers to specific GPUs via `GPU_DEVICE_MAP`:

```env
GPU_DEVICE_MAP={"fish_speech": "cuda:0", "orpheus": "cuda:1", "openvoice_v2": "cuda:0"}
```

## Architecture

```
Atlas Vox (Docker)                    GPU Service (Host)
+-----------------+                   +------------------+
| FastAPI Backend |  --- HTTP --->    | FastAPI (port 8200)
| (port 8000)     |                   |   |
+-----------------+                   |   +-- Fish Speech
                                      |   +-- Chatterbox
                                      |   +-- F5-TTS
                                      |   +-- OpenVoice v2
                                      |   +-- Orpheus TTS
                                      |   +-- Piper Training
                                      +------------------+
                                            |
                                      NVIDIA GPU (CUDA)
```
