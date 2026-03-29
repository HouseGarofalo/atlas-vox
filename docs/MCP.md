# Atlas Vox MCP Server Guide

> **Model Context Protocol integration for AI agent-driven voice synthesis, training, and profile management.**

Atlas Vox exposes an MCP server that allows AI agents (Claude Desktop, custom LLM pipelines, automation frameworks) to synthesize speech, manage voice profiles, run training jobs, and query provider status -- all through a standardized protocol.

---

## Table of Contents

- [Protocol Overview](#protocol-overview)
- [Transport](#transport)
  - [SSE Endpoint](#sse-endpoint)
  - [Message Endpoint](#message-endpoint)
- [Authentication](#authentication)
- [Server Capabilities](#server-capabilities)
- [Tools](#tools)
  - [atlas\_vox\_synthesize](#atlas_vox_synthesize)
  - [atlas\_vox\_list\_voices](#atlas_vox_list_voices)
  - [atlas\_vox\_train\_voice](#atlas_vox_train_voice)
  - [atlas\_vox\_get\_training\_status](#atlas_vox_get_training_status)
  - [atlas\_vox\_manage\_profile](#atlas_vox_manage_profile)
  - [atlas\_vox\_compare\_voices](#atlas_vox_compare_voices)
  - [atlas\_vox\_provider\_status](#atlas_vox_provider_status)
- [Resources](#resources)
  - [atlas-vox://profiles](#atlas-voxprofiles)
  - [atlas-vox://providers](#atlas-voxproviders)
- [Integration Examples](#integration-examples)
  - [Claude Desktop Configuration](#claude-desktop-configuration)
  - [Custom Python Client](#custom-python-client)
  - [curl Examples](#curl-examples)
- [Error Handling](#error-handling)
- [Architecture](#architecture)

---

## Protocol Overview

Atlas Vox implements the **Model Context Protocol (MCP)** specification version `2024-11-05`, using:

| Aspect | Implementation |
|---|---|
| **Wire protocol** | JSONRPC 2.0 |
| **Transport** | HTTP + Server-Sent Events (SSE) |
| **Content type** | `application/json` |
| **Capabilities** | Tools, Resources |

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant SSE as GET /mcp/sse
    participant MSG as POST /mcp/message
    participant Server as MCP Server

    Agent->>SSE: Connect (SSE stream)
    SSE-->>Agent: event: endpoint\ndata: /mcp/message

    Agent->>MSG: initialize
    MSG->>Server: handle_message
    Server-->>MSG: serverInfo + capabilities
    MSG-->>Agent: JSONRPC response

    Agent->>MSG: tools/list
    Server-->>Agent: 7 tools

    Agent->>MSG: tools/call (atlas_vox_synthesize)
    Server-->>Agent: audio result
```

---

## Transport

### SSE Endpoint

```
GET /mcp/sse
```

Establishes a persistent Server-Sent Events connection. The server sends:

1. **Initial `endpoint` event** -- tells the client where to send JSONRPC messages:
   ```
   event: endpoint
   data: /mcp/message
   ```

2. **Periodic `ping` events** (every 30 seconds) to keep the connection alive:
   ```
   event: ping
   data: {}
   ```

**Response headers:**

| Header | Value |
|---|---|
| `Content-Type` | `text/event-stream` |
| `Cache-Control` | `no-cache` |
| `Connection` | `keep-alive` |
| `X-Accel-Buffering` | `no` |

---

### Message Endpoint

```
POST /mcp/message
Content-Type: application/json
```

Accepts JSONRPC 2.0 requests and returns JSONRPC 2.0 responses.

**Supported methods:**

| Method | Description |
|---|---|
| `initialize` | Handshake -- returns protocol version and capabilities |
| `tools/list` | List all available tools |
| `tools/call` | Execute a tool with arguments |
| `resources/list` | List all available resources |
| `resources/read` | Read a resource by URI |
| `ping` | Liveness check |

---

## Authentication

MCP authentication follows the same rules as the REST API:

| Mode | Behavior |
|---|---|
| `AUTH_DISABLED=true` (default) | No authentication required |
| `AUTH_DISABLED=false` | API key required via `Authorization` header |

When authentication is enabled, include the API key as a Bearer token:

```
Authorization: Bearer avx_abc123...
```

The server validates the key against all active API keys stored in the database using Argon2id hash comparison.

---

## Server Capabilities

The `initialize` handshake returns:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {},
      "resources": {}
    },
    "serverInfo": {
      "name": "atlas-vox",
      "version": "0.1.0"
    }
  }
}
```

---

## Tools

Atlas Vox exposes 7 MCP tools. All tools return results in the standard MCP content format:

```json
{
  "content": [
    { "type": "text", "text": "..." }
  ]
}
```

On error, the response includes `"isError": true`.

---

### `atlas_vox_synthesize`

Synthesize text to speech using a voice profile.

**Input Schema:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `text` | `string` | Yes | -- | Text to synthesize |
| `profile_id` | `string` | Yes | -- | Voice profile UUID |
| `speed` | `number` | No | `1.0` | Speech speed (0.5 to 2.0) |

**Example Request:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "atlas_vox_synthesize",
    "arguments": {
      "text": "Hello from Atlas Vox!",
      "profile_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "speed": 1.0
    }
  }
}
```

**Example Response:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{
      "type": "text",
      "text": "{\"id\": \"syn_abc123\", \"audio_url\": \"/audio/output_abc123.wav\", \"duration_seconds\": 1.8, \"latency_ms\": 120, \"profile_id\": \"a1b2c3d4-...\", \"provider_name\": \"kokoro\"}"
    }]
  }
}
```

---

### `atlas_vox_list_voices`

List all available voice profiles.

**Input Schema:** No parameters.

**Example Request:**

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "atlas_vox_list_voices",
    "arguments": {}
  }
}
```

**Example Response:**

```json
{
  "content": [{
    "type": "text",
    "text": "[{\"id\": \"a1b2...\", \"name\": \"Narrator\", \"provider\": \"kokoro\", \"status\": \"ready\"}, ...]"
  }]
}
```

---

### `atlas_vox_train_voice`

Start a voice training job from uploaded samples.

**Input Schema:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `profile_id` | `string` | Yes | Voice profile UUID |
| `provider_name` | `string` | No | Override provider (uses profile default if omitted) |

**Example Request:**

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "atlas_vox_train_voice",
    "arguments": {
      "profile_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    }
  }
}
```

**Example Response:**

```json
{
  "content": [{
    "type": "text",
    "text": "{\"job_id\": \"job_xyz789\", \"status\": \"queued\", \"provider\": \"kokoro\"}"
  }]
}
```

---

### `atlas_vox_get_training_status`

Get the current status of a training job.

**Input Schema:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `job_id` | `string` | Yes | Training job UUID |

**Example Response:**

```json
{
  "content": [{
    "type": "text",
    "text": "{\"id\": \"job_xyz789\", \"status\": \"training\", \"progress\": 0.65, \"error_message\": null, \"result_version_id\": null}"
  }]
}
```

**Status values:** `queued`, `preprocessing`, `training`, `completed`, `failed`, `cancelled`

---

### `atlas_vox_manage_profile`

Create, update, or delete a voice profile.

**Input Schema:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `action` | `string` | Yes | One of: `create`, `update`, `delete` |
| `profile_id` | `string` | For update/delete | Profile UUID |
| `name` | `string` | For create | Profile name |
| `provider_name` | `string` | No | Provider (defaults to `kokoro`) |

**Create Example:**

```json
{
  "params": {
    "name": "atlas_vox_manage_profile",
    "arguments": {
      "action": "create",
      "name": "Podcast Host",
      "provider_name": "elevenlabs"
    }
  }
}
```

**Delete Example:**

```json
{
  "params": {
    "name": "atlas_vox_manage_profile",
    "arguments": {
      "action": "delete",
      "profile_id": "a1b2c3d4-..."
    }
  }
}
```

---

### `atlas_vox_compare_voices`

Compare the same text synthesized across multiple voice profiles.

**Input Schema:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `text` | `string` | Yes | Text to compare |
| `profile_ids` | `string[]` | Yes | Array of profile UUIDs (minimum 2) |

**Example Request:**

```json
{
  "params": {
    "name": "atlas_vox_compare_voices",
    "arguments": {
      "text": "Good morning, everyone.",
      "profile_ids": ["a1b2c3d4-...", "e5f6g7h8-..."]
    }
  }
}
```

**Example Response:**

```json
{
  "content": [{
    "type": "text",
    "text": "{\"text\": \"Good morning, everyone.\", \"results\": [{\"profile_name\": \"Narrator\", \"provider_name\": \"kokoro\", \"latency_ms\": 120, \"audio_url\": \"/audio/cmp_abc.wav\"}, ...]}"
  }]
}
```

---

### `atlas_vox_provider_status`

Get the health status and capabilities of TTS providers.

**Input Schema:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `provider_name` | `string` | No | Specific provider name. Omit to get all providers. |

**Single provider response:**

```json
{
  "content": [{
    "type": "text",
    "text": "{\"name\": \"kokoro\", \"healthy\": true, \"latency_ms\": 45, \"gpu_mode\": \"host_cpu\"}"
  }]
}
```

**All providers response:**

```json
{
  "content": [{
    "type": "text",
    "text": "[{\"name\": \"kokoro\", \"display_name\": \"Kokoro\", \"healthy\": true}, {\"name\": \"elevenlabs\", \"display_name\": \"ElevenLabs\", \"healthy\": null}, ...]"
  }]
}
```

Providers that are not yet implemented return `"healthy": null`.

---

## Resources

MCP resources provide read-only access to Atlas Vox data. Resources are accessed via `resources/read` with a URI.

### `atlas-vox://profiles`

Returns a JSON array of all voice profiles.

| Field | Type | Description |
|---|---|---|
| `uri` | `string` | `atlas-vox://profiles` |
| `name` | `string` | `Voice Profiles` |
| `mimeType` | `string` | `application/json` |

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "method": "resources/read",
  "params": { "uri": "atlas-vox://profiles" }
}
```

**Response:**

```json
{
  "result": {
    "contents": [{
      "uri": "atlas-vox://profiles",
      "mimeType": "application/json",
      "text": "[{\"id\": \"...\", \"name\": \"Narrator\", \"provider\": \"kokoro\", \"status\": \"ready\"}, ...]"
    }]
  }
}
```

---

### `atlas-vox://providers`

Returns a JSON array of all known TTS providers with implementation status.

| Field | Type | Description |
|---|---|---|
| `uri` | `string` | `atlas-vox://providers` |
| `name` | `string` | `TTS Providers` |
| `mimeType` | `string` | `application/json` |

**Response contents:**

```json
[
  {"name": "kokoro", "display_name": "Kokoro", "provider_type": "local", "implemented": true},
  {"name": "elevenlabs", "display_name": "ElevenLabs", "provider_type": "cloud", "implemented": true},
  {"name": "cosyvoice", "display_name": "CosyVoice", "provider_type": "local", "implemented": false}
]
```

---

## Integration Examples

### Claude Desktop Configuration

Add Atlas Vox as an MCP server in your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "atlas-vox": {
      "url": "http://localhost:8100/mcp/sse",
      "transport": "sse"
    }
  }
}
```

**With authentication enabled:**

```json
{
  "mcpServers": {
    "atlas-vox": {
      "url": "http://localhost:8100/mcp/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer avx_your_api_key_here"
      }
    }
  }
}
```

Once configured, Claude can use natural language to:
- "Synthesize this paragraph using the Narrator voice"
- "Create a new voice profile called 'Podcast Host' using ElevenLabs"
- "Check which TTS providers are healthy"
- "Compare how 'Hello world' sounds across my three voices"

---

### Custom Python Client

```python
import json
import httpx

BASE = "http://localhost:8100"

async def mcp_call(method: str, params: dict = {}, msg_id: int = 1) -> dict:
    """Send a JSONRPC 2.0 message to the Atlas Vox MCP server."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE}/mcp/message",
            json={
                "jsonrpc": "2.0",
                "id": msg_id,
                "method": method,
                "params": params,
            },
        )
        return response.json()

# Initialize the session
result = await mcp_call("initialize")
print(result["result"]["serverInfo"])
# {'name': 'atlas-vox', 'version': '0.1.0'}

# List available tools
tools = await mcp_call("tools/list", msg_id=2)
for tool in tools["result"]["tools"]:
    print(f"  {tool['name']}: {tool['description']}")

# Synthesize speech
synth = await mcp_call("tools/call", {
    "name": "atlas_vox_synthesize",
    "arguments": {
        "text": "Hello from my Python script!",
        "profile_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    },
}, msg_id=3)

audio_data = json.loads(synth["result"]["content"][0]["text"])
print(f"Audio URL: {audio_data['audio_url']}")
print(f"Latency: {audio_data['latency_ms']}ms")
```

---

### curl Examples

**Initialize:**

```bash
curl -X POST http://localhost:8100/mcp/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

**List tools:**

```bash
curl -X POST http://localhost:8100/mcp/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

**Synthesize speech:**

```bash
curl -X POST http://localhost:8100/mcp/message \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0","id":3,"method":"tools/call",
    "params":{
      "name":"atlas_vox_synthesize",
      "arguments":{"text":"Hello world","profile_id":"YOUR_PROFILE_ID"}
    }
  }'
```

**Read profiles resource:**

```bash
curl -X POST http://localhost:8100/mcp/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":4,"method":"resources/read","params":{"uri":"atlas-vox://profiles"}}'
```

---

## Error Handling

The MCP server uses standard JSONRPC 2.0 error codes:

| Code | Meaning | When |
|---|---|---|
| `-32700` | Parse error | Malformed JSON in request body |
| `-32601` | Method not found | Unknown JSONRPC method |
| `-32603` | Internal error | Unhandled exception in handler |

**Tool-level errors** (e.g., profile not found, provider unhealthy) return a successful JSONRPC response with `isError: true` in the tool result:

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "result": {
    "content": [{ "type": "text", "text": "Error: Profile not found" }],
    "isError": true
  }
}
```

**Notifications** (JSONRPC messages without an `id` field) are silently ignored, except for `initialize`.

---

## Architecture

```mermaid
graph TB
    subgraph "AI Agent"
        A[Claude Desktop / Custom Agent]
    end

    subgraph "Atlas Vox MCP Layer"
        SSE["GET /mcp/sse<br/>(SSE transport)"]
        MSG["POST /mcp/message<br/>(JSONRPC 2.0)"]
        SRV["MCPServer<br/>(singleton)"]
        TOOLS["7 Tool Handlers"]
        RES["2 Resource Handlers"]
    end

    subgraph "Atlas Vox Core"
        PS[Profile Service]
        SS[Synthesis Service]
        TS[Training Service]
        CS[Comparison Service]
        PR[Provider Registry]
        DB[(Database)]
    end

    A -->|"1. Connect"| SSE
    SSE -->|"2. endpoint: /mcp/message"| A
    A -->|"3. JSONRPC requests"| MSG
    MSG --> SRV
    SRV --> TOOLS
    SRV --> RES
    TOOLS --> PS
    TOOLS --> SS
    TOOLS --> TS
    TOOLS --> CS
    TOOLS --> PR
    PS --> DB
    SS --> DB
    TS --> DB
```

**Key design decisions:**

1. **Singleton server** -- `MCPServer` is instantiated once at module level and shared across all requests.
2. **Lazy imports** -- Tool handlers import services inside their function bodies to avoid circular dependencies and speed up startup.
3. **Database session per call** -- Each tool handler creates its own `async_session_factory()` context, ensuring clean transaction boundaries.
4. **Auth passthrough** -- MCP auth uses the same API key system as the REST API, validated at the transport layer before messages reach the server.
