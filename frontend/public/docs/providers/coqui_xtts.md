# Coqui XTTS v2

> Local (GPU) — Unlimited via voice cloning (any reference audio)

State-of-the-art voice cloning from just 6 seconds of audio. Supports 17 languages with zero-shot synthesis.

**Website:** [https://github.com/coqui-ai/TTS](https://github.com/coqui-ai/TTS)

## Quality Notes

Excellent cloning quality from short audio. 6 seconds minimum, 15-30 seconds recommended for best results. ~1.5B parameters. GPU strongly recommended.

## Setup Steps

### Step 1: Enable GPU Mode (Recommended)

For usable speed, GPU mode is strongly recommended. CPU mode is 10-50x slower.

```bash
COQUI_XTTS_GPU_MODE=docker_gpu
# Or use: make docker-gpu-up
```

### Step 2: Install NVIDIA Container Toolkit (Docker GPU)

If using Docker GPU mode, install the NVIDIA Container Toolkit for GPU passthrough.

```bash
# Ubuntu/Debian
sudo apt install nvidia-container-toolkit
sudo systemctl restart docker
```

### Step 3: Model Downloads Automatically

The XTTS v2 model (~1.8 GB) downloads on first use. Ensure internet access and sufficient disk space.

### Step 4: Prepare Reference Audio

For voice cloning, upload a clean audio sample (15-30 seconds of clear speech, no background noise) via the Training Studio.

### Step 5: Run Health Check

Go to Providers > Coqui XTTS > Health Check. First check will be slow while the model loads into memory.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| COQUI_XTTS_GPU_MODE | No | host_cpu | GPU mode: host_cpu, docker_gpu, or auto |

## Configuration Checklist

- [ ] TTS Python package installed
- [ ] GPU mode configured (if using GPU)
- [ ] NVIDIA Container Toolkit installed (for Docker GPU)
- [ ] Model downloaded successfully (~1.8 GB)
- [ ] Health check passes

## Tips & Best Practices

- Voice cloning from 6 seconds, but 15-30 seconds gives much better results
- GPU mode is 10-50x faster than CPU
- Supports 17 languages: English, Spanish, French, German, Italian, Portuguese, Polish, Turkish, Russian, Dutch, Czech, Arabic, Chinese, Japanese, Korean, Hungarian, Hindi
- Clean audio without background noise is critical for good cloning
- Minimum 4 GB VRAM required for GPU mode

## Common Issues

### CUDA out of memory

Coqui XTTS needs at least 4 GB VRAM. Close other GPU applications. Use shorter text segments.

### Model download fails

Check internet access from the container. The model is ~1.8 GB. Try increasing Docker timeout.

### Very slow synthesis on CPU

CPU mode is impractical for production. Switch to docker_gpu mode or use Kokoro/Piper instead.

## CLI Example

```bash
atlas-vox synthesize --text "Hello from XTTS" --provider coqui_xtts --profile my-clone
```

## API Example

```bash
curl -X POST http://localhost:8100/api/v1/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from XTTS", "provider_name": "coqui_xtts", "profile_id": "abc-123"}'
```
