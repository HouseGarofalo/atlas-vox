"""Tests for Kokoro TTS provider — CPU-only, 54 built-in voices."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.providers.base import (
    ProviderCapabilities,
    ProviderHealth,
    SynthesisSettings,
    VoiceInfo,
)
from app.providers.kokoro_tts import KokoroTTSProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_pipeline():
    """Build a mock KPipeline that yields a single audio chunk."""
    mock_pipe = MagicMock()
    # KPipeline.__call__ returns an iterator of (grapheme_str, phoneme_str, audio_ndarray)
    sample_audio = np.zeros(24000, dtype=np.float32)  # 1 second of silence at 24 kHz
    mock_pipe.return_value = iter([("hello", "hɛloʊ", sample_audio)])
    return mock_pipe


def _provider_with_pipeline(mock_pipe=None):
    """Return a KokoroTTSProvider with a pre-injected mock pipeline."""
    provider = KokoroTTSProvider()
    provider._pipeline = mock_pipe or _mock_pipeline()
    return provider


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy_when_pipeline_loads(self):
        """health_check returns healthy=True when the kokoro pipeline loads successfully."""
        mock_pipe = _mock_pipeline()
        mock_kpipeline_cls = MagicMock(return_value=mock_pipe)

        provider = KokoroTTSProvider()

        with patch.dict("sys.modules", {"kokoro": MagicMock(KPipeline=mock_kpipeline_cls)}):
            result = await provider.health_check()

        assert isinstance(result, ProviderHealth)
        assert result.name == "kokoro"
        assert result.healthy is True
        assert result.error is None
        assert result.latency_ms is not None

    @pytest.mark.asyncio
    async def test_unhealthy_when_import_fails(self):
        """health_check returns healthy=False when kokoro is not installed."""
        provider = KokoroTTSProvider()

        # Make _get_pipeline raise ImportError
        with patch.object(provider, "_get_pipeline", side_effect=ImportError("No module named 'kokoro'")):
            result = await provider.health_check()

        assert isinstance(result, ProviderHealth)
        assert result.name == "kokoro"
        assert result.healthy is False
        assert "kokoro" in result.error.lower()

    @pytest.mark.asyncio
    async def test_healthy_with_cached_pipeline(self):
        """health_check returns healthy=True when pipeline was already loaded."""
        provider = _provider_with_pipeline()

        result = await provider.health_check()

        assert result.healthy is True
        assert result.latency_ms is not None


# ---------------------------------------------------------------------------
# List Voices
# ---------------------------------------------------------------------------

class TestListVoices:
    @pytest.mark.asyncio
    async def test_returns_54_voices(self):
        """list_voices returns exactly 54 built-in Kokoro voices."""
        provider = KokoroTTSProvider()
        voices = await provider.list_voices()
        assert len(voices) == 54

    @pytest.mark.asyncio
    async def test_voices_are_voice_info_instances(self):
        """Each voice is a VoiceInfo dataclass."""
        provider = KokoroTTSProvider()
        voices = await provider.list_voices()
        for voice in voices:
            assert isinstance(voice, VoiceInfo)

    @pytest.mark.asyncio
    async def test_voice_ids_follow_naming_convention(self):
        """Voice IDs follow the Kokoro naming convention: {lang_prefix}{gender}_{name}."""
        provider = KokoroTTSProvider()
        voices = await provider.list_voices()
        for voice in voices:
            # Every voice_id should have at least one underscore (prefix_name)
            assert "_" in voice.voice_id, f"Voice ID {voice.voice_id} missing underscore separator"

    @pytest.mark.asyncio
    async def test_american_english_voices_present(self):
        """Includes American English voices (af_ and am_ prefixes)."""
        provider = KokoroTTSProvider()
        voices = await provider.list_voices()
        af_voices = [v for v in voices if v.voice_id.startswith("af_")]
        am_voices = [v for v in voices if v.voice_id.startswith("am_")]
        assert len(af_voices) == 11  # 11 American Female voices
        assert len(am_voices) == 9   # 9 American Male voices

    @pytest.mark.asyncio
    async def test_multilingual_coverage(self):
        """Voices span all 9 supported languages."""
        provider = KokoroTTSProvider()
        voices = await provider.list_voices()
        languages = {v.language for v in voices}
        expected = {"en", "ja", "zh", "es", "fr", "hi", "it", "pt"}
        assert languages == expected

    @pytest.mark.asyncio
    async def test_voices_have_gender(self):
        """Every voice declares Male or Female gender."""
        provider = KokoroTTSProvider()
        voices = await provider.list_voices()
        for voice in voices:
            assert voice.gender in ("Male", "Female"), f"Voice {voice.voice_id} has unexpected gender: {voice.gender}"

    @pytest.mark.asyncio
    async def test_voices_are_cached_on_second_call(self):
        """Calling list_voices twice returns the same cached list."""
        provider = KokoroTTSProvider()
        first = await provider.list_voices()
        second = await provider.list_voices()
        assert first is second  # Same object reference (cached)

    @pytest.mark.asyncio
    async def test_default_voice_heart_exists(self):
        """The default 'af_heart' voice (Heart, American Female) exists."""
        provider = KokoroTTSProvider()
        voices = await provider.list_voices()
        heart = [v for v in voices if v.voice_id == "af_heart"]
        assert len(heart) == 1
        assert heart[0].name == "Heart (American Female)"
        assert heart[0].language == "en"
        assert heart[0].gender == "Female"


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

class TestCapabilities:
    @pytest.mark.asyncio
    async def test_requires_no_gpu(self):
        """Kokoro runs on CPU only — requires_gpu must be False."""
        provider = KokoroTTSProvider()
        caps = await provider.get_capabilities()
        assert isinstance(caps, ProviderCapabilities)
        assert caps.requires_gpu is False
        assert caps.gpu_mode == "none"

    @pytest.mark.asyncio
    async def test_no_cloning_or_finetuning(self):
        """Kokoro does not support cloning or fine-tuning."""
        provider = KokoroTTSProvider()
        caps = await provider.get_capabilities()
        assert caps.supports_cloning is False
        assert caps.supports_fine_tuning is False
        assert caps.min_samples_for_cloning == 0

    @pytest.mark.asyncio
    async def test_supports_streaming_and_batch(self):
        """Kokoro supports streaming and batch synthesis."""
        provider = KokoroTTSProvider()
        caps = await provider.get_capabilities()
        assert caps.supports_streaming is True
        assert caps.supports_batch is True

    @pytest.mark.asyncio
    async def test_no_ssml_or_zero_shot(self):
        """Kokoro does not support SSML input or zero-shot cloning."""
        provider = KokoroTTSProvider()
        caps = await provider.get_capabilities()
        assert caps.supports_ssml is False
        assert caps.supports_zero_shot is False

    @pytest.mark.asyncio
    async def test_supported_languages(self):
        """Kokoro supports 8 languages."""
        provider = KokoroTTSProvider()
        caps = await provider.get_capabilities()
        assert len(caps.supported_languages) == 8
        for lang in ("en", "ja", "zh", "es", "fr", "hi", "it", "pt"):
            assert lang in caps.supported_languages

    @pytest.mark.asyncio
    async def test_output_format_wav(self):
        """Kokoro outputs WAV only."""
        provider = KokoroTTSProvider()
        caps = await provider.get_capabilities()
        assert caps.supported_output_formats == ["wav"]

    @pytest.mark.asyncio
    async def test_max_text_length(self):
        """Kokoro advertises a 5000-character max text length."""
        provider = KokoroTTSProvider()
        caps = await provider.get_capabilities()
        assert caps.max_text_length == 5000


# ---------------------------------------------------------------------------
# Synthesize
# ---------------------------------------------------------------------------

class TestSynthesize:
    @pytest.mark.asyncio
    async def test_synthesize_produces_audio_file(self, tmp_path: Path):
        """synthesize creates a WAV file and returns an AudioResult."""
        mock_pipe = _mock_pipeline()
        provider = _provider_with_pipeline(mock_pipe)

        output_file = tmp_path / "kokoro_test_output.wav"

        with patch.object(provider, "prepare_output_path", return_value=output_file), \
             patch("app.providers.kokoro_tts.run_sync") as mock_run_sync:
            # run_sync executes the _synth closure; we call it directly
            async def execute_fn(fn, *a, **kw):
                return fn()

            mock_run_sync.side_effect = execute_fn

            # We need numpy and soundfile available inside _synth
            mock_sf = MagicMock()
            with patch.dict("sys.modules", {"soundfile": mock_sf}):
                result = await provider.synthesize(
                    "Hello world",
                    "af_heart",
                    SynthesisSettings(),
                )

        assert result.audio_path == output_file
        assert result.sample_rate == 24000
        assert result.format == "wav"
        assert result.duration_seconds is not None
        assert result.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_synthesize_calls_pipeline_with_voice_and_speed(self, tmp_path: Path):
        """synthesize passes the correct voice_id and speed to the Kokoro pipeline."""
        mock_pipe = _mock_pipeline()
        provider = _provider_with_pipeline(mock_pipe)

        output_file = tmp_path / "kokoro_speed_test.wav"
        settings = SynthesisSettings(speed=1.5)

        with patch.object(provider, "prepare_output_path", return_value=output_file), \
             patch("app.providers.kokoro_tts.run_sync") as mock_run_sync:
            async def execute_fn(fn, *a, **kw):
                return fn()

            mock_run_sync.side_effect = execute_fn

            mock_sf = MagicMock()
            with patch.dict("sys.modules", {"soundfile": mock_sf}):
                await provider.synthesize("Test", "am_adam", settings)

        # The pipeline was called with text, voice=voice_id, speed=settings.speed
        mock_pipe.assert_called_once_with("Test", voice="am_adam", speed=1.5)

    @pytest.mark.asyncio
    async def test_synthesize_raises_on_empty_output(self, tmp_path: Path):
        """synthesize raises RuntimeError when Kokoro produces no audio chunks."""
        mock_pipe = MagicMock()
        mock_pipe.return_value = iter([])  # No chunks produced
        provider = _provider_with_pipeline(mock_pipe)

        output_file = tmp_path / "kokoro_empty.wav"

        with patch.object(provider, "prepare_output_path", return_value=output_file), \
             patch("app.providers.kokoro_tts.run_sync") as mock_run_sync:
            async def execute_fn(fn, *a, **kw):
                return fn()

            mock_run_sync.side_effect = execute_fn

            with pytest.raises(RuntimeError, match="no audio output"):
                await provider.synthesize("Hello", "af_heart", SynthesisSettings())

    @pytest.mark.asyncio
    async def test_synthesize_concatenates_multiple_chunks(self, tmp_path: Path):
        """synthesize concatenates audio from multiple pipeline segments."""
        mock_pipe = MagicMock()
        chunk1 = np.ones(12000, dtype=np.float32)   # 0.5s
        chunk2 = np.ones(12000, dtype=np.float32)   # 0.5s
        mock_pipe.return_value = iter([
            ("Hello", "hɛloʊ", chunk1),
            ("World", "wɜːrld", chunk2),
        ])
        provider = _provider_with_pipeline(mock_pipe)

        output_file = tmp_path / "kokoro_multi.wav"

        with patch.object(provider, "prepare_output_path", return_value=output_file), \
             patch("app.providers.kokoro_tts.run_sync") as mock_run_sync:
            async def execute_fn(fn, *a, **kw):
                return fn()

            mock_run_sync.side_effect = execute_fn

            mock_sf = MagicMock()
            with patch.dict("sys.modules", {"soundfile": mock_sf}):
                result = await provider.synthesize("Hello World", "af_heart", SynthesisSettings())

        # Duration = 24000 samples / 24000 Hz = 1 second
        assert result.duration_seconds == pytest.approx(1.0)

        # soundfile.write was called with the concatenated array
        sf_write_call = mock_sf.write.call_args
        written_array = sf_write_call[0][1]
        assert len(written_array) == 24000


# ---------------------------------------------------------------------------
# Error Handling — kokoro not installed
# ---------------------------------------------------------------------------

class TestKokoroNotInstalled:
    def test_get_pipeline_raises_import_error(self):
        """_get_pipeline raises ImportError when kokoro is not installed."""
        provider = KokoroTTSProvider()

        with patch.dict("sys.modules", {"kokoro": None}):
            with pytest.raises(ImportError):
                provider._get_pipeline()

    @pytest.mark.asyncio
    async def test_synthesize_fails_when_not_installed(self):
        """synthesize fails cleanly when the kokoro library is missing."""
        provider = KokoroTTSProvider()

        with patch.object(provider, "_get_pipeline", side_effect=ImportError("No module named 'kokoro'")):
            with pytest.raises(ImportError):
                await provider.synthesize("Hello", "af_heart", SynthesisSettings())


# ---------------------------------------------------------------------------
# Clone / Fine-tune — Not Supported
# ---------------------------------------------------------------------------

class TestUnsupportedOperations:
    @pytest.mark.asyncio
    async def test_clone_voice_not_supported(self):
        """clone_voice raises NotImplementedError."""
        provider = KokoroTTSProvider()
        with pytest.raises(NotImplementedError, match="voice cloning"):
            await provider.clone_voice([], MagicMock())

    @pytest.mark.asyncio
    async def test_fine_tune_not_supported(self):
        """fine_tune raises NotImplementedError."""
        provider = KokoroTTSProvider()
        with pytest.raises(NotImplementedError, match="fine-tuning"):
            await provider.fine_tune("model-1", [], MagicMock())
