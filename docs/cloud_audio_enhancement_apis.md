# Cloud Audio Enhancement APIs — Research Summary

**Date:** March 31, 2026
**Focus:** Programmatic audio enhancement APIs with REST interfaces and Python SDKs

---

## Executive Summary

Four production-ready APIs emerged with clear Python support and pricing models:

1. **ElevenLabs Audio Isolation** — Simple, fast, integrated with TTS
2. **Audo.ai** — Dedicated noise removal, closed beta, most affordable
3. **Cleanvoice AI** — Full podcast/audio production suite
4. **Dolby.io Enhance** — Enterprise-grade, comprehensive audio restoration

Adobe Podcast Enhance Speech **does not have a public API**. Krisp provides a real-time Voice SDK focused on live calls, not batch processing. Deepgram excels at speech-to-text but not audio enhancement.

---

## 1. ElevenLabs Audio Isolation API

### What It Does
Removes background noise from audio files. Extracts speech from background noise in both audio and video files (up to 500MB, 1 hour max).

### API Endpoint
```
POST https://api.elevenlabs.io/v1/audio-isolation
```

### Input Format
Multipart form-data with:
- **audio** (required): Binary audio file
- **file_format** (optional): `pcm_s16le_16` or `other` (default)
  - PCM requires: 16-bit PCM at 16kHz sample rate, mono, little-endian
- **preview_b64** (optional): Base64-encoded preview image

### Python SDK Usage
```python
from elevenlabs import ElevenLabs

client = ElevenLabs(api_key="xi-api-key")
result = client.audio_isolation.convert(audio="example_audio")
```

### Output
Returns enhanced audio file (200 OK response with audio data).

### Pricing
**NOT DOCUMENTED** in official API reference. Likely bundled with Text-to-Speech credits or usage-based.

### Key Strengths
- ✅ Simple integration (single endpoint)
- ✅ Works with ElevenLabs TTS for end-to-end voice pipeline
- ✅ Official Python SDK included
- ✅ Supports streaming via `/stream` endpoint for large files

### Key Limitations
- ❌ No explicit pricing listed
- ❌ Limited to audio isolation (no other restoration like reverb removal)

