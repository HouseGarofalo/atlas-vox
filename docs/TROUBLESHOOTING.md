# 🔧 Atlas Vox Troubleshooting Guide

> Solutions organized by category. Each issue includes the symptom, cause, fix, and prevention.

---

## Table of Contents

- [Installation Issues](#-installation-issues)
- [Provider Issues](#-provider-issues)
  - [General Provider Issues](#general-provider-issues)
  - [Kokoro](#kokoro)
  - [Piper](#piper)
  - [ElevenLabs](#elevenlabs)
  - [Azure Speech](#azure-speech)
  - [Coqui XTTS v2](#coqui-xtts-v2)
  - [StyleTTS2](#styletts2)
  - [CosyVoice](#cosyvoice)
  - [Dia / Dia2](#dia--dia2)
- [Audio Issues](#-audio-issues)
- [Database Issues](#-database-issues)
- [Network Issues](#-network-issues)
- [Training Issues](#-training-issues)
- [Performance Issues](#-performance-issues)
- [Frontend Issues](#-frontend-issues)

---

## 🏗️ Installation Issues

### Docker Build Fails with "pip install" Error

**Symptom:** `docker compose up --build` fails during pip install in the backend build stage.

**Cause:** Network issues, PyPI rate limiting, or dependency conflict.

**Fix:**
```bash
# Retry with no cache
docker compose -f docker/docker-compose.yml build --no-cache backend

# If behind a proxy, configure Docker proxy
# In ~/.docker/config.json:
# { "proxies": { "default": { "httpProxy": "http://proxy:8080" } } }
```

**Prevention:** Pin dependency versions in `pyproject.toml` (already done). Build images during off-peak hours if on restricted networks.

---

### Docker Build Fails with "COPY failed: file not found"

**Symptom:** `COPY backend/pyproject.toml` fails.

**Cause:** Docker build context is incorrect. The Dockerfiles expect the project root as context.

**Fix:** Always build from the project root using the Makefile:
```bash
make docker-up
# Which runs: docker compose -f docker/docker-compose.yml up --build
```

If running manually, ensure context is the parent of the `docker/` directory:
```bash
docker compose -f docker/docker-compose.yml up --build
```

---

### Port Conflict on Startup

**Symptom:** `Error starting userland proxy: listen tcp4 0.0.0.0:3100: bind: address already in use`

**Cause:** Another service is using port 3100 (frontend) or 8100 (backend).

**Fix:**
```bash
# Option 1: Change ports in docker/.env
echo "BACKEND_PORT=8200" >> docker/.env
echo "FRONTEND_PORT=3200" >> docker/.env

# Option 2: Find and stop the conflicting process
# Linux/macOS
lsof -i :3100
kill -9 <PID>

# Windows
netstat -aon | findstr :3100
taskkill /PID <PID> /F
```

**Prevention:** Use non-standard ports by customizing `docker/.env` before first start.

---

### "make: command not found" (Windows)

**Symptom:** Running `make docker-up` fails on Windows.

**Cause:** GNU Make is not installed on Windows by default.

**Fix:**
```bash
# Option 1: Use the Docker command directly
docker compose -f docker/docker-compose.yml up --build

# Option 2: Install Make via Chocolatey
choco install make

# Option 3: Install Make via winget
winget install GnuWin32.Make
```

---

### "npm ci" Fails During Frontend Build

**Symptom:** Docker build fails at `RUN npm ci` in the frontend stage.

**Cause:** Missing or outdated `package-lock.json`.

**Fix:**
```bash
# Regenerate the lockfile
cd frontend
npm install
# Commit the updated package-lock.json
```

---

### Redis Connection Refused

**Symptom:** Backend logs show `redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379. Connection refused.`

**Cause:** Redis is not running.

**Fix:**
```bash
# Docker: Redis starts automatically with docker-compose
make docker-up

# Local development: Start Redis
# macOS
brew services start redis

# Linux
sudo systemctl start redis-server

# Windows (WSL2)
sudo service redis-server start
```

**Prevention:** Use Docker Compose which manages Redis automatically.

---

## 🔌 Provider Issues

### General Provider Issues

#### Provider Shows "Unhealthy" on Dashboard

**Symptom:** Provider card shows a red "unhealthy" badge.

**Cause:** The health check failed. Common reasons:
- Missing API key (cloud providers)
- Model not downloaded (local providers)
- Dependency not installed
- GPU not available when required

**Fix:**
1. Go to **Providers** page
2. Click the provider to expand details
3. Click **Health Check** to see the specific error
4. Address the error (see provider-specific sections below)

---

#### "Provider not available" Error

**Symptom:** `HTTP 404: Provider 'xxx' not available`

**Cause:** The provider's Python dependencies are not installed, or the provider failed to initialize.

**Fix:**
```bash
# Check backend logs for import errors
docker compose -f docker/docker-compose.yml logs backend | grep -i "import\|error\|failed"

# Common: install provider-specific dependencies
cd backend
pip install -e ".[audio]"
```

---

#### Provider Config Not Saving

**Symptom:** Configuration changes revert after restart.

**Cause:** Provider database record may not exist.

**Fix:**
```bash
# Seed providers in database
make seed
# Or via API
curl -X POST http://localhost:8100/api/v1/providers/seed
```

---

### Kokoro

#### "No module named 'kokoro'"

**Symptom:** Kokoro health check fails with import error.

**Cause:** The `kokoro` package is not installed.

**Fix:**
```bash
pip install "kokoro>=0.9.4" "misaki[en]"
```

In Docker, this is installed automatically.

---

#### Kokoro Produces No Audio / Empty File

**Symptom:** Synthesis returns but audio file is empty or very short.

**Cause:** Voice ID not found or text too short.

**Fix:**
- Verify the voice ID exists: use the **Providers > Kokoro > Voices** list
- Ensure text is at least a few words long
- Check that the voice prefix matches the language (`af_` = American female, `am_` = American male)

---

### Piper

#### "Model file not found"

**Symptom:** Piper health check fails with "Model file not found at storage/models/piper/..."

**Cause:** The ONNX model was not downloaded during build, or the model path is wrong.

**Fix:**
```bash
# Download the default model manually
mkdir -p storage/models/piper
cd storage/models/piper
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

Verify `PIPER_MODEL_PATH` points to the correct directory.

---

#### Piper Requires espeak-ng

**Symptom:** `OSError: espeak-ng not found`

**Cause:** `espeak-ng` is not installed on the system.

**Fix:**
```bash
# Linux
sudo apt install espeak-ng

# macOS
brew install espeak-ng

# Docker: installed automatically via Dockerfile
```

---

### ElevenLabs

#### "Invalid API key" / 401 Error

**Symptom:** ElevenLabs health check returns "Unauthorized" or "Invalid API key".

**Cause:** API key is missing, invalid, or expired.

**Fix:**
1. Go to **Providers > ElevenLabs > Settings**
2. Enter your API key from [elevenlabs.io/settings](https://elevenlabs.io/settings)
3. Click **Save**
4. Run **Health Check**

Alternatively, set the environment variable:
```bash
ELEVENLABS_API_KEY=your_key_here
```

---

#### "Quota exceeded" / 429 Error

**Symptom:** Synthesis fails with "You have exceeded your character quota".

**Cause:** Free tier limit reached (10,000 characters/month).

**Fix:**
- Wait for the monthly reset
- Upgrade to a paid plan at elevenlabs.io
- Switch to a local provider (Kokoro, Piper) for testing

---

### Azure Speech

#### "Invalid subscription key" / 401 Error

**Symptom:** Azure health check fails with authentication error.

**Cause:** Subscription key or region is incorrect.

**Fix:**
1. Verify your key in the [Azure Portal](https://portal.azure.com) > Speech resource > Keys and Endpoint
2. Go to **Providers > Azure Speech > Settings**
3. Enter the correct key and region (e.g., `eastus`, `westeurope`)
4. Click **Save**

---

#### "Access denied" / SSML Error

**Symptom:** SSML synthesis returns "Access denied" or malformed SSML error.

**Cause:** SSML markup is invalid, or the requested voice is not available in your region.

**Fix:**
- Validate your SSML against the [Azure SSML schema](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup)
- Ensure the voice name matches exactly (e.g., `en-US-JennyNeural`)
- Check that the voice is available in your selected region

---

### Coqui XTTS v2

#### "TTS not installed" / Import Error

**Symptom:** `ModuleNotFoundError: No module named 'TTS'`

**Cause:** The Coqui TTS package is not installed or torch is missing.

**Fix:**
```bash
pip install "TTS>=0.22.0" torch
```

In Docker, this is handled by the Dockerfile (with `|| true` since it may fail on some platforms).

---

#### Model Download Hangs / Fails

**Symptom:** First synthesis takes very long or fails with a download error.

**Cause:** The XTTS v2 model (~1.8 GB) downloads on first use.

**Fix:**
- Ensure internet access from the container
- Pre-download the model:
  ```bash
  python -c "from TTS.api import TTS; TTS('tts_models/multilingual/multi-dataset/xtts_v2')"
  ```
- For air-gapped environments, download the model files manually and mount them as a volume

---

#### CUDA Out of Memory

**Symptom:** `RuntimeError: CUDA out of memory`

**Cause:** GPU does not have enough VRAM (minimum 4 GB).

**Fix:**
```bash
# Switch to CPU mode
COQUI_XTTS_GPU_MODE=host_cpu

# Or use a GPU with more VRAM
# Or reduce batch size / text length
```

---

### StyleTTS2

#### "nltk punkt not found"

**Symptom:** `LookupError: Resource punkt not found`

**Cause:** NLTK data not downloaded.

**Fix:**
```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
```

In Docker, this is handled in the Dockerfile.

---

#### StyleTTS2 Very Slow on CPU

**Symptom:** Synthesis takes 30+ seconds per sentence.

**Cause:** StyleTTS2 is a GPU-oriented model.

**Fix:**
- Use GPU mode: `STYLETTS2_GPU_MODE=docker_gpu`
- Or switch to Kokoro/Piper for CPU-only environments

---

### CosyVoice

#### "CosyVoice model not found"

**Symptom:** Import or initialization error.

**Cause:** CosyVoice must be installed from its GitHub repository.

**Fix:**
```bash
pip install git+https://github.com/FunAudioLLM/CosyVoice.git
```

---

### Dia / Dia2

#### "CUDA is required for Dia"

**Symptom:** Dia health check fails with GPU requirement error.

**Cause:** Dia and Dia2 are very large models that practically require a GPU.

**Fix:**
```bash
# Enable GPU mode
DIA_GPU_MODE=docker_gpu
DIA2_GPU_MODE=docker_gpu

# Or use make docker-gpu-up which sets these automatically
make docker-gpu-up
```

---

#### Dia Out of Memory

**Symptom:** `RuntimeError: CUDA out of memory` with Dia (1.6B) or Dia2 (2B).

**Cause:** Insufficient VRAM. Dia needs 6 GB+, Dia2 needs 8 GB+.

**Fix:**
- Use a GPU with more VRAM
- Close other GPU applications
- Use shorter text inputs
- Switch to a smaller model (Kokoro, Piper) if GPU is limited

---

## 🔊 Audio Issues

### No Audio Output / Playback Fails

**Symptom:** Synthesis succeeds but no audio plays in the browser.

**Cause:** Audio file not served correctly, or browser audio issue.

**Fix:**
1. Check the audio URL in the synthesis response
2. Try accessing the audio URL directly: `http://localhost:8100/api/v1/audio/<filename>`
3. Check browser console for errors
4. Try downloading the file and playing locally
5. Ensure the output directory has the file: `ls storage/output/`

---

### Garbled / Distorted Audio

**Symptom:** Audio plays but sounds robotic, choppy, or distorted.

**Cause:** Sample rate mismatch, encoding issue, or model producing poor output.

**Fix:**
- Try WAV format (lossless) instead of MP3/OGG
- Ensure the text is in the language the voice model supports
- Check if the provider is healthy
- Try a different voice or provider

---

### Audio File Too Large

**Symptom:** Generated audio files are very large.

**Cause:** WAV format is uncompressed.

**Fix:**
- Switch to MP3 or OGG format in Settings or per-request
- Use the `output_format` parameter in API requests:
  ```json
  { "output_format": "mp3" }
  ```

---

### Upload Rejected: "Unsupported format"

**Symptom:** `HTTP 400: Unsupported format 'xyz'. Allowed: flac, m4a, mp3, ogg, wav`

**Cause:** Uploaded file has an unsupported extension.

**Fix:** Convert your audio to one of the supported formats:
```bash
ffmpeg -i input.webm output.wav
```

---

### Upload Rejected: "Exceeds 50MB limit"

**Symptom:** `HTTP 413: File exceeds 50MB limit`

**Cause:** Audio file is too large.

**Fix:**
- Compress the audio: `ffmpeg -i input.wav -b:a 128k output.mp3`
- Split long recordings into shorter files
- Use a lower sample rate if appropriate

---

## 🗄️ Database Issues

### "Table not found" / "no such table"

**Symptom:** `sqlalchemy.exc.OperationalError: no such table: voice_profiles`

**Cause:** Database tables were not created.

**Fix:**
```bash
# Run migrations
make migrate

# Or reset the database (development only)
rm atlas_vox.db
# Restart the backend — tables are created automatically on startup
```

---

### Migration Fails: "Target database is not up to date"

**Symptom:** `alembic.util.exc.CommandError: Target database is not up to date`

**Cause:** Migration history is out of sync.

**Fix:**
```bash
# Stamp the current state
cd backend
alembic stamp head

# Then retry
alembic upgrade head
```

---

### Database Locked (SQLite)

**Symptom:** `sqlite3.OperationalError: database is locked`

**Cause:** Multiple processes writing to SQLite simultaneously.

**Fix:**
- Ensure only one backend process runs at a time with SQLite
- For concurrent access, switch to PostgreSQL:
  ```bash
  DATABASE_URL=postgresql+asyncpg://user:pass@localhost/atlas_vox
  ```

---

## 🌐 Network Issues

### CORS Error in Browser Console

**Symptom:** `Access to fetch at 'http://localhost:8100/api/v1/...' from origin 'http://localhost:3000' has been blocked by CORS policy`

**Cause:** The frontend origin is not in the CORS allowed list.

**Fix:**
```bash
# Add your frontend URL to CORS origins
CORS_ORIGINS='["http://localhost:3000","http://localhost:3100","http://your-domain.com"]'
```

---

### Container Cannot Reach Internet

**Symptom:** Cloud providers (ElevenLabs, Azure) fail with connection errors inside Docker.

**Cause:** Docker network or DNS issue.

**Fix:**
```bash
# Test DNS from inside the container
docker compose -f docker/docker-compose.yml exec backend python -c "import socket; print(socket.getaddrinfo('api.elevenlabs.io', 443))"

# If DNS fails, configure Docker DNS
# In /etc/docker/daemon.json:
# { "dns": ["8.8.8.8", "8.8.4.4"] }
# Then restart Docker
```

---

### WebSocket Connection Fails

**Symptom:** Training progress does not update in real-time.

**Cause:** WebSocket connection blocked by proxy or firewall.

**Fix:**
- If behind a reverse proxy (nginx), add WebSocket support:
  ```nginx
  location /api/v1/training/jobs/ {
      proxy_pass http://backend:8100;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
  }
  ```
- Check browser console for WebSocket errors

---

## 📚 Training Issues

### Training Stuck at "queued"

**Symptom:** Training job stays in "queued" status indefinitely.

**Cause:** Celery worker is not running or not connected to Redis.

**Fix:**
```bash
# Docker: Check worker logs
docker compose -f docker/docker-compose.yml logs worker

# Local: Start a Celery worker
cd backend
celery -A app.tasks.celery_app worker --loglevel=info --queues=default,preprocessing,training

# Verify Redis is accessible
redis-cli ping  # Should return PONG
```

---

### Training Fails Immediately

**Symptom:** Training job moves to "failed" within seconds.

**Cause:** No audio samples uploaded, or provider does not support training.

**Fix:**
1. Upload audio samples first (Training Studio > Upload)
2. Run preprocessing (Training Studio > Preprocess)
3. Verify the profile's provider supports cloning/fine-tuning
4. Check the error message in the training job details

---

### Training Fails: "No preprocessed samples"

**Symptom:** Training fails with "No preprocessed samples found".

**Cause:** Preprocessing was not run, or preprocessing failed.

**Fix:**
1. Go to Training Studio
2. Click **Preprocess** before starting training
3. Wait for preprocessing to complete
4. Then click **Start Training**

---

## ⚡ Performance Issues

### Health Checks Are Slow

**Symptom:** Provider health checks take 10+ seconds.

**Cause:** Local models loading into memory on first check.

**Fix:**
- First health check is slow (model loading). Subsequent checks are faster.
- For Docker, increase container memory limit if models are being evicted
- Run health checks at startup to "warm up" models

---

### High Memory Usage

**Symptom:** Backend container uses 4+ GB RAM.

**Cause:** Multiple TTS models loaded simultaneously.

**Fix:**
- Disable providers you are not using
- Use the provider config page to disable unused providers
- Each local GPU model uses 1-4 GB of VRAM

---

### Slow Synthesis

**Symptom:** Text-to-speech takes 10+ seconds.

**Cause:** Using GPU-oriented models on CPU, or large text inputs.

**Fix:**
- Use GPU mode for large models (Coqui XTTS, StyleTTS2, CosyVoice, Dia)
- Use Kokoro or Piper for fast CPU synthesis
- Split long text into shorter chunks
- Use streaming for lower time-to-first-audio

---

## 🖥️ Frontend Issues

### Page Shows "Loading..." Indefinitely

**Symptom:** A page shows the loading spinner forever.

**Cause:** Backend API is not reachable.

**Fix:**
1. Check that the backend is running: `curl http://localhost:8100/api/v1/health`
2. Check browser console for network errors
3. Verify the frontend is configured to proxy to the correct backend URL
4. In Docker, ensure the `backend` service is healthy

---

### Dark Mode Not Persisting

**Symptom:** Theme resets to light mode on page refresh.

**Cause:** Local storage access issue (incognito mode or storage full).

**Fix:**
- Try in a normal (non-incognito) browser window
- Clear site data and try again
- Check that localStorage is not disabled

---

### Provider Logos Not Showing

**Symptom:** Provider cards show placeholder instead of logos.

**Cause:** This is expected — logos use a text-based fallback component.

---

## 🚦 Rate Limiting & Configuration Issues

### Rate Limiting (429 Too Many Requests)

**Symptom:** API returns 429 status code.

**Cause:** Rate limits protect expensive endpoints: synthesis (10/min), training (5/min), compare (5/min), OpenAI-compat (20/min), default (60/min).

**Fix:** Wait 60 seconds. For programmatic use, add retry logic with exponential backoff. Rate limits are per-IP.

---

### Redis Database Configuration

**Symptom:** Redis key collision with ATLAS or other services.

**Cause:** Atlas Vox defaults to Redis database 1. If another service uses db1, conflicts may occur.

**Fix:** Change `REDIS_URL` in `.env` to use a different database number:
```bash
REDIS_URL=redis://localhost:6379/2
```

---

## 🆘 Still Need Help?

If your issue is not covered here:

1. **Check the backend logs:**
   ```bash
   docker compose -f docker/docker-compose.yml logs backend --tail=100
   ```

2. **Check the worker logs:**
   ```bash
   docker compose -f docker/docker-compose.yml logs worker --tail=100
   ```

3. **Check the Swagger docs** for API error details:
   `http://localhost:8100/docs`

4. **Open an issue** on the [GitHub repository](https://github.com/HouseGarofalo/atlas-vox/issues) with:
   - Steps to reproduce
   - Error message (full text)
   - Backend logs
   - Docker version and OS

---

<div align="center">

[Back to User Guide](USER_GUIDE.md) | [API Reference](API_REFERENCE.md) | [Deployment Guide](DEPLOYMENT.md)

</div>
