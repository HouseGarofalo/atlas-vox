# Kokoro

> Local (CPU) — 54 built-in voices

Lightweight, fast TTS with 54 built-in voices. CPU-only, no GPU required. Default provider in Atlas Vox.

**Website:** [https://github.com/hexgrad/kokoro](https://github.com/hexgrad/kokoro)

## Quality Notes

Good quality for an 82M parameter model. Best for English. Fastest CPU provider with sub-100ms latency on modern hardware.

## Setup Steps

### Step 1: No Setup Required

Kokoro works out of the box with no configuration. It is the default provider and is automatically enabled when the backend starts.

### Step 2: Verify Installation

Confirm the kokoro Python package is installed in your environment. Docker handles this automatically.

```bash
pip show kokoro   # Should show version 0.x.x
```

### Step 3: Check Provider Health

Go to the Providers page and check that Kokoro shows a green "healthy" badge. You can also verify via CLI.

```bash
atlas-vox providers list
atlas-vox providers health kokoro
```

### Step 4: Browse Available Voices

Kokoro includes 54 built-in voices organized by accent and gender. Prefixes: af_ (American female), am_ (American male), bf_ (British female), bm_ (British male).

```bash
atlas-vox synthesize --provider kokoro --voice af_heart --text "Hello world"
```

### Step 5: Test Synthesis

Run a quick synthesis to verify audio output quality. Try different voices to find your preferred one.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| KOKORO_ENABLED | No | true | Enable or disable Kokoro provider |

## Configuration Checklist

- [ ] Backend is running
- [ ] kokoro Python package installed
- [ ] Kokoro health check passes
- [ ] Can list Kokoro voices in Voice Library
- [ ] Can synthesize speech with a Kokoro voice

## Tips & Best Practices

- Kokoro is the fastest CPU provider -- ideal for testing and prototyping
- Keep text under 500 characters per request for best quality
- 82M parameter model uses minimal RAM (~200 MB)
- Use af_heart for a warm, natural-sounding female voice
- Supports speed adjustment from 0.5x to 2.0x

## Common Issues

### Health check shows unhealthy

Ensure the kokoro package is installed: pip install kokoro. Check logs for import errors.

### No voices appear in Voice Library

Verify the provider is enabled (KOKORO_ENABLED=true). Try restarting the backend.

### Audio sounds robotic or choppy

Keep text under 500 characters. Try a different voice (af_heart is recommended). Ensure sample rate is 24000.

## CLI Example

```bash
atlas-vox synthesize --text "Hello from Kokoro" --provider kokoro --voice af_heart
```

## API Example

```bash
curl -X POST http://localhost:8100/api/v1/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from Kokoro", "provider_name": "kokoro", "voice_id": "af_heart"}'
```