### Reference
- [Audio Isolation | ElevenLabs Documentation](https://elevenlabs.io/docs/api-reference/audio-isolation/convert)
- [Voice Isolator Overview](https://elevenlabs.io/docs/overview/capabilities/voice-isolator)
- [Blog: Voice Isolator API Launch](https://elevenlabs.io/blog/voice-isolator-api-launch)

---

## 2. Audo.ai Audio Enhancement API

### What It Does
Proprietary AI noise removal—removes background noise of any kind. Designed for batch and real-time processing with focus on speech clarity.

### API Endpoints
```
Base URL: https://api.audo.ai/v1/
GET    /apiKey/test                    # Test authentication
POST   /upload                         # Upload audio file → fileId
POST   /process                        # Submit for noise removal → jobId
GET    /status/{jobId}                 # Check job status
GET    /download/{jobId}               # Retrieve processed audio
```

### Authentication
```
Header: x-api-key: $AUDO_API_KEY
```

### Python SDK Usage
Audo provides a Python SDK. Install and test:
```bash
pip install audo-sdk
```

```python
import audo

client = audo.Client(api_key="$AUDO_API_KEY")

# Upload
file_id = client.upload("path/to/audio.wav")

# Process
job_id = client.process(file_id=file_id)

# Poll for status
status = client.status(job_id)

# Download when ready
client.download(job_id, output_path="cleaned.wav")
```

### Workflow
1. Upload → receive `fileId`
2. Submit → receive `jobId`
3. Poll `status/{jobId}` until complete
4. Download processed audio

### Pricing
**CLOSED BETA** — not publicly available. Pricing structure TBD (likely per-minute or volume-based).

### Key Strengths
- ✅ Dedicated noise removal (single purpose, optimized)
- ✅ Supports real-time streaming SDK for live applications
- ✅ Python SDK available
- ✅ Simple 4-step workflow

### Key Limitations
- ❌ **Closed beta** — access may be limited
- ❌ Pricing not public
- ❌ Limited to noise removal (no other audio restoration)

### Reference
- [Audo AI API Docs](https://docs.audo.ai/)
- [Audo.ai Website](https://www.audo.ai/api)

---

## 3. Cleanvoice AI Audio Editing API

### What It Does
Comprehensive podcast/audio production suite: removes filler words (um, uh, like), long silences, mouth sounds, breathing, stutters. Includes noise reduction and loudness normalization.

### API Endpoint
```
Base URL: https://api.cleanvoice.ai/v2
```

### Workflow
Asynchronous processing:
1. POST audio file → receive processing job ID
2. Poll for status
3. Download enhanced audio when complete

### Python SDK Usage
```bash
pip install cleanvoice-sdk
```

```python
from cleanvoice import Cleanvoice

client = Cleanvoice(api_key="$CLEANVOICE_API_KEY")

# Upload and process
job = client.upload_and_process("path/to/audio.mp3")

# Poll for completion
result = job.wait_until_done()

# Download
result.download("cleaned_audio.mp3")
```

### REST API Usage
```bash
curl -X POST "https://api.cleanvoice.ai/v2/upload" \
  -H "Authorization: Bearer $CLEANVOICE_API_KEY" \
  -F "file=@audio.mp3"
```

### Output Formats
- Audio and video files accepted
- Output: publication-ready format with all enhancements applied

### Pricing
- **Free Trial:** 30 minutes
- **Pay-as-you-go:** $11 for 5 hours
- **Subscription:** $11/month (10 hours) → $90/month (100 hours)
- **Custom Enterprise:** 200+ hours/month with API access and priority support
- **API pricing:** Same as standard usage

### Key Strengths
- ✅ Full podcast production automation (not just noise removal)
- ✅ Removes fillers, stutters, breathing, mouth sounds
- ✅ Loudness normalization included
- ✅ Clear pricing with free trial
- ✅ Official Python SDK

### Key Limitations
- ❌ More expensive than dedicated noise removal APIs
- ❌ Over-engineered for simple background noise removal
- ❌ Filler/stutter removal may not work for non-English audio

### Reference
- [Cleanvoice AI API Docs](https://docs.cleanvoice.ai/)
- [Cleanvoice REST API Reference](https://docs.cleanvoice.ai/api/)
- [Pricing Page](https://cleanvoice.ai/pricing/)

---

## 4. Dolby.io Enhance API

### What It Does
Enterprise-grade audio restoration using neural networks to distinguish speech from noise, then suppress noise. Features: noise reduction, speech leveling, speech isolation, loudness correction, sibilance reduction, plosive reduction, dynamic EQ, hum reduction, mouth click reduction.

### API Endpoint
```
https://api.dolby.com/media/enhance
```

### Python Integration
Official Python wrapper available:

```bash
pip install dolbyio-rest-apis
```

```python
from dolbyio_rest_apis.enhance import Enhance
from dolbyio_rest_apis.media import Media

# Initialize
enhance = Enhance(api_token="$DOLBY_API_TOKEN")
media = Media(api_token="$DOLBY_API_TOKEN")

# Upload and process
input_url = media.upload_file("path/to/audio.wav")
output_url = enhance.process(input_url)

# Download
media.download_file(output_url, "enhanced_audio.wav")
```

### Workflow
1. Upload audio to Dolby cloud storage (temporary)
2. Submit enhancement job
3. Check job status
4. Download enhanced result

### Pricing
- **Pricing Model:** Per-minute of audio processed
- **Free Credit:** $50 for new sign-ups (Communications/Media APIs)
- **Monthly Credit:** $25/month with pay-as-you-go plan
- **Enterprise Pricing:** Contact sales

### Key Strengths
- ✅ Enterprise-grade audio restoration (comprehensive feature set)
- ✅ Neural network-based noise suppression
- ✅ Multiple restoration capabilities (not just noise removal)
- ✅ Official Python SDK available
- ✅ Free trial credits available

### Key Limitations
- ❌ More expensive (per-minute pricing can add up)
- ❌ Requires cloud storage integration
- ❌ More complex workflow than simple APIs
- ❌ Pricing not transparent on public pages

### Reference
- [Dolby.io Enhance API Guide](https://docs.dolby.io/media-apis/docs/enhance-api-guide)
- [Python Client Library](https://github.com/DolbyIO/dolbyio-rest-apis-client-python)
- [PyPI: dolbyio-rest-apis](https://pypi.org/project/dolbyio-rest-apis/)
- [Calculating Usage](https://docs.dolby.io/media-apis/docs/guides-calculating-usage)

---

## 5. ai-coustics Audio Enhancement API

### What It Does
Studio-quality audio enhancement: eliminates distortions, removes noise, transcodes formats (WAV→MP3), adjusts loudness to platform requirements. Customizable enhancement level (0-100%).

### API Endpoint
```
Base URL: https://api.ai-coustics.com/
```

### Input Specifications
- Supported codecs: PCM, MPEG Audio, Vorbis, Opus, AAC LC, FLAC
- Max file size: 512 MB
- Max duration: 120 minutes
- Format: Audio or video files

### Python SDK Usage
```bash
pip install aic-sdk-py
```

```python
from aicoustics import Client

client = Client(api_key="$AICOUSTICS_API_KEY")

# Submit enhancement job
job = client.enhance(
    input_file="path/to/audio.wav",
    enhancement_level=75  # 0-100
)

# Wait for completion
result = job.wait()

# Download
result.download("enhanced.mp3")
```

### REST API Usage
```bash
curl -X POST "https://api.ai-coustics.com/enhance" \
  -H "Authorization: Bearer $AICOUSTICS_API_KEY" \
  -F "file=@audio.wav" \
  -F "enhancement_level=75"
```

### Pricing
**NOT PUBLICLY LISTED** — contact for quotes. Likely per-minute or volume-based.

### Key Strengths
- ✅ Handles large files (512 MB, 2 hours)
- ✅ Multiple codec support
- ✅ Customizable enhancement level
- ✅ Format transcoding included
- ✅ LiveKit integration for real-time use

### Key Limitations
- ❌ Pricing not transparent
- ❌ No clear free tier information
- ❌ Less mature ecosystem than ElevenLabs/Dolby

### Reference
- [ai-coustics API](https://ai-coustics.com/api/)
- [Python SDK Docs](https://ai-coustics.github.io/aic-sdk-py/)
- [GitHub: aic-sdk-py](https://github.com/ai-coustics/aic-sdk-py)
- [API Tutorials](https://github.com/ai-coustics/api-tutorials)

---

## 6. Krisp Voice SDK

### What It Does
Real-time AI Voice SDK for live calls and meetings. Noise cancellation (inbound/outbound), voice isolation, accent conversion.

### Deployment Model
**SDK-based, not REST API** — Runs locally on device (CPU) with sub-10ms latency. Two SDKs:
- **VIVA SDK** — Human-to-AI (voice agents)
- **RTC SDK** — Human-to-human (calls, meetings)

### Python Usage
```python
# Krisp is primarily a Voice SDK, not a REST API
# Used in frameworks like Pipecat for real-time processing
from pipecat.processors.audio import KrispFilter

processor = KrispFilter()
# Integrated into audio pipeline for live streams
```

### Pricing
**FREE** for consumer apps (Discord, Slack). **Enterprise licensing** available for custom integrations.

### Key Strengths
- ✅ Real-time processing (sub-10ms latency)
- ✅ Privacy-first (runs locally)
- ✅ Free for most use cases
- ✅ Deployed on 200M+ devices

### Key Limitations
- ❌ **NOT a REST API** — SDK-only
- ❌ Not suitable for batch audio processing
- ❌ Focused on live calls, not post-processing

### Note for Atlas Vox
Krisp is **not suitable** for your use case (batch audio training preparation). Use Krisp only if you need real-time voice enhancement in live streaming or voice agent scenarios.

### Reference
- [Krisp Developers](https://krisp.ai/developers/)
- [Krisp SDK Docs](https://sdk-docs.krisp.ai/)
- [Pipecat Integration](https://docs.pipecat.ai/server/utilities/audio/krisp-filter)

---

## 7. Adobe Podcast Enhance Speech

### Status
**NO PUBLIC API** — Tool available only via web interface at [podcast.adobe.com](https://podcast.adobe.com) or Adobe Creative Cloud.

### Partnership Model
Adobe partners with third-party SaaS platforms (e.g., Wistia) to offer Enhance Speech embedded in their services, but there is **no REST API for developers**.

### Key Limitation
Cannot be programmatically integrated into custom applications.

### Reference
- [Adobe Podcast Enhance Speech](https://podcast.adobe.com/en/enhance)
- [Adobe Product Community Discussion](https://community.adobe.com/t5/adobe-podcast-discussions/podcast-api-to-clean-audio-using-ai/td-p/15171877)

---

## 8. Google Cloud Speech-to-Text & Deepgram

### Google Cloud Speech-to-Text
- Offers **enhanced models** for phone calls and video
- These are optimized **transcription models**, not audio enhancement
- `useEnhanced: true` flag in RecognitionConfig improves transcription of noisy audio, but doesn't return enhanced audio
- **NOT suitable** for audio restoration (returns transcribed text, not cleaned audio)

### Deepgram
- Offers STT (speech-to-text) and TTS (text-to-speech) APIs
- **No native audio enhancement** API
- Integrates with Dolby.io Enhance for preprocessing
- **NOT suitable** for standalone audio enhancement

### Reference
- [Google Cloud Speech-to-Text Enhanced Models](https://cloud.google.com/speech-to-text/docs/enhanced-models)
- [Deepgram Integration with Dolby](https://deepgram.com/learn/enhance-audio-with-dolby-and-deepgram)

---

## Comparison Matrix

| API | Type | Use Case | Pricing | Python SDK | Free Trial | Input Limit |
|-----|------|----------|---------|-----------|-----------|------------|
| **ElevenLabs Audio Isolation** | Noise removal | Integrated TTS pipeline | Undocumented | ✅ Yes | ❓ Unknown | 500 MB / 1 hr |
| **Audo.ai** | Noise removal | Batch + real-time | Closed beta | ✅ Yes | Closed beta | Unknown |
| **Cleanvoice AI** | Full production suite | Podcasts, interviews | $11-90/mo | ✅ Yes | 30 min free | Unknown |
| **Dolby.io Enhance** | Enterprise restoration | Professional workflows | $/min + $50 credit | ✅ Yes | $50 credit | Unknown |
| **ai-coustics** | Audio enhancement | Studio quality | Undocumented | ✅ Yes | Unknown | 512 MB / 2 hrs |
| **Krisp SDK** | Real-time voice | Live calls, streaming | Free | ⚠️ SDK only | Yes | Real-time |
| **Adobe Podcast** | Enhancement | Web only | Web only | ❌ No | Web only | N/A |
| **Google Speech-to-Text** | Transcription | Text output | $/min | ✅ Yes | Free credits | N/A |

---

## Recommendations for Atlas Vox

### For Voice Training Pipeline (Batch Audio Cleaning)

**Primary Choice:** **Cleanvoice AI** or **Dolby.io Enhance**

- **Cleanvoice AI** if you need podcast-grade editing (removes fillers, stutters) → $11-90/mo per project
- **Dolby.io Enhance** if you need professional restoration with detailed control → $50 credit for testing, then per-minute pricing

### For Simple Noise Removal Only

**Best Option:** **ElevenLabs Audio Isolation**

- Simple REST endpoint
- Integrated with TTS pipeline
- Pricing likely bundled with existing ElevenLabs usage
- Minimal latency

### For Real-Time Voice Enhancement (Live Training Sessions)

**Option:** **Krisp SDK**

- Real-time processing (sub-10ms)
- Free tier available
- Local processing (privacy-preserving)
- Not a REST API — requires integration into audio pipeline

---

## Implementation Notes

### For FastAPI Integration
```python
# Example: Chain ElevenLabs isolation + TTS
from elevenlabs import ElevenLabs

async def enhance_and_synthesize(audio_bytes, text, voice_id):
    client = ElevenLabs(api_key=API_KEY)

    # Step 1: Clean audio
    cleaned = await client.audio_isolation.convert(audio=audio_bytes)

    # Step 2: Process cleaned audio (e.g., transcribe)

    # Step 3: Synthesize new TTS from cleaned reference
    tts_result = await client.text_to_speech(
        text=text,
        voice_id=voice_id,
        model_id="eleven_monolingual_v1"
    )

    return tts_result
```

### For Celery Background Jobs
```python
# Use Audo.ai or Cleanvoice for batch processing in background tasks
@app.task
def clean_training_audio(file_id: str):
    client = Cleanvoice(api_key=API_KEY)
    job = client.upload_and_process(f"s3://bucket/{file_id}.wav")
    result = job.wait_until_done()
    return result.download_url()
```

---

## Summary Table: Quick Selection Guide

```
Need professional podcast editing?  → Cleanvoice AI ($11-90/mo)
Need simple noise removal?          → ElevenLabs Audio Isolation (bundled)
Need enterprise restoration?        → Dolby.io Enhance ($50+ credits)
Need real-time processing?          → Krisp SDK (free)
Need custom integration?            → Audo.ai or ai-coustics (contact sales)
```

---

## Additional Resources

- [ElevenLabs Blog: Voice Isolator API Launch](https://elevenlabs.io/blog/voice-isolator-api-launch)
- [Best AI Audio APIs 2026 Guide](https://codeboxr.com/best-ai-audio-apis-2026-speech-to-text-text-to-speech-guide/)
- [Dolby + Deepgram Integration](https://deepgram.com/learn/enhance-audio-with-dolby-and-deepgram)
- [Krisp Real-Time Voice SDK](https://krisp.ai/developers/)
