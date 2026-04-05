---
name: Azure Custom Neural Voice (CNV) API Research
description: Comprehensive REST API documentation, authentication, training data requirements, and workflow for Azure Custom Neural Voice (Professional Voice Fine-tuning)
type: reference
---

# Azure Custom Neural Voice (CNV) — Comprehensive API Research

**Last Updated:** March 30, 2026
**API Version:** 2024-02-01-preview (Latest stable)
**Documentation Source:** Microsoft Learn official documentation

## 1. API Endpoints & Base URLs

All Custom Voice REST APIs use this base pattern:

```
https://{region}.api.cognitive.microsoft.com/customvoice/{resource}?api-version=2024-02-01-preview
```

**Example regions:** eastus, westus2, westeurope, eastasia, etc.

### Key Endpoints

| Operation | Method | Endpoint | Purpose |
|-----------|--------|----------|---------|
| **Projects_Create** | PUT | `/customvoice/projects/{projectId}` | Create a professional voice project |
| **Consents_Create** | PUT | `/customvoice/consents/{consentId}` | Add voice talent consent (from URL) |
| **Consents_Post** | POST | `/customvoice/consents/{consentId}` | Add voice talent consent (upload file) |
| **TrainingSets_Create** | PUT | `/customvoice/training-sets/{trainingSetId}` | Create a training set |
| **TrainingSets_UploadData** | POST | `/customvoice/training-sets/{trainingSetId}:uploadData` | Upload training data (audio + transcripts) |
| **Models_Create** | PUT | `/customvoice/models/{modelId}` | Create/train a voice model |
| **Models_Get** | GET | `/customvoice/models/{modelId}` | Get training status |
| **Endpoints_Create** | PUT | `/customvoice/endpoints/{endpointId}` | Deploy trained model as endpoint |
| **Endpoints_Suspend** | POST | `/customvoice/endpoints/{endpointId}:suspend` | Suspend endpoint (no charges) |
| **Endpoints_Resume** | POST | `/customvoice/endpoints/{endpointId}:resume` | Resume suspended endpoint |
| **Endpoints_Delete** | DELETE | `/customvoice/endpoints/{endpointId}` | Delete endpoint |

**Synthesis Endpoint (Text-to-Speech):**
```
https://{region}.voice.speech.microsoft.com/cognitiveservices/v1?deploymentId={endpointId}
```

---

## 2. Authentication

### Method 1: Subscription Key (Recommended for REST)

```http
Ocp-Apim-Subscription-Key: {your-speech-resource-key}
```

**Example header:**
```http
Ocp-Apim-Subscription-Key: 1234567890abcdefghijklmnopqrstuv
```

### Method 2: Bearer Token (OAuth)

First, get a token from:
```
https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken
```

Then use:
```http
Authorization: Bearer {access-token}
```

Tokens are valid for **10 minutes**.

### Method 3: Microsoft Entra ID (Managed Identity)

For enterprise deployments, use Microsoft Entra authentication with `Authorization: Bearer` header.

---

## 3. Training Data Requirements

### Audio Format

| Property | Value | Notes |
|----------|-------|-------|
| **File Format** | RIFF (.wav) or .mp3 | Grouped in .zip |
| **Sample Rate** | 24 KHz or higher | **Minimum:** 16 kHz (will be upsampled to 24 kHz) |
| **Bit Depth** | PCM, 16-bit minimum | 24-bit acceptable |
| **Channels** | Mono (1 channel) | Stereo not supported |
| **Audio Length** | < 15 seconds per file | For individual utterances |
| **Archive Size** | Max 2048 MB per .zip | ≤ 1,000 files per .zip |
| **Filename** | Windows-compatible .wav | No: `\ / : * ? " < > |` chars; can't start/end with space or dot; no duplicates |

### Transcript Format

| Property | Value | Notes |
|----------|-------|-------|
| **File Format** | Plain text (.txt) | One transcript per audio file |
| **Encoding** | ANSI, ASCII, UTF-8, UTF-8-BOM, UTF-16-LE, UTF-16-BE | zh-CN: Not ANSI/ASCII |
| **Matching** | Tab-separated (audio_name.wav[TAB]transcription) | One utterance per line |
| **Accuracy** | 100% accurate transcriptions required | Errors degrade voice quality |
| **File Size** | Max 2048 MB | Group .txt files in .zip |

**Transcript Example:**
```
0000000001	This is the waistline, and it's falling.
0000000002	We have trouble scoring.
0000000003	It was Janet Maslin.
```

### Training Data Size Requirements

