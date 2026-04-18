"""HTTP dispatcher that implements the Agent SDK tool schemas.

The dispatcher deliberately uses synchronous ``httpx.Client`` so downstream
applications can use it from either sync or async contexts (Anthropic's
own SDK has both; the tool-call loop traditionally runs sync). Async
consumers can wrap individual calls in ``asyncio.to_thread(dispatcher.run, ...)``.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:  # pragma: no cover — httpx IS a runtime dep, but guard for vendoring
    _HAS_HTTPX = False

logger = logging.getLogger(__name__)


class ToolDispatcher:
    """Execute Atlas Vox tool calls against a running backend instance.

    Parameters
    ----------
    base_url:
        Atlas Vox backend URL, e.g. ``"http://localhost:8100"``. The
        dispatcher appends the ``/api/v1`` prefix itself.
    api_key:
        Optional API key. When set, it's sent as ``Authorization: Bearer``.
    timeout:
        Per-request timeout in seconds. Defaults to 30.
    client:
        Optional pre-built ``httpx.Client`` (useful for tests that want
        to inject a MockTransport).
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        timeout: float = 30.0,
        client: "httpx.Client | None" = None,
    ) -> None:
        if not _HAS_HTTPX and client is None:
            raise ImportError(
                "httpx is required for ToolDispatcher. "
                "Install with: pip install httpx"
            )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def run(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Dispatch ``tool_name`` with ``tool_input``.

        Returns a plain dict the caller can hand back to the Claude
        conversation as a ``tool_result`` content block. Errors surface
        as ``{"error": str, "status_code": int | None}`` so the LLM can
        see them too — raising would short-circuit the conversation.
        """
        handler = _HANDLERS.get(tool_name)
        if handler is None:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            return handler(self, tool_input)
        except _ToolError as exc:
            return {"error": exc.message, "status_code": exc.status_code}
        except Exception as exc:  # pragma: no cover — defensive
            logger.exception("agent_bridge_tool_crash: %s", tool_name)
            return {"error": f"unexpected error: {exc}"}

    def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "ToolDispatcher":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}/api/v1{path}"
        resp = self._client.get(url, params=params or {}, headers=self._headers())
        return self._unpack(resp)

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        url = f"{self.base_url}/api/v1{path}"
        resp = self._client.post(url, json=payload, headers=self._headers())
        return self._unpack(resp)

    @staticmethod
    def _unpack(resp: "httpx.Response") -> Any:
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text or f"HTTP {resp.status_code}"
            raise _ToolError(str(detail), status_code=resp.status_code)
        if resp.status_code == 204:
            return {}
        try:
            return resp.json()
        except Exception:
            return {"raw": resp.text}


class _ToolError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Tool handlers — each maps one schema name to the REST call it wraps.
# Kept as top-level functions so tests can monkey-patch individual ones.
# ---------------------------------------------------------------------------


def _synthesize(d: ToolDispatcher, args: dict[str, Any]) -> Any:
    payload = {
        "text": args["text"],
        "profile_id": args["profile_id"],
        "speed": args.get("speed", 1.0),
        "pitch": args.get("pitch", 0.0),
        "ssml": args.get("ssml", False),
        "output_format": args.get("output_format", "wav"),
    }
    return d._post("/synthesize", payload)


def _recommend_voice(d: ToolDispatcher, args: dict[str, Any]) -> Any:
    return d._post(
        "/synthesis/recommend-voice",
        {"text": args["text"], "limit": args.get("limit", 3)},
    )


def _list_profiles(d: ToolDispatcher, _args: dict[str, Any]) -> Any:
    return d._get("/profiles")


def _list_voices(d: ToolDispatcher, args: dict[str, Any]) -> Any:
    params: dict[str, Any] = {}
    if args.get("provider"):
        params["provider"] = args["provider"]
    if args.get("language"):
        params["language"] = args["language"]
    if args.get("limit"):
        params["limit"] = int(args["limit"])
    return d._get("/voices", params=params)


def _start_training(d: ToolDispatcher, args: dict[str, Any]) -> Any:
    payload: dict[str, Any] = {}
    if args.get("provider_name"):
        payload["provider_name"] = args["provider_name"]
    return d._post(f"/profiles/{args['profile_id']}/train", payload)


def _training_status(d: ToolDispatcher, args: dict[str, Any]) -> Any:
    return d._get(f"/training/jobs/{args['job_id']}")


def _quality_dashboard(d: ToolDispatcher, args: dict[str, Any]) -> Any:
    return d._get(
        f"/profiles/{args['profile_id']}/quality-dashboard",
        params={"wer_limit": args.get("wer_limit", 50)},
    )


def _recommended_samples(d: ToolDispatcher, args: dict[str, Any]) -> Any:
    return d._get(
        f"/profiles/{args['profile_id']}/recommended-samples",
        params={"count": args.get("count", 10)},
    )


def _render_audiobook(d: ToolDispatcher, args: dict[str, Any]) -> Any:
    return d._post(
        "/audiobook/render",
        {"markdown": args["markdown"], "profile_id": args["profile_id"]},
    )


def _list_providers(d: ToolDispatcher, _args: dict[str, Any]) -> Any:
    return d._get("/providers")


_HANDLERS: dict[str, Any] = {
    "atlas_vox_synthesize": _synthesize,
    "atlas_vox_recommend_voice": _recommend_voice,
    "atlas_vox_list_profiles": _list_profiles,
    "atlas_vox_list_voices": _list_voices,
    "atlas_vox_start_training": _start_training,
    "atlas_vox_training_status": _training_status,
    "atlas_vox_quality_dashboard": _quality_dashboard,
    "atlas_vox_recommended_samples": _recommended_samples,
    "atlas_vox_render_audiobook": _render_audiobook,
    "atlas_vox_list_providers": _list_providers,
}
