"""Integration tests for the end-to-end synthesis flow.

Tests the full API pipeline: profile creation → synthesis → history retrieval,
with the TTS provider mocked at the registry level to avoid loading ML models.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.main import app as fastapi_app
from app.providers.base import AudioResult, ProviderCapabilities, SynthesisSettings


# ---------------------------------------------------------------------------
# Fixtures — integration client with raise_app_exceptions=False
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def integration_client(db_session: AsyncSession) -> AsyncClient:
    """HTTPX client that returns HTTP error responses instead of raising exceptions.

    Unlike the default ``client`` fixture (which uses raise_app_exceptions=True),
    this client lets the FastAPI global exception handler convert application
    exceptions into proper HTTP responses (e.g. NotFoundError → 404).
    """
    async def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_audio_path(tmp_path: Path) -> Path:
    """Write a minimal WAV file and return its path."""
    wav_path = tmp_path / f"synth_{uuid.uuid4().hex[:12]}.wav"
    # Minimal valid WAV header (44 bytes) + 100 bytes of silence
    import struct

    num_samples = 100
    sample_rate = 22050
    bits_per_sample = 16
    num_channels = 1
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE",
        b"fmt ", 16, 1,  # PCM
        num_channels, sample_rate, byte_rate, block_align, bits_per_sample,
        b"data", data_size,
    )
    wav_path.write_bytes(header + b"\x00" * data_size)
    return wav_path


def _build_mock_provider(tmp_path: Path) -> MagicMock:
    """Return a MagicMock that behaves like a TTSProvider."""
    provider = MagicMock()

    audio_path = _fake_audio_path(tmp_path)
    fake_result = AudioResult(
        audio_path=audio_path,
        duration_seconds=0.5,
        sample_rate=22050,
        format="wav",
    )

    provider.synthesize = AsyncMock(return_value=fake_result)
    provider.get_capabilities = AsyncMock(
        return_value=ProviderCapabilities(
            supports_streaming=True,
            supports_ssml=False,
            supports_word_boundaries=False,
        )
    )

    async def _fake_stream(text, voice_id, settings):
        yield b"\x00" * 512
        yield b"\x00" * 512

    provider.stream_synthesize = MagicMock(side_effect=_fake_stream)

    return provider


async def _create_profile(client: AsyncClient, provider_name: str = "kokoro") -> dict:
    """Helper: create a voice profile via the API and return the response body."""
    resp = await client.post(
        "/api/v1/profiles",
        json={
            "name": f"Test Voice {uuid.uuid4().hex[:6]}",
            "description": "Integration test profile",
            "language": "en",
            "provider_name": provider_name,
            "voice_id": "test-voice-001",
        },
    )
    assert resp.status_code == 201, f"Profile creation failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_audio_dir(tmp_path: Path) -> Path:
    """Ensure a temp directory exists for fake audio output."""
    audio_dir = tmp_path / "output"
    audio_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def mock_provider(tmp_audio_dir: Path) -> MagicMock:
    """Provide a mock TTS provider for the entire test."""
    return _build_mock_provider(tmp_audio_dir)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_profile_synthesize_and_verify(
    client: AsyncClient, mock_provider: MagicMock
) -> None:
    """Full flow: create a profile → synthesize text → verify response structure."""
    # 1. Create a profile
    profile = await _create_profile(client)
    profile_id = profile["id"]
    assert profile["status"] == "ready"
    assert profile["provider_name"] == "kokoro"

    # 2. Synthesize text with the mocked provider
    with patch(
        "app.services.provider_registry.provider_registry.get_provider",
        return_value=mock_provider,
    ):
        resp = await client.post(
            "/api/v1/synthesize",
            json={
                "text": "Hello, this is an integration test.",
                "profile_id": profile_id,
            },
        )

    assert resp.status_code == 200, f"Synthesis failed: {resp.text}"
    data = resp.json()

    # 3. Verify response shape
    assert "id" in data
    assert "audio_url" in data
    assert data["audio_url"].startswith("/api/v1/audio/")
    assert data["profile_id"] == profile_id
    assert data["provider_name"] == "kokoro"
    assert "latency_ms" in data
    assert isinstance(data["latency_ms"], int)
    assert data["duration_seconds"] == 0.5

    # Verify the provider was called with the right arguments
    mock_provider.synthesize.assert_awaited_once()
    call_args = mock_provider.synthesize.call_args
    assert call_args[0][0] == "Hello, this is an integration test."
    assert call_args[0][1] == "test-voice-001"  # voice_id from profile


@pytest.mark.asyncio
async def test_synthesize_with_invalid_profile_returns_404(
    integration_client: AsyncClient, mock_provider: MagicMock
) -> None:
    """Synthesizing with a non-existent profile_id should return 404."""
    fake_profile_id = str(uuid.uuid4())

    with patch(
        "app.services.provider_registry.provider_registry.get_provider",
        return_value=mock_provider,
    ):
        resp = await integration_client.post(
            "/api/v1/synthesize",
            json={
                "text": "This should fail.",
                "profile_id": fake_profile_id,
            },
        )

    assert resp.status_code == 404
    body = resp.json()
    assert "not found" in body["detail"].lower()


@pytest.mark.asyncio
async def test_synthesize_with_empty_text_returns_422(
    client: AsyncClient,
) -> None:
    """Sending an empty text field should fail Pydantic validation (422)."""
    profile = await _create_profile(client)

    resp = await client.post(
        "/api/v1/synthesize",
        json={
            "text": "",
            "profile_id": profile["id"],
        },
    )

    assert resp.status_code == 422
    body = resp.json()
    # Pydantic v2 validation error structure
    assert "detail" in body


@pytest.mark.asyncio
async def test_synthesize_missing_text_field_returns_422(
    client: AsyncClient,
) -> None:
    """Omitting the text field entirely should return 422."""
    profile = await _create_profile(client)

    resp = await client.post(
        "/api/v1/synthesize",
        json={
            "profile_id": profile["id"],
        },
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_synthesis_history_returns_previous_records(
    client: AsyncClient, mock_provider: MagicMock
) -> None:
    """After synthesizing, GET /synthesis/history should include the record."""
    # 1. Create profile and synthesize
    profile = await _create_profile(client)
    profile_id = profile["id"]

    with patch(
        "app.services.provider_registry.provider_registry.get_provider",
        return_value=mock_provider,
    ):
        synth_resp = await client.post(
            "/api/v1/synthesize",
            json={
                "text": "Record this in history.",
                "profile_id": profile_id,
            },
        )
    assert synth_resp.status_code == 200
    synth_data = synth_resp.json()

    # 2. Fetch history
    history_resp = await client.get("/api/v1/synthesis/history")
    assert history_resp.status_code == 200
    history = history_resp.json()

    assert isinstance(history, list)
    assert len(history) >= 1

    # Find our synthesis record in history
    matching = [h for h in history if h["id"] == synth_data["id"]]
    assert len(matching) == 1

    record = matching[0]
    assert record["profile_id"] == profile_id
    assert record["provider_name"] == "kokoro"
    assert record["text"] == "Record this in history."
    assert record["audio_url"] is not None
    assert "created_at" in record


@pytest.mark.asyncio
async def test_synthesis_history_filtered_by_profile(
    client: AsyncClient, mock_provider: MagicMock
) -> None:
    """History endpoint should support profile_id filter."""
    # Create two profiles
    profile_a = await _create_profile(client)
    profile_b = await _create_profile(client)

    with patch(
        "app.services.provider_registry.provider_registry.get_provider",
        return_value=mock_provider,
    ):
        # Synthesize with profile A
        await client.post(
            "/api/v1/synthesize",
            json={"text": "From profile A.", "profile_id": profile_a["id"]},
        )
        # Synthesize with profile B
        await client.post(
            "/api/v1/synthesize",
            json={"text": "From profile B.", "profile_id": profile_b["id"]},
        )

    # Filter history for profile A only
    resp = await client.get(
        "/api/v1/synthesis/history",
        params={"profile_id": profile_a["id"]},
    )
    assert resp.status_code == 200
    history = resp.json()

    assert all(h["profile_id"] == profile_a["id"] for h in history)
    assert len(history) >= 1


@pytest.mark.asyncio
async def test_stream_synthesis_returns_chunked_audio(
    client: AsyncClient, mock_provider: MagicMock
) -> None:
    """POST /synthesize/stream should return a StreamingResponse with correct headers."""
    profile = await _create_profile(client)

    with patch(
        "app.services.provider_registry.provider_registry.get_provider",
        return_value=mock_provider,
    ):
        resp = await client.post(
            "/api/v1/synthesize/stream",
            json={
                "text": "Stream this audio please.",
                "profile_id": profile["id"],
            },
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("audio/wav")
    assert resp.headers.get("transfer-encoding") == "chunked"

    # Body should contain audio bytes from our mock generator
    assert len(resp.content) > 0


@pytest.mark.asyncio
async def test_synthesize_with_custom_settings(
    client: AsyncClient, mock_provider: MagicMock
) -> None:
    """Synthesis should accept and pass through speed/pitch/volume settings."""
    profile = await _create_profile(client)

    with patch(
        "app.services.provider_registry.provider_registry.get_provider",
        return_value=mock_provider,
    ):
        resp = await client.post(
            "/api/v1/synthesize",
            json={
                "text": "Custom settings test.",
                "profile_id": profile["id"],
                "speed": 1.5,
                "pitch": 5.0,
                "volume": 0.8,
                "output_format": "wav",
            },
        )

    assert resp.status_code == 200

    # Verify the provider received the correct SynthesisSettings
    mock_provider.synthesize.assert_awaited_once()
    call_args = mock_provider.synthesize.call_args
    settings_arg = call_args[0][2]  # Third positional arg: SynthesisSettings
    assert isinstance(settings_arg, SynthesisSettings)
    assert settings_arg.speed == 1.5
    assert settings_arg.pitch == 5.0
    assert settings_arg.volume == 0.8


@pytest.mark.asyncio
async def test_synthesize_blocked_voice_settings_returns_422(
    client: AsyncClient,
) -> None:
    """Sending blocked keys in voice_settings should fail validation (422)."""
    profile = await _create_profile(client)

    resp = await client.post(
        "/api/v1/synthesize",
        json={
            "text": "This has blocked settings.",
            "profile_id": profile["id"],
            "voice_settings": {"api_key": "evil"},
        },
    )

    assert resp.status_code == 422
    body = resp.json()
    assert "detail" in body
