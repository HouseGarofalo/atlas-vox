# CosyVoice

> Local (GPU) — Built-in voices + voice cloning

Alibaba's multilingual TTS with natural prosody. Supports 9 languages with ~150ms streaming latency on GPU.

**Website:** [https://github.com/FunAudioLLM/CosyVoice](https://github.com/FunAudioLLM/CosyVoice)

## Quality Notes

Excellent multilingual quality. Handles code-switching between languages naturally. ~300M parameters. ~150ms first-chunk latency in streaming mode on GPU.

## Setup Steps

### Step 1: Enable GPU Mode

GPU mode is recommended for acceptable performance.

```bash
COSYVOICE_GPU_MODE=docker_gpu
```

### Step 2: Docker Installation

CosyVoice is installed from its GitHub repository during Docker build. No manual installation needed.

```bash
make docker-gpu-up
```

### Step 3: Verify Model Download

The CosyVoice model downloads on first use. Monitor Docker logs for download progress.

```bash
docker compose -f docker/docker-compose.yml logs -f worker
```

### Step 4: Run Health Check

Verify the provider is operational via the Providers page.

### Step 5: Test Multilingual Synthesis

Try synthesizing in different languages. CosyVoice excels at Chinese, Japanese, Korean, and natural code-switching.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| COSYVOICE_GPU_MODE | No | host_cpu | GPU mode: host_cpu, docker_gpu, or auto |

## Configuration Checklist

- [ ] CosyVoice package installed
- [ ] GPU mode configured
- [ ] Model downloaded
- [ ] Health check passes
- [ ] Multilingual synthesis works

## Tips & Best Practices

- Excellent for Chinese and Asian language TTS
- ~150ms first-chunk latency in streaming mode on GPU
- Handles code-switching between languages naturally
- 300M parameters, needs ~3 GB VRAM

## Common Issues

### Import error for CosyVoice

CosyVoice must be installed from GitHub. Use Docker for automatic installation.

### Slow first synthesis

First synthesis triggers model download (~2 GB). Subsequent calls are fast.

## CLI Example

```bash
atlas-vox synthesize --text "Hello from CosyVoice" --provider cosyvoice
```

## API Example

```bash
curl -X POST http://localhost:8100/api/v1/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from CosyVoice", "provider_name": "cosyvoice"}'
```
