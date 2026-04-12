# Step-by-Step Walkthroughs

7 tutorials covering common workflows from first synthesis to advanced configuration.

---

## 1. First Synthesis

Generate your first TTS audio in under a minute.

1. Open the Synthesis Lab from the sidebar.
2. Select the default Kokoro provider profile (pre-configured).
3. Type or paste text into the input area (up to 5000 characters).
4. Click 'Synthesize' and wait for the waveform to appear.
5. Click the play button to listen, or click the download icon to save the WAV file.

---

## 2. Voice Cloning with Coqui XTTS

Clone a voice from a short audio sample.

1. Navigate to Providers and ensure Coqui XTTS shows a green health badge. Enable GPU mode for best quality.
2. Go to Voice Profiles and click 'New Profile'. Select Coqui XTTS as the provider.
3. On the profile page, open the Samples tab and upload 1-3 audio clips (6+ seconds each, clean speech, minimal background noise).
4. Click 'Preprocess' to normalize audio levels and trim silence.
5. Click 'Start Training' and monitor the progress bar. Training takes 5-15 minutes on GPU.
6. Once status changes to 'ready', go to the Synthesis Lab and select your new profile to synthesize with your cloned voice.

---

## 3. Comparing Voices

A/B test multiple voices with the same text.

1. Open the Comparison page from the sidebar.
2. Select 2-5 voice profiles from the multi-select dropdown.
3. Enter the text you want to compare (the same text is synthesized by each profile).
4. Click 'Compare' and review the side-by-side results. Each card shows the waveform, latency, and a play button.

---

## 4. Azure Speech Setup

Configure the Azure AI Speech cloud provider.

1. In the Azure Portal, create a 'Speech' resource (Cognitive Services). Choose a supported region (e.g., eastus).
2. After deployment, go to Keys and Endpoint. Copy Key 1 and the Region name.
3. In Atlas Vox, go to Providers > Azure Speech > Settings.
4. Paste the API key into the 'API Key' field and enter the region (e.g., eastus) in the 'Region' field. Click Save.
5. Click 'Health Check' -- it should turn green. Azure Speech supports SSML, neural voices, and multiple languages.

---

## 5. ElevenLabs Setup

Configure the ElevenLabs cloud provider.

1. Sign up at elevenlabs.io and navigate to your Profile Settings page.
2. Copy your API key from the API Keys section.
3. In Atlas Vox, go to Providers > ElevenLabs > Settings. Paste your API key and click Save.
4. Run a Health Check to verify. ElevenLabs offers a free tier with limited characters per month.

---

## 6. OpenAI-Compatible API Usage

Use Atlas Vox as a drop-in replacement for the OpenAI TTS API.

1. Atlas Vox exposes an OpenAI-compatible endpoint at `/v1/audio/speech`.

2. Use any OpenAI TTS client library by pointing it to your Atlas Vox server:

```bash
curl http://localhost:8100/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model": "kokoro", "input": "Hello from Atlas Vox!", "voice": "af_heart"}' \
  --output speech.wav
```

3. The 'model' field maps to a provider name, and 'voice' maps to a voice ID from that provider. Supported response_format values: wav, mp3, opus, flac.

---

## 7. Design Customization

Personalize the Atlas Vox interface with the Design System.

1. Open the Design System page from the sidebar (palette icon).
2. Start with a preset: click one of the 8 theme cards (Blue, Emerald, Violet, Sunset, Rose, Mono, Minimal, Spacious Serif).
3. Fine-tune individual tokens using the sliders and dropdowns: accent color hue/saturation, font family, density, card style, border radius, and more.
4. All changes apply instantly and persist across browser sessions. Click 'Reset to Defaults' to return to the Blue preset.
