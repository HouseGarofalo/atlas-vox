# StyleTTS2

> Local (GPU) — Style transfer from reference audio (unlimited)

Style diffusion and adversarial training for human-level speech quality. Zero-shot voice transfer with the highest MOS scores.

**Website:** [https://github.com/yl4579/StyleTTS2](https://github.com/yl4579/StyleTTS2)

## Quality Notes

Achieves the highest MOS (Mean Opinion Score) of any open-source TTS. English-only. ~200M parameters. Style transfer allows combining voice identity with speaking style.

## Setup Steps

### Step 1: Enable GPU Mode

StyleTTS2 is impractical on CPU. Use GPU mode for any real-time synthesis.

```bash
STYLETTS2_GPU_MODE=docker_gpu
```

### Step 2: Install System Dependencies

espeak-ng and NLTK punkt data are required. Both are installed automatically in Docker.

```bash
sudo apt install espeak-ng
python -c "import nltk; nltk.download('punkt')"
```

### Step 3: Configure GPU Container

Use the GPU Docker Compose configuration for automatic setup.

```bash
make docker-gpu-up
```

### Step 4: Run Health Check

First health check may be slow as the model loads. Subsequent checks are faster. Check the Providers page.

### Step 5: Test Style Transfer

Upload reference audio and synthesize with style transfer to combine the identity of one voice with the style of another.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| STYLETTS2_GPU_MODE | No | host_cpu | GPU mode: host_cpu, docker_gpu, or auto |

## Configuration Checklist

- [ ] styletts2 Python package installed
- [ ] espeak-ng installed
- [ ] NLTK punkt data downloaded
- [ ] GPU mode configured
- [ ] Health check passes

## Tips & Best Practices

- English-only, but achieves the highest quality MOS scores of any open-source model
- Style transfer lets you apply one voice's style to another voice's identity
- CPU mode is very slow -- GPU is strongly recommended
- ~200M parameters, needs ~2 GB VRAM

## Common Issues

### espeak-ng not found

Install with: sudo apt install espeak-ng (Linux) or brew install espeak-ng (macOS).

### NLTK punkt error

Run: python -c "import nltk; nltk.download('punkt')" before starting the backend.

### Extremely slow synthesis

You are likely running on CPU. Switch to STYLETTS2_GPU_MODE=docker_gpu.

## CLI Example

```bash
atlas-vox synthesize --text "Hello from StyleTTS2" --provider styletts2
```

## API Example

```bash
curl -X POST http://localhost:8100/api/v1/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from StyleTTS2", "provider_name": "styletts2"}'
```