| Tier | Data Size | Use Case | Voice Quality |
|------|-----------|----------|---------------|
| **Lite** | 20-50 utterances | Demo / evaluation | Moderate |
| **Professional (Standard)** | 300-2,000 utterances (30 min - 3 hours) | Production use | High quality |
| **Production (Recommended)** | 2,000+ utterances (2-3 hours) | Best results | Excellent |

**Key:** At least 300 utterances (30 minutes) required for professional voice. Recommend 2,000 utterances for production-grade voice quality.

### Data Types Supported

1. **Individual Utterances + Matching Transcript** ← Recommended
   - Pre-segmented audio files (< 15 seconds each)
   - One transcript per audio file
   - Ready for immediate fine-tuning

2. **Long Audio + Transcript**
   - Unsegmented audio files (> 20 seconds, up to 1,000 per .zip)
   - Full transcripts covering all audio
   - Requires batch transcription segmentation
   - **Supported languages only:** See documentation

3. **Audio Only**
   - No transcripts provided
   - Speech service auto-segments and transcribes
   - Slower processing, higher cost
   - **Supported languages only:** See documentation

---

## 4. Consent Statement Requirements

### Voice Talent Consent

**Mandatory recording from voice talent:**

> "I [state your first and last name] am aware that recordings of my voice will be used by [state the name of the company] to create and use a synthetic version of my voice."

### Consent Audio Specifications

- **Format:** WAV or MP3
- **Content:** Exact statement as text (language-specific)
- **Sample Rate:** Match training data (24 kHz recommended)
- **Storage:** Upload to publicly accessible URL with SAS token, or use direct upload endpoint

### Consent Metadata

Required fields when submitting consent:

- `voiceTalentName` — Person who recorded consent (in original language)
- `companyName` — Company name (must match what was spoken in recording)
- `locale` — Language code (e.g., "en-US", "zh-CN")
- `audioUrl` — SAS token URL or direct file reference

---

## 5. Complete REST API Workflow

### Step 1: Create Project

```http
PUT https://{region}.api.cognitive.microsoft.com/customvoice/projects/{projectId}?api-version=2024-02-01-preview
Ocp-Apim-Subscription-Key: {key}
Content-Type: application/json

{
  "kind": "ProfessionalVoice",
  "description": "Custom voice for chatbot"
}
```

**Response (201 Created):**
```json
{
  "id": "projectId",
  "kind": "ProfessionalVoice",
  "description": "Custom voice for chatbot",
  "createdDateTime": "2024-03-30T10:00:00.000Z"
}
```

### Step 2: Create Training Set

```http
PUT https://{region}.api.cognitive.microsoft.com/customvoice/training-sets/{trainingSetId}?api-version=2024-02-01-preview
Ocp-Apim-Subscription-Key: {key}
Content-Type: application/json

{
  "projectId": "projectId",
  "voiceKind": "Female",
  "locale": "en-US",
  "description": "Female voice training data"
}
```

**Response:**
```json
{
  "id": "trainingSetId",
  "projectId": "projectId",
  "voiceKind": "Female",
  "locale": "en-US",
  "description": "Female voice training data",
  "createdDateTime": "2024-03-30T10:05:00.000Z"
}
```

### Step 3: Add Consent (from URL)

```http
PUT https://{region}.api.cognitive.microsoft.com/customvoice/consents/{consentId}?api-version=2024-02-01-preview
Ocp-Apim-Subscription-Key: {key}
Content-Type: application/json

{
  "projectId": "projectId",
  "voiceTalentName": "Jane Doe",
  "companyName": "Acme Corp",
  "locale": "en-US",
  "audioUrl": "https://storage.blob.core.windows.net/consent/jane_consent.wav?sv=2021-06-08&..."
}
```

### Step 4: Upload Training Data

First, upload audio and transcript files to **Azure Blob Storage** with SAS tokens.

Then call:

```http
POST https://{region}.api.cognitive.microsoft.com/customvoice/training-sets/{trainingSetId}:uploadData?api-version=2024-02-01-preview
Ocp-Apim-Subscription-Key: {key}
Content-Type: application/json

{
  "kind": "AudioAndScript",
  "audios": {
    "containerUrl": "https://storage.blob.core.windows.net/audio-container?sv=2021-06-08&...",
    "extensions": [".wav"],
    "prefix": "utterances/"
  },
  "scripts": {
    "containerUrl": "https://storage.blob.core.windows.net/script-container?sv=2021-06-08&...",
    "extensions": [".txt"],
    "prefix": "transcripts/"
  }
}
```

### Step 5: Create & Train Voice Model

