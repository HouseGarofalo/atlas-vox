# Azure Speech

> Cloud API — 400+ neural voices across 140+ languages

Microsoft Azure Cognitive Services TTS with 400+ neural voices, full SSML support, and enterprise reliability.

**Website:** [https://azure.microsoft.com/en-us/products/ai-services/text-to-speech](https://azure.microsoft.com/en-us/products/ai-services/text-to-speech)

## Quality Notes

Enterprise-grade quality. Only provider with full SSML support for fine-grained prosody control. Very low latency. Best for multilingual and enterprise deployments.

## Setup Steps

### Step 1: Create an Azure Account

Sign up at azure.microsoft.com. A free tier with 500K characters/month is available for neural voices.

### Step 2: Create a Speech Resource

In the Azure Portal, search for 'Speech' and create a new Speech resource. Note the region you select (e.g., eastus).

### Step 3: Get Your Key and Region

Go to your Speech resource > Keys and Endpoint. Copy Key 1 and the Region.

```bash
AZURE_SPEECH_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AZURE_SPEECH_REGION=eastus
```

### Step 4: Configure in Atlas Vox

Go to Providers > Azure Speech > Settings. Enter the subscription key and region. Click Save.

### Step 5: Test with SSML

Azure is the only provider that supports SSML. Try the SSML editor in the Synthesis Lab for prosody control.

```xml
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
  <voice name="en-US-JennyNeural">
    <prosody rate="medium" pitch="+2st">Hello from Azure Speech!</prosody>
  </voice>
</speak>
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AZURE_SPEECH_KEY | Yes | | Azure subscription key |
| AZURE_SPEECH_REGION | Yes | eastus | Azure region (e.g., eastus, westus2, westeurope) |

## Configuration Checklist

- [ ] Azure account and Speech resource created
- [ ] Subscription key and region configured
- [ ] Health check passes
- [ ] Can list Azure voices in Voice Library
- [ ] SSML synthesis works with Azure profiles

## Tips & Best Practices

- Free tier: 500K characters/month for neural voices
- 400+ neural voices across 140+ languages and variants
- Only provider with full SSML support for prosody, emphasis, and pronunciation
- Use en-US-JennyNeural for natural conversational English
- eastus region typically has lowest latency for US users

## Common Issues

### 401 Access Denied

Verify your subscription key is correct. Copy Key 1 from the Azure Portal > Speech resource > Keys.

### Wrong region error

Ensure AZURE_SPEECH_REGION matches the region where your Speech resource was created (e.g., eastus, not East US).

### SSML parsing errors

Validate your SSML against the W3C schema. Common issue: missing xmlns attribute or incorrect voice name.

## CLI Example

```bash
atlas-vox synthesize --text "Hello from Azure" --provider azure_speech --voice en-US-JennyNeural
```

## API Example

```bash
curl -X POST http://localhost:8100/api/v1/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from Azure", "provider_name": "azure_speech", "voice_id": "en-US-JennyNeural"}'
```
