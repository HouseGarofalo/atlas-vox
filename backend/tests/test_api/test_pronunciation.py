"""Tests for pronunciation lexicon endpoints (VQ-38)."""

from __future__ import annotations

import io
import struct
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.providers.base import AudioResult


BASE = "/api/v1"


@pytest.mark.asyncio
async def test_crud_round_trip(client: AsyncClient):
    # Create
    resp = await client.post(
        f"{BASE}/pronunciations",
        json={"word": "tomato", "ipa": "təˈmeɪtoʊ", "language": "en"},
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["word"] == "tomato"
    assert created["ipa"] == "təˈmeɪtoʊ"
    assert created["stress"] == "primary"  # ˈ detected
    entry_id = created["id"]

    # List & find it
    resp = await client.get(f"{BASE}/pronunciations?q=toma")
    assert resp.status_code == 200
    data = resp.json()
    assert any(e["id"] == entry_id for e in data["entries"])

    # Update
    resp = await client.put(
        f"{BASE}/pronunciations/{entry_id}",
        json={"ipa": "təˈmɑtoʊ"},
    )
    assert resp.status_code == 200
    assert resp.json()["ipa"] == "təˈmɑtoʊ"

    # Delete
    resp = await client.delete(f"{BASE}/pronunciations/{entry_id}")
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get(f"{BASE}/pronunciations?q=tomato")
    assert resp.status_code == 200
    assert not any(e["id"] == entry_id for e in resp.json()["entries"])


@pytest.mark.asyncio
async def test_update_nonexistent_returns_404(client: AsyncClient):
    resp = await client.put(
        f"{BASE}/pronunciations/does-not-exist",
        json={"word": "x"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_404(client: AsyncClient):
    resp = await client.delete(f"{BASE}/pronunciations/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_import_csv(client: AsyncClient):
    csv_body = "word,ipa,language\nhello,həˈloʊ,en\nworld,ˈwɜːld,en\n".encode("utf-8")
    files = {"file": ("lexicon.csv", csv_body, "text/csv")}
    resp = await client.post(f"{BASE}/pronunciations/import", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["imported"] == 2
    assert data["format"] == "csv"

    # Verify entries are visible via search
    resp = await client.get(f"{BASE}/pronunciations?q=hello")
    words = {e["word"] for e in resp.json()["entries"]}
    assert "hello" in words


@pytest.mark.asyncio
async def test_import_pls(client: AsyncClient):
    pls_body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<lexicon version="1.0"\n'
        '    xmlns="http://www.w3.org/2005/01/pronunciation-lexicon"\n'
        '    xml:lang="en" alphabet="ipa">\n'
        '  <lexeme><grapheme>gigabyte</grapheme><phoneme>ˈɡɪɡəbaɪt</phoneme></lexeme>\n'
        '  <lexeme><grapheme>router</grapheme><phoneme>ˈruːtər</phoneme></lexeme>\n'
        '</lexicon>\n'
    ).encode("utf-8")
    files = {"file": ("lex.pls", pls_body, "application/pls+xml")}
    resp = await client.post(f"{BASE}/pronunciations/import", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["imported"] == 2
    assert data["format"] == "pls"

    resp = await client.get(f"{BASE}/pronunciations?q=gigabyte")
    assert any(e["word"] == "gigabyte" for e in resp.json()["entries"])


@pytest.mark.asyncio
async def test_export_csv_and_pls(client: AsyncClient):
    # Seed an entry
    await client.post(
        f"{BASE}/pronunciations",
        json={"word": "atlas", "ipa": "ˈætləs", "language": "en"},
    )

    resp_csv = await client.get(f"{BASE}/pronunciations/export?format=csv")
    assert resp_csv.status_code == 200
    body = resp_csv.text
    assert "word,ipa,language" in body
    assert "atlas" in body

    resp_pls = await client.get(f"{BASE}/pronunciations/export?format=pls")
    assert resp_pls.status_code == 200
    pls_body = resp_pls.text
    assert "<lexicon" in pls_body
    assert "<grapheme>atlas</grapheme>" in pls_body


# ---------------------------------------------------------------------------
# Preview — synthesizes the word via synthesis_service with a real profile.
# ---------------------------------------------------------------------------


def _make_wav() -> Path:
    tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sample_rate, num_channels, bits = 22050, 1, 16
    num_samples = 100
    data_size = num_samples * num_channels * (bits // 8)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, num_channels, sample_rate,
        sample_rate * num_channels * (bits // 8),
        num_channels * (bits // 8), bits,
        b"data", data_size,
    )
    tf.write(header + struct.pack(f"<{num_samples}h", *([0] * num_samples)))
    tf.close()
    return Path(tf.name)


@pytest.mark.asyncio
async def test_preview_returns_audio_url(client: AsyncClient):
    # Create a profile so preview has something to synthesize against.
    resp = await client.post(
        f"{BASE}/profiles",
        json={"name": "Preview Profile", "provider_name": "kokoro", "voice_id": "af_heart"},
    )
    assert resp.status_code == 201, resp.text
    profile_id = resp.json()["id"]

    # Create lexicon entry.
    resp = await client.post(
        f"{BASE}/pronunciations",
        json={"word": "caramel", "ipa": "ˈkærəmɛl", "language": "en",
              "profile_id": profile_id},
    )
    assert resp.status_code == 201, resp.text
    entry_id = resp.json()["id"]

    # Mock the provider so synthesis doesn't require Kokoro weights.
    wav_path = _make_wav()
    audio_result = AudioResult(
        audio_path=wav_path,
        duration_seconds=0.25,
        sample_rate=22050,
        format="wav",
    )
    provider = AsyncMock()
    provider.synthesize = AsyncMock(return_value=audio_result)

    with patch(
        "app.services.synthesis_service.provider_registry.get_provider",
        return_value=provider,
    ):
        resp = await client.post(
            f"{BASE}/pronunciations/{entry_id}/preview",
            json={"profile_id": profile_id},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["word"] == "caramel"
    assert body["audio_url"].startswith("/api/v1/audio/")
