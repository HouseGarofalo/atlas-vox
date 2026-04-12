# Troubleshooting

Frequently asked questions organized by category.

---

## Installation

### How do I start Atlas Vox with Docker?

Run `make docker-up` from the project root. This starts the backend, frontend, Redis, and a Celery worker. The Web UI is at http://localhost:3100.

### Docker build fails during pip install

Rebuild with no cache: `docker compose -f docker/docker-compose.yml build --no-cache backend`. Usually caused by network issues or PyPI rate limiting.

### Port 3100 or 8100 is already in use

Edit `docker/.env` and change `BACKEND_PORT` / `FRONTEND_PORT`. Then restart with `make docker-up`.

### Redis connection fails on startup

Atlas Vox uses Redis database 1 (`redis://localhost:6379/1`) to avoid collision with other services on database 0. Ensure Redis is running: `redis-server` or check Docker.

---

## Providers

### A provider shows as 'unhealthy' on the dashboard

Go to Providers, expand the provider, and click Health Check to see the specific error. Common causes: missing API key (cloud), missing model files (local), or GPU not available.

### How do I configure ElevenLabs?

Get your API key from elevenlabs.io/settings. Go to Providers > ElevenLabs > Settings, enter the API key, click Save, then run a Health Check.

### How do I configure Azure Speech?

Create a Speech resource in the Azure Portal. Copy Key 1 and Region from Keys and Endpoint. Enter them in Providers > Azure Speech > Settings.

### How do I enable GPU mode for local providers?

Run `make docker-gpu-up` instead of `make docker-up`. This starts a GPU worker with CUDA 12.1 and auto-enables GPU mode for Coqui XTTS, StyleTTS2, CosyVoice, Dia, and Dia2.

### Can I use multiple cloud providers at the same time?

Yes. Each provider is independent. Configure API keys for both ElevenLabs and Azure Speech, and you can use either from the Synthesis Lab or Comparison page.

---

## Audio

### Synthesis succeeds but no audio plays

Check the audio URL in the response. Try accessing it directly: `http://localhost:8100/api/v1/audio/<filename>`. Verify browser console for errors. Try WAV format instead of MP3/OGG.

### Audio upload is rejected as unsupported format

Atlas Vox supports WAV, MP3, FLAC, OGG, and M4A. Convert your file with: `ffmpeg -i input.webm output.wav`

### Audio sounds distorted or clipped

Check the volume slider (should be between 0.8 and 1.2 for most cases). If using a cloned voice, ensure training samples were clean without clipping. Re-preprocess with noise reduction enabled.

---

## Training

### Training job stuck at 'queued'

The Celery worker is not running or not connected to Redis. In Docker: `docker compose -f docker/docker-compose.yml logs worker`. For local dev, start Celery manually.

### Training fails immediately

Ensure you have uploaded and preprocessed audio samples before starting training. Check the training job error message for the specific cause (common: insufficient samples or corrupted audio).

### How many audio samples do I need for voice cloning?

Minimum: 1 sample of 6+ seconds (Coqui XTTS). For best quality: 10-30 minutes of clean speech split into 5-15 second segments. More data generally produces better results up to about 1 hour.

---

## Synthesis

### Synthesis returns an empty audio file

The provider may have returned an error silently. Check backend logs: `docker compose logs backend | tail -50`. Common cause: text too short (some providers need at least a few words) or invalid voice ID.

### SSML is not being interpreted

SSML is only supported by Azure Speech. Switch to the Azure Speech provider and ensure you are in SSML mode (click 'Switch to SSML' in the Synthesis Lab). Validate your SSML markup.

### Streaming synthesis is choppy

Streaming quality depends on network and provider. Use a wired connection for cloud providers. For local providers, ensure the GPU is not overloaded. Reduce text length for smoother streaming.

---

## Database

### Getting 'no such table' errors

Run `make migrate` to apply database migrations. For a fresh start, delete `atlas_vox.db` and restart -- tables are created automatically.

### Can I switch from SQLite to PostgreSQL?

Yes. Set `DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname` in your `.env` file. Run `make migrate` to create tables. PostgreSQL is recommended for production deployments.

---

## Self-Healing

### What triggers self-healing remediation?

Configurable rules: consecutive health check failures (default: 3), average latency exceeding threshold (default: 5000ms), error rate above threshold in a time window (default: 50% in 5 minutes). Each rule can be customized per provider.

### A provider keeps restarting due to self-healing

Check the incident log for the root cause. Common: GPU out of memory (reduce batch size or switch to CPU), missing model files (re-download), or rate limiting (increase cooldown). Disable auto-remediation for that provider temporarily via the Self-Healing settings.

---

## Performance

### Synthesis is very slow (10+ seconds)

GPU-oriented models (Coqui XTTS, StyleTTS2, Dia) on CPU are slow. Switch to GPU mode, or use Kokoro/Piper for fast CPU synthesis (typically <1 second).

### GPU memory errors (CUDA out of memory)

VRAM requirements: Dia2 needs 8 GB+, Dia needs 6 GB+, Coqui XTTS needs 4 GB+, StyleTTS2 needs 3 GB+, CosyVoice needs 4 GB+. Close other GPU applications, use shorter text, or switch to CPU mode.

### Getting '429 Too Many Requests' errors

Rate limits: synthesis 10/min, training 5/min, comparison 5/min, OpenAI-compatible 20/min. Wait a minute and try again, or reduce request frequency.
