"""Tests for app.services.audiobook_stitcher (AP-41)."""

from __future__ import annotations

import struct
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.base import ProviderCapabilities
from app.schemas.profile import ProfileCreate
from app.services import audiobook_stitcher
from app.services.audiobook_stitcher import parse_markdown, render_audiobook
from app.services.profile_service import create_profile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav_bytes(num_samples: int = 22050, sample_rate: int = 22050) -> bytes:
    num_channels, bits = 1, 16
    data_size = num_samples * num_channels * (bits // 8)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, num_channels, sample_rate,
        sample_rate * num_channels * (bits // 8),
        num_channels * (bits // 8), bits,
        b"data", data_size,
    )
    return header + struct.pack(f"<{num_samples}h", *([0] * num_samples))


def _make_temp_wav() -> Path:
    from app.core.config import settings

    out_dir = Path(settings.storage_path) / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"synth_{uuid.uuid4().hex[:12]}.wav"
    path.write_bytes(_make_wav_bytes())
    return path


async def _make_profile(db, name="AB Profile", provider="kokoro"):
    return await create_profile(
        db, ProfileCreate(name=name, provider_name=provider, voice_id="af_heart")
    )


# ---------------------------------------------------------------------------
# parse_markdown
# ---------------------------------------------------------------------------

class TestParseMarkdown:
    def test_two_h1_headings_two_chapters(self):
        md = "# Chapter One\n\nPara one.\n\n# Chapter Two\n\nPara two."
        chapters = parse_markdown(md)
        assert len(chapters) == 2
        assert chapters[0].title == "Chapter One"
        assert chapters[1].title == "Chapter Two"
        assert chapters[0].paragraphs == ["Para one."]
        assert chapters[1].paragraphs == ["Para two."]

    def test_h2_headings_also_split(self):
        md = "## A\n\nalpha\n\n## B\n\nbeta"
        chapters = parse_markdown(md)
        assert len(chapters) == 2
        assert [c.title for c in chapters] == ["A", "B"]

    def test_content_before_first_heading_preserved(self):
        md = "Intro paragraph.\n\n# First Chapter\n\nBody."
        chapters = parse_markdown(md)
        titles = [c.title for c in chapters]
        assert "First Chapter" in titles
        all_paras = sum(len(c.paragraphs) for c in chapters)
        assert all_paras == 2

    def test_multiple_paragraphs_per_chapter(self):
        md = "# One\n\np1\n\np2\n\np3"
        chapters = parse_markdown(md)
        assert len(chapters) == 1
        assert len(chapters[0].paragraphs) == 3


# ---------------------------------------------------------------------------
# render_audiobook (mocked)
# ---------------------------------------------------------------------------

class TestRenderAudiobook:
    @pytest.mark.asyncio
    async def test_synthesize_called_per_paragraph(self, db_session):
        profile = await _make_profile(db_session)

        mock_synth = AsyncMock()

        def _synth_impl(*args, **kwargs):
            # Each call must return a new wav file path dict.
            wav = _make_temp_wav()
            return {
                "id": uuid.uuid4().hex,
                "audio_url": f"/api/v1/audio/{wav.name}",
                "duration_seconds": 1.0,
                "latency_ms": 10,
                "profile_id": profile.id,
                "provider_name": profile.provider_name,
            }

        mock_synth.side_effect = _synth_impl

        mock_provider = AsyncMock()
        mock_provider.get_capabilities = AsyncMock(
            return_value=ProviderCapabilities(supports_ssml=False)
        )

        # Stub out concat, loudness, mp3 and duration so we don't need ffmpeg.
        fake_output = _make_temp_wav()

        def _fake_concat(paths, crossfade_ms, out_path):
            out_path.write_bytes(_make_wav_bytes())
            return out_path

        def _fake_loudness(audio_path, out_path, target_lufs):
            out_path.write_bytes(_make_wav_bytes())
            return out_path, -16.0, False

        def _fake_mp3(wav_path, mp3_path):
            mp3_path.write_bytes(b"IDv3 fake")
            return mp3_path

        def _fake_duration(path):
            return 2.0

        md = "# Ch One\n\npara A\n\npara B\n\n# Ch Two\n\npara C"

        with patch.object(
            audiobook_stitcher.provider_registry, "get_provider", return_value=mock_provider
        ), patch(
            "app.services.synthesis_service.synthesize", mock_synth
        ), patch(
            "app.services.audiobook_stitcher._concat_with_crossfade_sync",
            _fake_concat,
        ), patch(
            "app.services.audiobook_stitcher._loudness_normalize_sync",
            _fake_loudness,
        ), patch(
            "app.services.audiobook_stitcher._encode_mp3_sync", _fake_mp3
        ), patch(
            "app.services.audiobook_stitcher._duration_seconds_sync", _fake_duration
        ):
            result = await render_audiobook(
                db_session,
                project_id="test-proj",
                markdown=md,
                profile_id=profile.id,
                options={"output_format": "mp3"},
            )

        assert mock_synth.call_count == 3, "synthesize must be called per paragraph"
        assert result.paragraph_count == 3
        assert len(result.chapter_markers) == 2
        assert result.output_path.suffix == ".mp3"
        assert result.duration_seconds == 2.0

    @pytest.mark.asyncio
    async def test_crossfade_and_loudness_invoked(self, db_session):
        profile = await _make_profile(db_session)

        mock_synth = AsyncMock()
        mock_synth.side_effect = lambda *a, **kw: {
            "id": uuid.uuid4().hex,
            "audio_url": f"/api/v1/audio/{_make_temp_wav().name}",
            "duration_seconds": 0.5,
            "latency_ms": 5,
            "profile_id": profile.id,
            "provider_name": profile.provider_name,
        }

        mock_provider = AsyncMock()
        mock_provider.get_capabilities = AsyncMock(
            return_value=ProviderCapabilities(supports_ssml=True)
        )

        concat_mock = MagicMock(side_effect=lambda paths, xf, out: (out.write_bytes(_make_wav_bytes()), out)[1])
        loud_mock = MagicMock(
            side_effect=lambda src, out, lufs: (
                out.write_bytes(_make_wav_bytes()),
                (out, -15.3, False),
            )[1]
        )
        mp3_mock = MagicMock(side_effect=lambda wav, mp3: (mp3.write_bytes(b"x"), mp3)[1])

        with patch.object(
            audiobook_stitcher.provider_registry, "get_provider", return_value=mock_provider
        ), patch("app.services.synthesis_service.synthesize", mock_synth), patch(
            "app.services.audiobook_stitcher._concat_with_crossfade_sync", concat_mock
        ), patch(
            "app.services.audiobook_stitcher._loudness_normalize_sync", loud_mock
        ), patch(
            "app.services.audiobook_stitcher._encode_mp3_sync", mp3_mock
        ), patch(
            "app.services.audiobook_stitcher._duration_seconds_sync", MagicMock(return_value=1.0)
        ):
            result = await render_audiobook(
                db_session,
                project_id=None,
                markdown="# Only\n\nOnly paragraph here.",
                profile_id=profile.id,
                options={"crossfade_ms": 250, "target_lufs": -16.0},
            )

        concat_mock.assert_called_once()
        loud_mock.assert_called_once()
        mp3_mock.assert_called_once()

        # Crossfade value passed through
        _, cf_arg, _ = concat_mock.call_args[0]
        assert cf_arg == 250

        # Target LUFS passed through
        _, _, lufs_arg = loud_mock.call_args[0]
        assert lufs_arg == -16.0

        assert result.loudness_lufs == -15.3
        assert result.loudness_fallback is False

    @pytest.mark.asyncio
    async def test_empty_markdown_rejected(self, db_session):
        profile = await _make_profile(db_session)

        mock_provider = AsyncMock()
        mock_provider.get_capabilities = AsyncMock(
            return_value=ProviderCapabilities(supports_ssml=False)
        )

        with patch.object(
            audiobook_stitcher.provider_registry, "get_provider", return_value=mock_provider
        ):
            with pytest.raises(ValueError):
                await render_audiobook(
                    db_session,
                    project_id=None,
                    markdown="   \n\n",
                    profile_id=profile.id,
                )
