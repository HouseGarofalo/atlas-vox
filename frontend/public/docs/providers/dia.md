# Dia

> Local (GPU) — 2 built-in dialogue speakers ([S1] and [S2])

Nari Labs dialogue TTS with 1.6B parameters. Generates natural multi-speaker conversations with non-verbal sounds.

**Website:** [https://github.com/nari-labs/dia](https://github.com/nari-labs/dia)

## Quality Notes

Excellent for dialogue and podcast generation. Supports non-verbal sounds like (laughs), (sighs), (clears throat). 1.6B parameters, needs 6 GB+ VRAM.

## Setup Steps

### Step 1: Enable GPU Mode

Dia's 1.6B model requires GPU. Minimum 6 GB VRAM. CPU mode is impractical.

```bash
DIA_GPU_MODE=docker_gpu
```

### Step 2: Launch with GPU Compose

Use the GPU Docker Compose configuration.

```bash
make docker-gpu-up
```

### Step 3: Format Dialogue Text

Use [S1] and [S2] tags for speakers. Non-verbal sounds go in parentheses.

```
[S1] Hello, how are you today?
[S2] Great, thanks! (laughs) And you?
[S1] Doing well. (clears throat) Let me tell you something.
```

### Step 4: Wait for Model Download

Model downloads on first use (~3 GB). Health check will be slow initially.

### Step 5: Test Dialogue Synthesis

Run a test with dialogue-formatted text. The output will contain two distinct speakers.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| DIA_GPU_MODE | No | host_cpu | GPU mode: host_cpu, docker_gpu, or auto |

## Configuration Checklist

- [ ] GPU with 6 GB+ VRAM available
- [ ] GPU mode configured
- [ ] Model downloaded successfully (~3 GB)
- [ ] Health check passes
- [ ] Dialogue synthesis produces two distinct speakers

## Tips & Best Practices

- Use [S1] and [S2] tags for different speakers
- Supports non-verbal sounds: (laughs), (sighs), (clears throat), (gasps)
- Great for podcast and conversation generation
- CPU mode is impractical for this model size
- Best results with natural, conversational text

## Common Issues

### CUDA out of memory

Dia needs 6 GB+ VRAM. Close other GPU applications. Reduce dialogue length.

### Only one speaker in output

Ensure you are using [S1] and [S2] tags at the start of each line. The tags are case-sensitive.

### Non-verbal sounds not working

Use parentheses with no spaces before: (laughs), not ( laughs ). Only supported sounds work.

## CLI Example

```bash
atlas-vox synthesize --text "[S1] Hello! [S2] Hi there! (laughs)" --provider dia
```

## API Example

```bash
curl -X POST http://localhost:8100/api/v1/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "[S1] Hello! [S2] Hi there!", "provider_name": "dia"}'
```
