# ElevenLabs

> Cloud API — Thousands of voices, plus custom voice cloning

Industry-leading cloud TTS with the most natural-sounding voices. Supports instant voice cloning and 29 languages.

**Website:** [https://elevenlabs.io](https://elevenlabs.io)

## Quality Notes

Best-in-class quality. The most natural-sounding provider available. Supports voice cloning from 1-5 minutes of audio. Multilingual v2 model supports 29 languages.

## Setup Steps

### Step 1: Create an ElevenLabs Account

Sign up at elevenlabs.io. A free tier with 10,000 characters/month is available. No credit card required.

### Step 2: Get Your API Key

Go to Profile Settings > API Keys and copy your key. Keep this key secure -- it provides full access to your account.

### Step 3: Configure in Atlas Vox

Set the API key via environment variable or the Providers settings page in the Web UI.

```bash
# Via environment variable
ELEVENLABS_API_KEY=sk_xxxxxxxxxxxxxxxx

# Or via Web UI:
# Providers > ElevenLabs > Settings > API Key
```

### Step 4: Run Health Check

Click the Health Check button on the Providers page. If the API key is valid, the status should change to healthy.

### Step 5: Test Synthesis

Click Test to run a quick synthesis and verify audio output. Try the Rachel voice for a high-quality demo.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| ELEVENLABS_API_KEY | Yes | | Your ElevenLabs API key (starts with sk_) |
| ELEVENLABS_MODEL_ID | No | eleven_multilingual_v2 | TTS model ID |

## Configuration Checklist

- [ ] ElevenLabs account created
- [ ] API key configured in provider settings
- [ ] Health check passes (status: healthy)
- [ ] Test synthesis produces audio
- [ ] Voices appear in Voice Library

## Tips & Best Practices

- Free tier: 10,000 characters/month, 3 custom voices
- eleven_multilingual_v2 supports all 29 languages
- Use eleven_monolingual_v1 for faster English-only synthesis
- Voice cloning works best with 1-5 minutes of clean audio
- Rachel and Adam are the most popular default voices

## Common Issues

### 401 Unauthorized error

Verify your API key is correct. Go to elevenlabs.io > Profile Settings > API Keys and copy a fresh key.

### 429 Rate limit exceeded

Free tier has rate limits. Wait 60 seconds and try again, or upgrade your plan.

### No voices returned

Check that ELEVENLABS_API_KEY is set correctly. The provider needs a valid key to fetch the voice list.

## CLI Example

```bash
atlas-vox synthesize --text "Hello from ElevenLabs" --provider elevenlabs --voice Rachel
```

## API Example

```bash
curl -X POST http://localhost:8100/api/v1/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from ElevenLabs", "provider_name": "elevenlabs", "voice_id": "Rachel"}'
```
