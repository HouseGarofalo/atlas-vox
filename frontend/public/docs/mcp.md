# MCP Integration

## What is MCP?

The **Model Context Protocol (MCP)** is an open standard that allows AI assistants like Claude to interact with external tools and data sources. Atlas Vox implements an MCP server that exposes voice synthesis, training, and management capabilities as tools that any MCP-compatible AI assistant can invoke. This means you can ask Claude to "speak this text with my voice" or "start training a new voice model" and it will use Atlas Vox behind the scenes.

---

## MCP Tools (9)

### atlas_vox_synthesize

Synthesize text to speech using a voice profile.

**Inputs:** `text` (str), `profile_id` (str), `speed?` (number)

```json
{"text": "Hello world", "profile_id": "abc-123", "speed": 1.0}
```

### atlas_vox_speak

Speak text using any available voice. No profile needed.

**Inputs:** `text` (str), `voice?` (str), `provider?` (str), `speed?` (number)

```json
{"text": "Hello world", "voice": "af_heart", "provider": "kokoro"}
```

### atlas_vox_list_voices

List all voice profiles in Atlas Vox.

**Inputs:** (none)

```json
{}
```

### atlas_vox_list_available_voices

List all available voices from all TTS providers (not profiles).

**Inputs:** `provider?` (str)

```json
{"provider": "kokoro"}
```

### atlas_vox_train_voice

Start training a voice model from uploaded samples.

**Inputs:** `profile_id` (str), `provider_name?` (str)

```json
{"profile_id": "abc-123"}
```

### atlas_vox_get_training_status

Get the status of a training job.

**Inputs:** `job_id` (str)

```json
{"job_id": "job-456"}
```

### atlas_vox_manage_profile

Create, update, or delete a voice profile.

**Inputs:** `action` (create|update|delete), `profile_id?` (str), `name?` (str)

```json
{"action": "create", "name": "My Voice", "provider_name": "kokoro"}
```

### atlas_vox_compare_voices

Compare the same text across multiple voice profiles.

**Inputs:** `text` (str), `profile_ids` (str[])

```json
{"text": "Test phrase", "profile_ids": ["id1", "id2"]}
```

### atlas_vox_provider_status

Get status and health of TTS providers.

**Inputs:** `provider_name?` (str)

```json
{"provider_name": "kokoro"}
```

---

## MCP Resources (2)

### atlas-vox://profiles

**Voice Profiles** (application/json)

List of all voice profiles in Atlas Vox with their status, provider, and configuration.

### atlas-vox://providers

**TTS Providers** (application/json)

Available TTS providers and their health status, capabilities, and configuration.

---

## Claude Desktop Configuration

Add this to your Claude Desktop `claude_desktop_config.json` to connect Claude to your Atlas Vox instance:

```json
{
  "mcpServers": {
    "atlas-vox": {
      "transport": "sse",
      "url": "http://localhost:8100/mcp/sse",
      "headers": {
        "Authorization": "Bearer avx_your_api_key_here"
      }
    }
  }
}
```

> **Note:** When `AUTH_DISABLED=true` (default), the Authorization header is optional. In production, create an API key with appropriate scopes on the API Keys page.

---

## Claude Code (CLI) Configuration

Add Atlas Vox as an MCP server in your Claude Code `settings.json` or project-level `.claude/settings.json`:

```json
{
  "mcpServers": {
    "atlas-vox": {
      "type": "sse",
      "url": "http://localhost:8100/mcp/sse",
      "headers": {
        "Authorization": "Bearer avx_your_api_key_here"
      }
    }
  }
}
```

Once configured, you can use Atlas Vox tools directly in Claude Code:

```
> Use atlas_vox_list_voices to show available voices
> Synthesize "Hello world" with the kokoro provider using atlas_vox_speak
> Check provider health with atlas_vox_provider_status
```

---

## Custom Python Agent Integration

Connect any Python agent to Atlas Vox using the `mcp` SDK:

```bash
pip install mcp httpx-sse
```

```python
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    # Connect to Atlas Vox MCP server
    async with sse_client(
        url="http://localhost:8100/mcp/sse",
        headers={"Authorization": "Bearer avx_your_api_key_here"}
    ) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")

            # List available voices
            result = await session.call_tool(
                "atlas_vox_list_voices", arguments={}
            )
            print(f"Voices: {result.content}")

            # Synthesize speech
            result = await session.call_tool(
                "atlas_vox_speak",
                arguments={
                    "text": "Hello from my custom agent!",
                    "voice": "af_heart",
                    "provider": "kokoro"
                }
            )
            print(f"Audio: {result.content}")

            # Check provider health
            result = await session.call_tool(
                "atlas_vox_provider_status", arguments={}
            )
            print(f"Providers: {result.content}")

asyncio.run(main())
```

---

## Claude Agent SDK (Anthropic)

Use Atlas Vox as a tool server in agents built with the Anthropic Agent SDK:

```python
from anthropic import Anthropic
from claude_agent_sdk import Agent, MCPServerConfig

# Configure Atlas Vox as an MCP server
atlas_vox = MCPServerConfig(
    name="atlas-vox",
    transport="sse",
    url="http://localhost:8100/mcp/sse",
    headers={"Authorization": "Bearer avx_your_api_key_here"}
)

# Create an agent with Atlas Vox tools
agent = Agent(
    model="claude-sonnet-4-6",
    mcp_servers=[atlas_vox],
    system_prompt="""You are a voice assistant. You can:
    - List available voices with atlas_vox_list_voices
    - Synthesize speech with atlas_vox_speak
    - Train new voice models with atlas_vox_train_voice
    - Compare voices with atlas_vox_compare_voices
    - Check provider status with atlas_vox_provider_status"""
)

# Run the agent
result = agent.run("Synthesize 'Welcome to Atlas Vox' using the best available voice")
```

