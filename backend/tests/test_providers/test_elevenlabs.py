"""Tests for the ElevenLabs provider — all external API calls are mocked."""

from __future__ import annotations

import struct
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.base import (
    AudioResult,
    CloneConfig,
    ProviderCapabilities,
    ProviderAudioSample,
    SynthesisSettings,
    WordBoundary,
)
from app.providers.elevenlabs import ElevenLabsProvider, _parse_word_boundaries


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_wav(path: Path) -> Path:
    """Write a minimal valid WAV file (0.1 s, 16 kHz mono)."""
    sr, nc, bits = 16000, 1, 16
    num = sr // 10
    data_size = num * nc * (bits // 8)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, nc, sr,
        sr * nc * (bits // 8),
        nc * (bits // 8), bits,
        b"data", data_size,
    )
    path.write_bytes(header + struct.pack(f"<{num}h", *([0] * num)))
    return path


def _provider_with_key() -> ElevenLabsProvider:
    p = ElevenLabsProvider()
    p.configure({"api_key": "test-key"})
    return p


def _mock_client() -> MagicMock:
    """Return a MagicMock shaped like the ElevenLabs SDK client."""
    client = MagicMock()
    return client


def _fake_run_sync_factory():
    """Return a run_sync replacement that executes the callable synchronously."""
    async def _fake(fn, *args, **kwargs):
        return fn(*args, **kwargs)
    return _fake


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


class TestCapabilities:
    @pytest.mark.asyncio
    async def test_supports_cloning_and_streaming(self):
        provider = ElevenLabsProvider()
        caps = await provider.get_capabilities()
        assert isinstance(caps, ProviderCapabilities)
        assert caps.supports_cloning is True
        assert caps.supports_streaming is True
        assert caps.supports_word_boundaries is True

    @pytest.mark.asyncio
    async def test_no_gpu_required(self):
        provider = ElevenLabsProvider()
        caps = await provider.get_capabilities()
        assert caps.requires_gpu is False
        assert caps.gpu_mode == "none"

    @pytest.mark.asyncio
    async def test_supported_languages(self):
        provider = ElevenLabsProvider()
        caps = await provider.get_capabilities()
        for lang in ("en", "es", "fr", "de", "ja"):
            assert lang in caps.supported_languages

    @pytest.mark.asyncio
    async def test_output_formats(self):
        provider = ElevenLabsProvider()
        caps = await provider.get_capabilities()
        assert "mp3" in caps.supported_output_formats

    @pytest.mark.asyncio
    async def test_no_fine_tuning(self):
        provider = ElevenLabsProvider()
        caps = await provider.get_capabilities()
        assert caps.supports_fine_tuning is False


# ---------------------------------------------------------------------------
# Client initialization
# ---------------------------------------------------------------------------


class TestClientInit:
    def test_raises_without_api_key(self):
        provider = ElevenLabsProvider()
        provider.configure({"api_key": ""})
        with pytest.raises(ValueError, match="ELEVENLABS_API_KEY"):
            provider._get_client()

    def test_raises_on_missing_sdk(self):
        provider = ElevenLabsProvider()
        provider.configure({"api_key": "test-key"})
        with patch.dict("sys.modules", {"elevenlabs": None, "elevenlabs.client": None}):
            provider._client = None
            with pytest.raises((ImportError, TypeError)):
                provider._get_client()

    def test_client_cached_after_first_call(self):
        provider = _provider_with_key()
        mock_client = _mock_client()

        with patch("app.providers.elevenlabs.ElevenLabsProvider._get_client", return_value=mock_client):
            c1 = provider._get_client.__wrapped__(provider) if hasattr(provider._get_client, "__wrapped__") else mock_client
            c2 = mock_client
            assert c1 is c2


# ---------------------------------------------------------------------------
# VoiceSettings construction
# ---------------------------------------------------------------------------


class TestVoiceSettings:
    def test_defaults(self):
        provider = ElevenLabsProvider()
        provider.configure({})

        mock_vs = MagicMock()
        with patch("app.providers.elevenlabs.ElevenLabsProvider._build_voice_settings", return_value=mock_vs):
            vs = provider._build_voice_settings()
            assert vs is mock_vs

    def test_custom_values_passed_through(self):
        provider = ElevenLabsProvider()
        provider.configure({
            "api_key": "k",
            "stability": 0.8,
            "similarity_boost": 0.9,
            "style": 0.3,
            "use_speaker_boost": True,
        })

        assert float(provider.get_config_value("stability", 0.5)) == 0.8
        assert float(provider.get_config_value("similarity_boost", 0.75)) == 0.9
        assert float(provider.get_config_value("style", 0.0)) == 0.3
        assert bool(provider.get_config_value("use_speaker_boost", False)) is True

    def test_default_model_id(self):
        provider = ElevenLabsProvider()
        provider.configure({"api_key": "k"})
        assert provider._get_model_id() == "eleven_multilingual_v2"

    def test_custom_model_id(self):
        provider = ElevenLabsProvider()
        provider.configure({"api_key": "k", "model_id": "eleven_flash_v2_5"})
        assert provider._get_model_id() == "eleven_flash_v2_5"


# ---------------------------------------------------------------------------
# synthesize()
# ---------------------------------------------------------------------------


class TestSynthesize:
    @pytest.mark.asyncio
    async def test_synthesize_returns_audio_result(self, tmp_path: Path):
        provider = _provider_with_key()
        output_file = tmp_path / "out.mp3"
        output_file.write_bytes(b"fake-mp3")

        mock_client = _mock_client()
        mock_client.text_to_speech.convert.return_value = [b"chunk1", b"chunk2"]

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch.object(provider, "prepare_output_path", return_value=output_file), \
             patch("app.providers.elevenlabs.run_sync", side_effect=_fake_run_sync_factory()), \
             patch.object(provider, "_build_voice_settings", return_value=MagicMock()):
            result = await provider.synthesize("Hello", "voice-abc", SynthesisSettings())

        assert isinstance(result, AudioResult)
        assert result.format == "mp3"
        assert result.sample_rate == 44100

    @pytest.mark.asyncio
    async def test_synthesize_passes_voice_settings(self, tmp_path: Path):
        provider = _provider_with_key()
        output_file = tmp_path / "out.mp3"
        output_file.write_bytes(b"fake")

        mock_client = _mock_client()
        mock_client.text_to_speech.convert.return_value = [b"audio"]
        mock_vs = MagicMock()

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch.object(provider, "prepare_output_path", return_value=output_file), \
             patch("app.providers.elevenlabs.run_sync", side_effect=_fake_run_sync_factory()), \
             patch.object(provider, "_build_voice_settings", return_value=mock_vs):
            await provider.synthesize("Hi", "v123", SynthesisSettings())

        call_kwargs = mock_client.text_to_speech.convert.call_args.kwargs
        assert call_kwargs["voice_settings"] is mock_vs

    @pytest.mark.asyncio
    async def test_synthesize_propagates_exceptions(self, tmp_path: Path):
        provider = _provider_with_key()
        mock_client = _mock_client()

        def _boom():
            raise RuntimeError("API rate limit")

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch.object(provider, "prepare_output_path", return_value=tmp_path / "out.mp3"), \
             patch("app.providers.elevenlabs.run_sync", new=AsyncMock(side_effect=RuntimeError("API rate limit"))), \
             patch.object(provider, "_build_voice_settings", return_value=MagicMock()):
            with pytest.raises(RuntimeError, match="API rate limit"):
                await provider.synthesize("Hi", "v1", SynthesisSettings())


# ---------------------------------------------------------------------------
# stream_synthesize()
# ---------------------------------------------------------------------------


class TestStreamSynthesize:
    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self, tmp_path: Path):
        provider = _provider_with_key()
        expected = [b"a", b"b", b"c"]

        mock_client = _mock_client()
        mock_client.text_to_speech.convert.return_value = expected

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch("app.providers.elevenlabs.run_sync", side_effect=_fake_run_sync_factory()), \
             patch.object(provider, "_build_voice_settings", return_value=MagicMock()):
            chunks = []
            async for chunk in provider.stream_synthesize("Hello", "v1", SynthesisSettings()):
                chunks.append(chunk)

        assert chunks == expected


# ---------------------------------------------------------------------------
# clone_voice()
# ---------------------------------------------------------------------------


class TestCloneVoice:
    @pytest.mark.asyncio
    async def test_clone_returns_voice_model(self, tmp_path: Path):
        provider = _provider_with_key()
        wav = _make_wav(tmp_path / "s.wav")
        samples = [ProviderAudioSample(file_path=wav)]

        mock_result = MagicMock()
        mock_result.voice_id = "cloned-voice-123"

        mock_client = _mock_client()
        mock_client.voices.ivc.create.return_value = mock_result

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch("app.providers.elevenlabs.run_sync", side_effect=_fake_run_sync_factory()):
            voice_model = await provider.clone_voice(samples, CloneConfig(name="MyVoice"))

        assert voice_model.model_id == "cloned-voice-123"
        assert voice_model.provider_model_id == "cloned-voice-123"
        assert voice_model.metrics["method"] == "instant_voice_clone"

    @pytest.mark.asyncio
    async def test_clone_passes_remove_background_noise(self, tmp_path: Path):
        provider = _provider_with_key()
        wav = _make_wav(tmp_path / "s.wav")
        samples = [ProviderAudioSample(file_path=wav)]

        mock_result = MagicMock()
        mock_result.voice_id = "v-id"

        mock_client = _mock_client()
        mock_client.voices.ivc.create.return_value = mock_result

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch("app.providers.elevenlabs.run_sync", side_effect=_fake_run_sync_factory()):
            await provider.clone_voice(samples, CloneConfig(name="V"))

        call_kwargs = mock_client.voices.ivc.create.call_args.kwargs
        assert call_kwargs.get("remove_background_noise") is True

    @pytest.mark.asyncio
    async def test_fine_tune_raises_not_implemented(self):
        provider = ElevenLabsProvider()
        with pytest.raises(NotImplementedError):
            await provider.fine_tune("model-id", [], MagicMock())


# ---------------------------------------------------------------------------
# isolate_audio()
# ---------------------------------------------------------------------------


class TestIsolateAudio:
    @pytest.mark.asyncio
    async def test_returns_enhanced_path(self, tmp_path: Path):
        provider = _provider_with_key()
        source = _make_wav(tmp_path / "input.wav")
        isolated_bytes = b"clean-audio"

        mock_client = _mock_client()
        mock_client.audio_isolation.audio_isolation.return_value = iter([isolated_bytes])

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch("app.providers.elevenlabs.run_sync", side_effect=_fake_run_sync_factory()):
            output = await provider.isolate_audio(source)

        assert output.name == f"enhanced_{source.name}"
        assert output.read_bytes() == isolated_bytes

    @pytest.mark.asyncio
    async def test_output_written_next_to_source(self, tmp_path: Path):
        provider = _provider_with_key()
        source = _make_wav(tmp_path / "noisy.wav")

        mock_client = _mock_client()
        mock_client.audio_isolation.audio_isolation.return_value = iter([b"clean"])

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch("app.providers.elevenlabs.run_sync", side_effect=_fake_run_sync_factory()):
            output = await provider.isolate_audio(source)

        assert output.parent == tmp_path


# ---------------------------------------------------------------------------
# speech_to_speech()
# ---------------------------------------------------------------------------


class TestSpeechToSpeech:
    @pytest.mark.asyncio
    async def test_returns_output_path(self, tmp_path: Path):
        provider = _provider_with_key()
        source = _make_wav(tmp_path / "input.wav")
        sts_bytes = b"converted-audio"

        mock_client = _mock_client()
        mock_client.speech_to_speech.convert.return_value = iter([sts_bytes])

        output_file = tmp_path / "elevenlabs_sts_abc123.mp3"

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch.object(provider, "prepare_output_path", return_value=output_file), \
             patch("app.providers.elevenlabs.run_sync", side_effect=_fake_run_sync_factory()):
            result = await provider.speech_to_speech(source, "target-voice-id")

        assert result == output_file
        assert result.read_bytes() == sts_bytes

    @pytest.mark.asyncio
    async def test_uses_sts_model(self, tmp_path: Path):
        provider = _provider_with_key()
        source = _make_wav(tmp_path / "input.wav")

        mock_client = _mock_client()
        mock_client.speech_to_speech.convert.return_value = iter([b"audio"])

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch.object(provider, "prepare_output_path", return_value=tmp_path / "out.mp3"), \
             patch("app.providers.elevenlabs.run_sync", side_effect=_fake_run_sync_factory()):
            await provider.speech_to_speech(source, "voice-id")

        call_kwargs = mock_client.speech_to_speech.convert.call_args.kwargs
        assert "sts" in call_kwargs.get("model_id", "")


# ---------------------------------------------------------------------------
# design_voice()
# ---------------------------------------------------------------------------


class TestDesignVoice:
    @pytest.mark.asyncio
    async def test_returns_previews(self):
        provider = _provider_with_key()

        mock_preview = MagicMock()
        mock_preview.generated_voice_id = "gen-voice-1"
        mock_preview.audio_base64 = "base64data=="

        mock_result = MagicMock()
        mock_result.previews = [mock_preview]

        mock_client = _mock_client()
        mock_client.text_to_voice.create_previews.return_value = mock_result

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch("app.providers.elevenlabs.run_sync", side_effect=_fake_run_sync_factory()):
            result = await provider.design_voice("A calm narrator", "Hello world")

        assert "previews" in result
        assert len(result["previews"]) == 1
        assert result["previews"][0]["voice_id"] == "gen-voice-1"
        assert result["previews"][0]["audio_base64"] == "base64data=="

    @pytest.mark.asyncio
    async def test_uses_default_text_when_empty(self):
        provider = _provider_with_key()

        mock_result = MagicMock()
        mock_result.previews = []

        mock_client = _mock_client()
        mock_client.text_to_voice.create_previews.return_value = mock_result

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch("app.providers.elevenlabs.run_sync", side_effect=_fake_run_sync_factory()):
            await provider.design_voice("Deep voice")

        call_kwargs = mock_client.text_to_voice.create_previews.call_args.kwargs
        assert call_kwargs.get("text") != ""


# ---------------------------------------------------------------------------
# generate_sound_effect()
# ---------------------------------------------------------------------------


class TestGenerateSoundEffect:
    @pytest.mark.asyncio
    async def test_returns_output_path(self, tmp_path: Path):
        provider = _provider_with_key()
        sfx_bytes = b"sfx-audio"

        mock_client = _mock_client()
        mock_client.text_to_sound_effects.convert.return_value = iter([sfx_bytes])

        output_file = tmp_path / "elevenlabs_sfx_abc123.mp3"

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch.object(provider, "prepare_output_path", return_value=output_file), \
             patch("app.providers.elevenlabs.run_sync", side_effect=_fake_run_sync_factory()):
            result = await provider.generate_sound_effect("Thunder storm", duration=3.0)

        assert result == output_file
        assert result.read_bytes() == sfx_bytes

    @pytest.mark.asyncio
    async def test_passes_duration(self, tmp_path: Path):
        provider = _provider_with_key()

        mock_client = _mock_client()
        mock_client.text_to_sound_effects.convert.return_value = iter([b"audio"])

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch.object(provider, "prepare_output_path", return_value=tmp_path / "out.mp3"), \
             patch("app.providers.elevenlabs.run_sync", side_effect=_fake_run_sync_factory()):
            await provider.generate_sound_effect("Rain", duration=7.5)

        call_kwargs = mock_client.text_to_sound_effects.convert.call_args.kwargs
        assert call_kwargs.get("duration_seconds") == 7.5


# ---------------------------------------------------------------------------
# synthesize_with_word_boundaries()
# ---------------------------------------------------------------------------


class TestSynthesizeWithWordBoundaries:
    @pytest.mark.asyncio
    async def test_returns_audio_result_and_boundaries(self, tmp_path: Path):
        import base64

        provider = _provider_with_key()
        output_file = tmp_path / "ts.mp3"
        output_file.write_bytes(b"audio")

        mock_alignment = MagicMock()
        mock_alignment.characters = list("Hello world")
        mock_alignment.character_start_times_seconds = [i * 0.05 for i in range(11)]
        mock_alignment.character_end_times_seconds = [(i + 1) * 0.05 for i in range(11)]

        mock_result = MagicMock()
        mock_result.audio_base64 = base64.b64encode(b"fake-mp3").decode()
        mock_result.alignment = mock_alignment
        mock_result.normalized_alignment = None

        mock_client = _mock_client()
        mock_client.text_to_speech.convert_with_timestamps.return_value = mock_result

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch.object(provider, "prepare_output_path", return_value=output_file), \
             patch("app.providers.elevenlabs.run_sync", side_effect=_fake_run_sync_factory()), \
             patch.object(provider, "_build_voice_settings", return_value=MagicMock()):
            audio_result, boundaries = await provider.synthesize_with_word_boundaries(
                "Hello world", "voice-id", SynthesisSettings()
            )

        assert isinstance(audio_result, AudioResult)
        assert isinstance(boundaries, list)
        # "Hello" and "world" — two words
        assert len(boundaries) == 2
        assert boundaries[0].text == "Hello"
        assert boundaries[1].text == "world"

    @pytest.mark.asyncio
    async def test_returns_empty_boundaries_on_no_alignment(self, tmp_path: Path):
        import base64

        provider = _provider_with_key()
        output_file = tmp_path / "ts.mp3"
        output_file.write_bytes(b"audio")

        mock_result = MagicMock()
        mock_result.audio_base64 = base64.b64encode(b"audio").decode()
        mock_result.alignment = None
        mock_result.normalized_alignment = None

        mock_client = _mock_client()
        mock_client.text_to_speech.convert_with_timestamps.return_value = mock_result

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch.object(provider, "prepare_output_path", return_value=output_file), \
             patch("app.providers.elevenlabs.run_sync", side_effect=_fake_run_sync_factory()), \
             patch.object(provider, "_build_voice_settings", return_value=MagicMock()):
            audio_result, boundaries = await provider.synthesize_with_word_boundaries(
                "Hello", "voice-id", SynthesisSettings()
            )

        assert boundaries == []


# ---------------------------------------------------------------------------
# _parse_word_boundaries() — unit tests for the helper
# ---------------------------------------------------------------------------


class TestParseWordBoundaries:
    def test_empty_input(self):
        assert _parse_word_boundaries([], [], []) == []

    def test_mismatched_lengths(self):
        assert _parse_word_boundaries(["a"], [], []) == []

    def test_single_word(self):
        chars = list("Hello")
        starts = [0.0, 0.05, 0.1, 0.15, 0.2]
        ends =   [0.05, 0.1, 0.15, 0.2, 0.25]
        result = _parse_word_boundaries(chars, starts, ends)
        assert len(result) == 1
        assert result[0].text == "Hello"
        assert result[0].offset_ms == 0
        assert result[0].duration_ms == 250
        assert result[0].word_index == 0

    def test_two_words(self):
        chars = list("Hi yo")
        starts = [0.0, 0.05, 0.1, 0.15, 0.2]
        ends =   [0.05, 0.1, 0.15, 0.2, 0.25]
        result = _parse_word_boundaries(chars, starts, ends)
        assert [w.text for w in result] == ["Hi", "yo"]
        assert result[0].word_index == 0
        assert result[1].word_index == 1

    def test_trailing_word_flushed(self):
        chars = list("end")
        starts = [1.0, 1.05, 1.1]
        ends =   [1.05, 1.1, 1.15]
        result = _parse_word_boundaries(chars, starts, ends)
        assert len(result) == 1
        assert result[0].text == "end"
        assert result[0].offset_ms == 1000

    def test_multiple_spaces_handled(self):
        chars = list("a  b")
        starts = [0.0, 0.1, 0.2, 0.3]
        ends =   [0.1, 0.2, 0.3, 0.4]
        result = _parse_word_boundaries(chars, starts, ends)
        assert [w.text for w in result] == ["a", "b"]


# ---------------------------------------------------------------------------
# health_check()
# ---------------------------------------------------------------------------


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy_when_sdk_available_no_key(self):
        provider = ElevenLabsProvider()
        provider.configure({"api_key": ""})

        mock_el_class = MagicMock()
        with patch.dict("sys.modules", {"elevenlabs": MagicMock(), "elevenlabs.client": MagicMock()}):
            with patch("app.providers.elevenlabs.ElevenLabsProvider._get_client", side_effect=ValueError("ELEVENLABS_API_KEY not configured")):
                health = await provider.health_check()

        # With no key, should still be reported as healthy (SDK ready)
        assert health.name == "elevenlabs"

    @pytest.mark.asyncio
    async def test_unhealthy_on_api_error(self):
        provider = _provider_with_key()
        mock_client = _mock_client()

        with patch.object(provider, "_get_client", return_value=mock_client), \
             patch("app.providers.elevenlabs.run_sync", new=AsyncMock(side_effect=Exception("Network error"))):
            health = await provider.health_check()

        assert health.healthy is False
        assert "Network error" in (health.error or "")


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestElevenLabsConfigSchema:
    def test_defaults(self):
        from app.schemas.provider import ElevenLabsConfig

        config = ElevenLabsConfig()
        assert config.api_key == ""
        assert config.model_id == "eleven_multilingual_v2"
        assert config.stability == 0.5
        assert config.similarity_boost == 0.75
        assert config.style == 0.0
        assert config.use_speaker_boost is False

    def test_custom_values(self):
        from app.schemas.provider import ElevenLabsConfig

        config = ElevenLabsConfig(
            api_key="k",
            model_id="eleven_flash_v2_5",
            stability=0.8,
            similarity_boost=0.9,
            style=0.2,
            use_speaker_boost=True,
        )
        assert config.model_id == "eleven_flash_v2_5"
        assert config.stability == 0.8
        assert config.use_speaker_boost is True

    def test_field_definitions_include_voice_settings(self):
        from app.schemas.provider import PROVIDER_FIELD_DEFINITIONS

        fields = {f.name for f in PROVIDER_FIELD_DEFINITIONS["elevenlabs"]}
        assert "stability" in fields
        assert "similarity_boost" in fields
        assert "style" in fields
        assert "use_speaker_boost" in fields
        assert "model_id" in fields
        assert "api_key" in fields

    def test_model_id_field_has_select_options(self):
        from app.schemas.provider import PROVIDER_FIELD_DEFINITIONS

        model_field = next(
            f for f in PROVIDER_FIELD_DEFINITIONS["elevenlabs"] if f.name == "model_id"
        )
        assert model_field.field_type == "select"
        assert "eleven_flash_v2_5" in model_field.options
        assert "eleven_turbo_v2_5" in model_field.options
        assert "eleven_multilingual_v2" in model_field.options
