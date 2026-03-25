# Atlas Vox MCP Integration Guide

## Overview

Atlas Vox exposes an MCP (Model Context Protocol) server for AI agent integration. Agents can synthesize speech, manage voices, and monitor training programmatically.

## Connection

### SSE Transport
```
GET /mcp/sse
```
Maintains a persistent Server-Sent Events connection. Returns the message endpoint URL.

### Message Endpoint
```
POST /mcp/message
Content-Type: application/json
```
Accepts JSONRPC 2.0 messages.

## Tools (7)

### `atlas_vox_synthesize`
Synthesize text to speech.
```json
{"text": "Hello world", "profile_id": "abc-123", "speed": 1.0}
```

### `atlas_vox_list_voices`
List all voice profiles.

### `atlas_vox_train_voice`
Start a training job.
```json
{"profile_id": "abc-123", "provider_name": "coqui_xtts"}
```

### `atlas_vox_get_training_status`
Check training job progress.
```json
{"job_id": "job-456"}
```

### `atlas_vox_manage_profile`
Create, update, or delete profiles.
```json
{"action": "create", "name": "My Voice", "provider_name": "kokoro"}
```

### `atlas_vox_compare_voices`
Compare text across multiple profiles.
```json
{"text": "Hello", "profile_ids": ["id1", "id2"]}
```

### `atlas_vox_provider_status`
Check provider health and capabilities.
```json
{"provider_name": "kokoro"}
```

## Resources (2)

- `atlas-vox://profiles` — All voice profiles
- `atlas-vox://providers` — All TTS providers with status

## Claude Code Configuration

Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "atlas-vox": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```