---

## LangChain / LangGraph Integration

Use the OpenAI-compatible API endpoint for LangChain agents. No MCP configuration needed -- Atlas Vox exposes `POST /v1/audio/speech` which works with any OpenAI SDK client:

```python
from openai import OpenAI

# Point the OpenAI client at Atlas Vox
client = OpenAI(
    base_url="http://localhost:8100/v1",
    api_key="not-needed"  # AUTH_DISABLED=true
)

# Synthesize speech (OpenAI-compatible)
response = client.audio.speech.create(
    model="tts-1",       # Maps to Kokoro
    voice="alloy",       # Maps to af_alloy
    input="Hello from LangChain!",
    speed=1.0
)

# Save the audio
response.stream_to_file("output.mp3")
```

**Model mapping:** `tts-1` -> Kokoro, `tts-1-hd` -> ElevenLabs. **Voice mapping:** alloy, echo, fable, onyx, nova, shimmer map to Kokoro voices.

---

## Direct REST API (curl / httpx / fetch)

For custom integrations without MCP, use the REST API directly:

### curl

```bash
# Synthesize text (requires a voice profile ID)
curl -X POST http://localhost:8100/api/v1/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "profile_id": "YOUR_PROFILE_ID"}' \
  | jq .

# OpenAI-compatible endpoint (no profile needed)
curl -X POST http://localhost:8100/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model": "tts-1", "voice": "alloy", "input": "Hello world"}' \
  --output hello.mp3

# List all providers
curl http://localhost:8100/api/v1/providers | jq .

# Health check
curl http://localhost:8100/api/v1/health | jq .
```

### Python (httpx)

```python
import httpx

client = httpx.Client(base_url="http://localhost:8100")

# List voices
voices = client.get("/api/v1/voices").json()
print(f"{voices['count']} voices available")

# Synthesize
result = client.post("/api/v1/synthesize", json={
    "text": "Hello from Python!",
    "profile_id": "your-profile-id",
    "speed": 1.0,
    "output_format": "wav"
}).json()
print(f"Audio: {result['audio_url']}")
```

### JavaScript (fetch)

```javascript
// List providers
const providers = await fetch('http://localhost:8100/api/v1/providers')
  .then(r => r.json());
console.log(providers.providers.map(p => p.display_name));

// OpenAI-compatible synthesis
const audio = await fetch('http://localhost:8100/v1/audio/speech', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model: 'tts-1',
    voice: 'alloy',
    input: 'Hello from JavaScript!'
  })
});
const blob = await audio.blob();
// Play or save the audio blob
```

---

## n8n / Make / Zapier (Webhook)

Use Atlas Vox webhooks to trigger automations when training completes or fails:

```bash
# Subscribe to training events
curl -X POST http://localhost:8100/api/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-n8n-instance.com/webhook/atlas-vox",
    "events": "training.completed,training.failed",
    "secret": "your-hmac-secret"
  }'
```

Atlas Vox sends HMAC-SHA256 signed payloads to your webhook URL. Verify with the `X-Atlas-Vox-Signature` header.

For **n8n**: Use an HTTP Webhook trigger node. For **Make**: Use a Custom Webhook module. For **Zapier**: Use Webhooks by Zapier as the trigger. The payload includes job ID, profile ID, provider, status, and error details.

---

## SSE Transport Details

Atlas Vox uses **Server-Sent Events (SSE)** as the MCP transport mechanism. SSE provides a persistent, one-way connection from server to client, with client-to-server communication via HTTP POST to a messages endpoint.

```
Transport Flow:
  1. Client connects to GET /mcp/sse
  2. Server sends SSE event with messages endpoint URL
  3. Client sends JSONRPC 2.0 requests via POST to /mcp/message
  4. Server streams responses back via SSE

Endpoints:
  GET  /mcp/sse          -- SSE connection (persistent)
  POST /mcp/message      -- JSONRPC 2.0 requests

Protocol:     JSONRPC 2.0
Auth:         Bearer token in Authorization header
              Optional when AUTH_DISABLED=true (default)
Scopes:       read, write, synthesize, train, admin
Keepalive:    Ping every 30 seconds
```

---

## API Key Scopes for MCP

Each MCP tool requires specific scopes. Create an API key on the API Keys page with the appropriate scopes for your use case:

| Tool | Required Scope | Use Case |
|------|---------------|----------|
| `atlas_vox_list_voices` | read | Browse available voices |
| `atlas_vox_provider_status` | read | Check provider health |
| `atlas_vox_get_training_status` | read | Monitor training jobs |
| `atlas_vox_list_available_voices` | read | Browse provider voices |
| `atlas_vox_synthesize` | synthesize | Generate speech from profile |
| `atlas_vox_speak` | synthesize | Quick synthesis (no profile) |
| `atlas_vox_compare_voices` | synthesize | Side-by-side comparison |
| `atlas_vox_manage_profile` | write | Create/update/delete profiles |
| `atlas_vox_train_voice` | train | Start training jobs |

### Create Scoped API Keys

```bash
# Read-only key (list voices, check health)
curl -X POST http://localhost:8100/api/v1/api-keys \
  -H "Content-Type: application/json" \
  -d '{"name": "my-agent-readonly", "scopes": ["read"]}'

# Synthesis key (read + synthesize)
curl -X POST http://localhost:8100/api/v1/api-keys \
  -H "Content-Type: application/json" \
  -d '{"name": "my-agent-synth", "scopes": ["read", "synthesize"]}'

# Full access key
curl -X POST http://localhost:8100/api/v1/api-keys \
  -H "Content-Type: application/json" \
  -d '{"name": "my-agent-admin", "scopes": ["admin"]}'
```
