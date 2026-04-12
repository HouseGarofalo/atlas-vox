# Dia2

> Local (GPU) — 2 built-in dialogue speakers ([S1] and [S2])

Next-gen dialogue model with 2B parameters and streaming support. Real-time conversation generation with improved quality.

**Website:** [https://github.com/nari-labs/dia](https://github.com/nari-labs/dia)

## Quality Notes

Higher quality than Dia with streaming support. 2B parameters produce more natural speech. Needs 8 GB+ VRAM.

## Setup Steps

### Step 1: Enable GPU Mode

Dia2's 2B model requires GPU. Minimum 8 GB VRAM.

```bash
DIA2_GPU_MODE=docker_gpu
```

### Step 2: Launch with GPU Compose

Use the GPU Docker Compose configuration.

```bash
make docker-gpu-up
```

### Step 3: Wait for Model Download

The 2B parameter model is approximately 4 GB. Ensure sufficient disk space and internet access.

### Step 4: Test Streaming Output

Dia2's primary advantage over Dia is streaming. Test with the Synthesis Lab to hear audio as it generates.

### Step 5: Verify Health

First health check will be slow while the model loads. Subsequent checks are faster.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| DIA2_GPU_MODE | No | host_cpu | GPU mode: host_cpu, docker_gpu, or auto |

## Configuration Checklist

- [ ] GPU with 8 GB+ VRAM available
- [ ] GPU mode configured
- [ ] Model downloaded (~4 GB)
- [ ] Health check passes
- [ ] Streaming synthesis works

## Tips & Best Practices

- Primary advantage over Dia: streaming support for real-time output
- 2B parameters produce higher quality than Dia's 1.6B
- CPU mode is not practical for this model
- Uses same [S1]/[S2] dialogue format as Dia

## Common Issues

### CUDA out of memory

Dia2 needs 8 GB+ VRAM. This is the most VRAM-hungry provider. Close all other GPU apps.

### Model download timeout

The 4 GB model download can take a while. Ensure stable internet. Check Docker logs for progress.

### Streaming not working

Verify WebSocket connection is established. Check browser console for connection errors.

## CLI Example

```bash
atlas-vox synthesize --text "[S1] Hello! [S2] Hi!" --provider dia2
```

## API Example

```bash
curl -X POST http://localhost:8100/api/v1/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "[S1] Hello! [S2] Hi!", "provider_name": "dia2"}'
```