```http
PUT https://{region}.api.cognitive.microsoft.com/customvoice/models/{modelId}?api-version=2024-02-01-preview
Ocp-Apim-Subscription-Key: {key}
Content-Type: application/json

{
  "voiceName": "JaneNeuralVoice",
  "description": "Jane custom neural voice",
  "projectId": "projectId",
  "consentId": "consentId",
  "trainingSetId": "trainingSetId",
  "recipe": {
    "kind": "Default"
  }
}
```

**Response (201 Created):**
```json
{
  "id": "modelId",
  "voiceName": "JaneNeuralVoice",
  "status": "NotStarted",
  "recipe": {
    "kind": "Default",
    "version": "V7.2023.03"
  },
  "engineVersion": "2023.07.04.0",
  "createdDateTime": "2024-03-30T10:15:00.000Z"
}
```

### Step 6: Check Training Status

```http
GET https://{region}.api.cognitive.microsoft.com/customvoice/models/{modelId}?api-version=2024-02-01-preview
Ocp-Apim-Subscription-Key: {key}
```

**Status values:** `NotStarted` → `Running` → `Succeeded` or `Failed`

**Training duration:** ~10-20 compute hours (average)

### Step 7: Deploy as Endpoint

Once training succeeds (status = "Succeeded"):

```http
PUT https://{region}.api.cognitive.microsoft.com/customvoice/endpoints/{endpointId}?api-version=2024-02-01-preview
Ocp-Apim-Subscription-Key: {key}
Content-Type: application/json

{
  "projectId": "projectId",
  "modelId": "modelId",
  "description": "Production endpoint for Jane voice",
  "properties": {
    "kind": "HighPerformance"
  }
}
```

**Endpoint types:**
- **HighPerformance** — Real-time, high-volume synthesis (~5 min to deploy)
- **FastResume** — Audio content creation, light usage (< 1 min to deploy)

### Step 8: Use Deployed Voice (Synthesis)

Via REST API:

```http
POST https://{region}.voice.speech.microsoft.com/cognitiveservices/v1?deploymentId={endpointId}
Ocp-Apim-Subscription-Key: {key}
Content-Type: application/ssml+xml
X-Microsoft-OutputFormat: riff-24khz-16bit-mono-pcm

<speak version="1.0" xml:lang="en-US">
    <voice name="JaneNeuralVoice">
        Hello, this is your custom voice speaking.
    </voice>
</speak>
```

Or via Speech SDK (see SDK section below).

---

## 6. Training Methods (Recipe Kinds)

Azure CNV supports four training approaches:

### Recipe Kind: Default (Neural)

- **Language:** Same as training data
- **Use case:** Standard custom voices
- **Training time:** ~10-20 compute hours
- **Minimum data:** 300 utterances
- **Version:** V7.2023.03 (current)

**Request:**
```json
"recipe": { "kind": "Default" }
```

### Recipe Kind: CrossLingual

- **Language:** Different from training data
- **Example:** Train on French data, deploy for German
- **Supported language pairs:** Limited (check docs)
- **Use case:** Accent transfer, multilingual voices
- **Minimum data:** 300 utterances in source language

**Request:**
```json
"recipe": { "kind": "CrossLingual" },
"locale": "de-DE"  // Target language
```

### Recipe Kind: MultiStyle

- **Styles:** Multiple emotional/conversational styles in one voice
- **Preset styles:** Cheerful, sad, angry, calm, etc. (per language)
- **Custom styles:** Provide 100+ utterances per custom style
- **Max custom styles:** English 10, Chinese 4, Japanese 5
- **Use case:** Games, chatbots, audiobooks

**Request:**
```json
"recipe": { "kind": "MultiStyle" },
"locale": "en-US",
"properties": {
  "presetStyles": ["cheerful", "sad"],
  "styleTrainingSetIds": {
    "friendly": "trainingSetId2",
    "formal": "trainingSetId3"
  }
}
```

### Recipe Kind: HD (Dragon HD Latest Neural)

- **Quality:** LLM-based, highest quality
- **Use case:** Dynamic conversations, conversational AI
- **Voice name format:** Must end with `:DragonHDLatestNeural`
- **Training time:** Longer than standard
- **Minimum data:** 300-2,000 utterances

**Request:**
```json
"recipe": { "kind": "HD" },
"voiceName": "JaneHDVoice:DragonHDLatestNeural"
```

---

## 7. Custom Neural Voice Lite vs Professional

