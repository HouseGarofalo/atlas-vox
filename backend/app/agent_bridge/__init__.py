"""Atlas Vox — Claude Agent SDK bridge.

IN-48 deliverable. A lightweight, dependency-minimal Python module that
exposes Atlas Vox synthesis / voice-library / training / audiobook /
quality-dashboard / recommender tools in the Anthropic tool-use schema,
so any Claude Agent SDK application can drop them in:

    from anthropic import Anthropic
    from app.agent_bridge import TOOL_SCHEMAS, ToolDispatcher

    client = Anthropic()
    dispatcher = ToolDispatcher(base_url="http://atlas-vox.local",
                                api_key=os.environ["ATLAS_API_KEY"])

    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        tools=TOOL_SCHEMAS,
        messages=[{"role": "user", "content": "Narrate 'hello world' in my clone voice"}],
    )
    # When resp.stop_reason == "tool_use":
    result = dispatcher.run(tool_name, tool_input)

Design notes:
- The bridge does NOT import the FastAPI app — it's purely an HTTP client
  wrapping the existing REST surface. This lets external projects consume
  atlas-vox as a remote service.
- Each tool schema follows Anthropic's published Tool shape: ``name``,
  ``description``, ``input_schema``. All fields are static JSON so a bundle
  can be emitted without running the app.
- The dispatcher returns provider-agnostic dicts so a downstream Claude
  conversation can format the result into a user-facing reply.
"""

from app.agent_bridge.client import ToolDispatcher
from app.agent_bridge.tools import TOOL_SCHEMAS, list_tool_names

__all__ = ["TOOL_SCHEMAS", "ToolDispatcher", "list_tool_names"]
__version__ = "0.1.0"
