"""Tests for /stt endpoints (AP-40).

The whisper backend is expensive to run in CI; these tests mock
``transcribe_detailed`` and ``stream_transcribe`` to verify:

* SSE framing uses ``event: <name>\\ndata: <json>\\n\\n``.
* Word timestamps pass through the response schema.
* Non-streaming endpoint returns the full transcript shape.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.services.whisper_transcriber import (
    TranscriptResult,
    TranscriptSegment,
    WordTimestamp,
)


def _wav_bytes() -> bytes:
    # Minimal WAV header + a tiny silence payload.
    import struct

    sr = 16000
    samples = 800
    body = struct.pack(f"<{samples}h", *([0] * samples))
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(body), b"WAVE",
        b"fmt ", 16, 1, 1, sr, sr * 2, 2, 16,
        b"data", len(body),
    )
    return header + body


@pytest.mark.asyncio
async def test_transcribe_non_streaming_returns_word_timestamps(client: AsyncClient):
    fake = TranscriptResult(
        text="hello world",
        language="en",
        language_probability=0.99,
        segments=[
            TranscriptSegment(
                start=0.0,
                end=1.0,
                text="hello world",
                words=[
                    WordTimestamp(word="hello", start=0.0, end=0.5, probability=0.9),
                    WordTimestamp(word="world", start=0.5, end=1.0, probability=0.8),
                ],
            )
        ],
    )

    with patch(
        "app.services.whisper_transcriber.transcribe_detailed",
        AsyncMock(return_value=fake),
    ):
        files = {"audio": ("in.wav", io.BytesIO(_wav_bytes()), "audio/wav")}
        resp = await client.post("/api/v1/stt/transcribe", files=files)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["text"] == "hello world"
    assert body["language"] == "en"
    assert len(body["segments"]) == 1
    assert len(body["words"]) == 2
    assert body["words"][0]["word"] == "hello"
    assert body["words"][0]["start"] == 0.0
    assert body["words"][1]["probability"] == 0.8


@pytest.mark.asyncio
async def test_transcribe_rejects_empty_payload(client: AsyncClient):
    resp = await client.post(
        "/api/v1/stt/transcribe",
        content=b"",
        headers={"Content-Type": "application/octet-stream"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_transcribe_backend_missing_returns_503(client: AsyncClient):
    with patch(
        "app.services.whisper_transcriber.transcribe_detailed",
        AsyncMock(side_effect=RuntimeError("no whisper installed")),
    ):
        files = {"audio": ("in.wav", io.BytesIO(_wav_bytes()), "audio/wav")}
        resp = await client.post("/api/v1/stt/transcribe", files=files)

    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_stream_endpoint_emits_sse_events(client: AsyncClient):
    async def fake_stream(audio_path: Path, language: str | None = None):
        yield {"type": "language_detected", "language": "en", "probability": 0.98}
        yield {
            "type": "partial",
            "segment": {
                "start": 0.0,
                "end": 0.5,
                "text": "hello",
                "words": [
                    {"word": "hello", "start": 0.0, "end": 0.5, "probability": 0.95}
                ],
            },
        }
        yield {
            "type": "final",
            "text": "hello",
            "language": "en",
            "segments": [
                {
                    "start": 0.0,
                    "end": 0.5,
                    "text": "hello",
                    "words": [
                        {"word": "hello", "start": 0.0, "end": 0.5, "probability": 0.95}
                    ],
                }
            ],
        }

    with patch(
        "app.services.whisper_transcriber.stream_transcribe", fake_stream
    ):
        files = {"audio": ("in.wav", io.BytesIO(_wav_bytes()), "audio/wav")}
        resp = await client.post("/api/v1/stt/stream", files=files)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    body = resp.text
    # SSE framing
    assert "event: language_detected\n" in body
    assert "event: partial\n" in body
    assert "event: final\n" in body
    assert "event: done\n" in body
    # Each event must be followed by a 'data:' line and terminator.
    assert "\ndata: " in body
    assert body.rstrip().endswith("}")  # JSON payload

    # Parse out partial event to verify word timestamp passthrough.
    partial_idx = body.index("event: partial")
    data_start = body.index("data:", partial_idx) + len("data: ")
    data_end = body.index("\n\n", data_start)
    partial_payload = json.loads(body[data_start:data_end])
    assert partial_payload["segment"]["words"][0]["word"] == "hello"


@pytest.mark.asyncio
async def test_stream_endpoint_language_query_passthrough(client: AsyncClient):
    captured: dict = {}

    async def fake_stream(audio_path: Path, language: str | None = None):
        captured["language"] = language
        yield {"type": "final", "text": "", "language": language or "en", "segments": []}

    with patch("app.services.whisper_transcriber.stream_transcribe", fake_stream):
        files = {"audio": ("in.wav", io.BytesIO(_wav_bytes()), "audio/wav")}
        resp = await client.post(
            "/api/v1/stt/stream?language=es", files=files
        )

    assert resp.status_code == 200
    assert captured["language"] == "es"