| Feature | Lite | Professional |
|---------|------|--------------|
| **Recording** | Online in Speech Studio (20-50 utterances) | Professional studio, bring your own data (300-2,000+) |
| **Script** | Microsoft-provided, pre-defined | Your own scripts |
| **Training Time** | < 1 compute hour | ~20-40 compute hours |
| **Voice Quality** | Moderate | High (excellent with 2,000+ utterances) |
| **Deployment** | Requires full access approval | Full access required |
| **Data Retention** | Auto-deleted after 90 days unless deployed | User controls retention |
| **Cost** | Same per-unit pricing | Same per-unit pricing |
| **Use Case** | Demo, evaluation | Production, brand voices |
| **API Support** | Speech Studio only | REST API + Speech SDK |

**Key difference:** Lite is **UI-only, no API support**. Professional supports full REST/SDK automation.

---

## 8. SDK Support

### Speech SDK (NOT for training, only synthesis)

The Azure Cognitive Services **Speech SDK** does **NOT** support programmatic training data upload or model training. All training operations are **REST API only**.

**SDK use:** Synthesis with custom voices (after deployment)

**Supported SDKs:** C#, Python, JavaScript, Java, Go, Objective-C, Swift

**Example (C# synthesis with custom endpoint):**
```csharp
var speechConfig = SpeechConfig.FromSubscription(key, region);
speechConfig.SpeechSynthesisVoiceName = "JaneNeuralVoice";
speechConfig.EndpointId = "{endpointId}";

using var synthesizer = new SpeechSynthesizer(speechConfig, AudioConfig.FromDefaultSpeakerOutput());
var result = synthesizer.SpeakTextAsync("Hello world").Result;
```

---

## 9. API Quotas & Limits

| Resource | Standard (S0) | Notes |
|----------|---------------|-------|
| **Projects** | Unlimited | Per Speech resource |
| **Models per project** | Unlimited | Training sequential |
| **Endpoints** | 50 max | Per Speech resource |
| **Simultaneous training** | 4 models | Queue others; wait for one to finish |
| **Training set imports** | 5 simultaneous | S0 users; wait for one to finish |
| **Max datasets** | 500 .zip files | Per subscription |
| **Archive size** | 2048 MB max | Per .zip file |
| **Files per archive** | 1,000 max | For long audio / audio-only |

---

## 10. Regional Availability

**Professional Voice Fine-tuning supported in:**
- eastus, westus2, westeurope, eastasia, and others

**Check:** https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions (footnotes on custom voice)

**Note:** Voice models trained in supported region can be copied to other regions via Foundry.

---

## 11. Error Handling

**Common HTTP status codes:**

| Status | Meaning | Example |
|--------|---------|---------|
| **201 Created** | Resource created successfully | Model/endpoint creation |
| **204 No Content** | Success, no response body | Delete operations |
| **400 Bad Request** | Invalid request format | Missing required field |
| **401 Unauthorized** | Invalid subscription key | Wrong key or expired token |
| **403 Forbidden** | Limited access not granted | Not approved for custom voice |
| **404 Not Found** | Resource doesn't exist | Invalid model ID |
| **429 Too Many Requests** | Rate limit exceeded | Wait and retry |
| **500 Server Error** | Service error | Transient; retry with backoff |

**Error response format:**
```json
{
  "error": {
    "code": "BadArgument",
    "message": "projectId is required",
    "target": "projectId"
  }
}
```

---

## 12. Key Takeaways for Integration

1. **REST API only** for training (no SDK support)
2. **Azure Blob Storage required** for training data uploads (use SAS tokens)
3. **Authentication:** Subscription key in `Ocp-Apim-Subscription-Key` header
4. **Audio:** 24 kHz WAV, mono, < 15 seconds per file, PCM 16-bit
5. **Transcripts:** Tab-separated, 100% accurate, one per audio
6. **Minimum data:** 300 utterances (30 minutes) for professional voice
7. **Training time:** ~10-20 compute hours average
8. **Consent:** Mandatory voice talent verbal statement required
9. **Deployment:** Separate endpoint creation; up to 50 endpoints per resource
10. **Synthesis:** Use Speech SDK or REST; specify voice name and endpoint ID

---

## References

- [Custom Voice API Reference](https://learn.microsoft.com/rest/api/aiservices/speechapi/)
- [Professional Voice Training](https://learn.microsoft.com/azure/ai-services/speech-service/professional-voice-train-voice)
- [Custom Voice Training Data](https://learn.microsoft.com/azure/ai-services/speech-service/how-to-custom-voice-training-data)
- [Deploy Professional Voice](https://learn.microsoft.com/azure/ai-services/speech-service/professional-voice-deploy-endpoint)
- [Custom Voice Lite vs Professional](https://learn.microsoft.com/azure/ai-services/speech-service/custom-neural-voice-lite)
