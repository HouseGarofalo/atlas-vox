# Piper

> Local (CPU) — 100+ downloadable voice models across 30+ languages

Fast, local TTS optimized for Raspberry Pi and Home Assistant. ONNX-based with many pre-trained voices across 30+ languages.

**Website:** [https://github.com/rhasspy/piper](https://github.com/rhasspy/piper)

## Quality Notes

Medium quality VITS models. Very fast inference, even on Raspberry Pi. Best for home automation and IoT. Low memory footprint.

## Setup Steps

### Step 1: Default Model Downloaded Automatically

The Docker build downloads en_US-lessac-medium.onnx automatically. For local dev, you may need to download it manually.

```bash
mkdir -p storage/models/piper
cd storage/models/piper
# Download from https://huggingface.co/rhasspy/piper-voices
```

### Step 2: Install espeak-ng

Piper requires espeak-ng for phoneme generation. This is installed automatically in Docker.

```bash
# Ubuntu/Debian
sudo apt install espeak-ng

# macOS
brew install espeak-ng
```

### Step 3: Add More Voices (Optional)

Download additional ONNX models from the Piper Voices repository and place them in the model directory.

```bash
# Each voice needs two files:
# <name>.onnx       -- the model weights
# <name>.onnx.json  -- the config file

# Example: download German voice
wget https://huggingface.co/rhasspy/piper-voices/.../de_DE-thorsten-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/.../de_DE-thorsten-medium.onnx.json
```

### Step 4: Configure Model Path

Set the PIPER_MODEL_PATH if you use a non-default location for model files.

```bash
PIPER_MODEL_PATH=./storage/models/piper
```

### Step 5: Verify Setup

Run a health check on the Providers page. Piper should show healthy if at least one model file is present.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| PIPER_ENABLED | No | true | Enable or disable Piper |
| PIPER_MODEL_PATH | No | ./storage/models/piper | Path to ONNX model files |

## Configuration Checklist

- [ ] ONNX model files present in model directory
- [ ] espeak-ng installed on the system
- [ ] Piper health check passes
- [ ] At least one voice appears in the Voice Library
- [ ] Can synthesize and play audio

## Tips & Best Practices

- Use medium quality models for the best speed/quality balance
- Piper supports 30+ languages -- download models for each language you need
- Very low memory footprint, works on Raspberry Pi 4
- Home Assistant compatible voice format
- Fastest inference of all local providers

## Common Issues

### espeak-ng not found error

Install espeak-ng: sudo apt install espeak-ng (Linux) or brew install espeak-ng (macOS).

### No model files found

Download at least one .onnx + .onnx.json pair from https://huggingface.co/rhasspy/piper-voices and place in the PIPER_MODEL_PATH directory.

### Model loading error

Ensure both the .onnx and .onnx.json files are present. They must have the same base filename.

## CLI Example

```bash
atlas-vox synthesize --text "Hello from Piper" --provider piper
```

## API Example

```bash
curl -X POST http://localhost:8100/api/v1/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from Piper", "provider_name": "piper"}'
```
