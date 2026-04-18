# Atlas Vox — Claude Agent SDK Bridge

Expose Atlas Vox as a drop-in tool set for any Claude Agent SDK
application. The bridge packages Atlas Vox's REST surface as Anthropic
tool-use schemas plus a synchronous HTTP dispatcher.

## Quick start

```python
import os
from anthropic import Anthropic
from app.agent_bridge import TOOL_SCHEMAS, ToolDispatcher

client = Anthropic()  # picks up ANTHROPIC_API_KEY
dispatcher = ToolDispatcher(
    base_url=os.environ["ATLAS_VOX_URL"],      # http://localhost:8100
    api_key=os.environ["ATLAS_VOX_API_KEY"],   # optional
)

messages = [{"role": "user", "content": "Narrate 'Once upon a time' in my best voice."}]

while True:
    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        tools=TOOL_SCHEMAS,
        messages=messages,
    )

    if resp.stop_reason == "end_turn":
        print(resp.content[0].text)
        break

    if resp.stop_reason == "tool_use":
        tool_use = next(b for b in resp.content if b.type == "tool_use")
        result = dispatcher.run(tool_use.name, tool_use.input)

        messages.append({"role": "assistant", "content": resp.content})
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": str(result),
            }],
        })
```

## Available tools

| Tool | Purpose |
|------|---------|
| `atlas_vox_list_profiles` | Enumerate user's voice profiles |
| `atlas_vox_list_voices` | Enumerate library (built-in) voices |
| `atlas_vox_list_providers` | Enumerate TTS providers + their capabilities |
| `atlas_vox_recommend_voice` | Classify text and recommend a profile (SL-30) |
| `atlas_vox_synthesize` | Text → audio URL |
| `atlas_vox_render_audiobook` | Long-form markdown → crossfaded + LUFS-normalized audio (AP-41) |
| `atlas_vox_start_training` | Kick off a training / cloning job |
| `atlas_vox_training_status` | Poll a job's progress |
| `atlas_vox_quality_dashboard` | Per-profile quality rollup (VQ-36) |
| `atlas_vox_recommended_samples` | Next-best phonetically-balanced sentences (SL-29) |

`from app.agent_bridge import list_tool_names` returns the flat list of
tool names for introspection; `get_tool_schema(name)` returns a single
schema if you want to feed one tool at a time.

## Error handling

The dispatcher never raises on recoverable errors — instead it returns
a dict of the form `{"error": "...", "status_code": 404}`. That shape
flows cleanly back into the Claude conversation as a `tool_result`, so
the model can see the failure and decide whether to retry, prompt the
user, or pivot to a different tool.

Genuine bugs (JSON decode failures, transport crashes) are re-raised
as Python exceptions.

## Authentication

Pass `api_key=` to the dispatcher. The header is sent as
`Authorization: Bearer <key>`. Atlas Vox's backend accepts this on every
endpoint exposed through the bridge. When `AUTH_DISABLED=true` the key
is optional.

## Extending

Adding a new tool requires three edits:

1. **`app/agent_bridge/tools.py`** — append a schema dict to `TOOL_SCHEMAS`.
2. **`app/agent_bridge/client.py`** — add a handler function and register
   it in `_HANDLERS`.
3. **`tests/test_services/test_agent_bridge.py`** — the schema contract
   test covers the schema automatically; add a dispatcher test mapping
   the tool name to the expected HTTP route.

The test `test_tool_names_match_registered_handlers` will fail if you
forget either of the first two steps.

## Performance

The dispatcher uses synchronous `httpx.Client`. For high-throughput use
you can inject your own `client=httpx.Client(http2=True, limits=...)`;
the dispatcher won't close a client you supplied. When used from an
async context (e.g. inside FastAPI), wrap calls in
`asyncio.to_thread(dispatcher.run, name, args)` to avoid blocking the
event loop.

## Why both MCP and an Agent SDK bridge?

Atlas Vox already exposes an MCP server (`backend/app/mcp/`) for clients
that speak the Model Context Protocol (Claude Desktop, some editor
plugins). The Agent SDK bridge exists because:

- Not every Anthropic SDK integration wants to talk MCP.
- Some applications need to pin a specific schema version.
- The tool schemas can be emitted as a static JSON manifest for
  deployment into environments without network access to Atlas Vox at
  compile time.

Both paths converge on the same backend endpoints — pick whichever fits
your integration shape.
