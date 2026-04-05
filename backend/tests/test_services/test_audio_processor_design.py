"""Tests for Audio Design Studio functions in audio_processor service.

Covers: trim_audio, concat_audio, apply_gain, convert_format, get_audio_info
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from app.services.audio_processor import (
    apply_gain,
    concat_audio,
    convert_format,
    get_audio_info,
    trim_audio,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_sine_wav(path: Path, duration: float, sample_rate: int = 22050, freq: float = 440.0) -> Path:
    """Write a mono sine-wave WAV to *path* and return it."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio = (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    sf.write(str(path), audio, sample_rate)
    return path


@pytest.fixture
def wav_2s(tmp_path: Path) -> Path:
    """2-second 22050 Hz mono WAV."""
    return _write_sine_wav(tmp_path / "two_seconds.wav", duration=2.0)


@pytest.fixture
def wav_1s(tmp_path: Path) -> Path:
    """1-second 22050 Hz mono WAV."""
    return _write_sine_wav(tmp_path / "one_second.wav", duration=1.0)


@pytest.fixture
def wav_3s(tmp_path: Path) -> Path:
    """3-second 22050 Hz mono WAV (used for concat tests)."""
    return _write_sine_wav(tmp_path / "three_seconds.wav", duration=3.0)


# ---------------------------------------------------------------------------
# trim_audio
# ---------------------------------------------------------------------------


class TestTrimAudio:
    @pytest.mark.asyncio
    async def test_trim_audio_produces_correct_duration(self, wav_2s: Path, tmp_path: Path):
        """Trimming 0.5 s – 1.5 s from a 2 s file should yield ≈ 1 second."""
        out = tmp_path / "trimmed.wav"
        result = await trim_audio(wav_2s, out, start=0.5, end=1.5)

        assert result == out
        assert out.exists()

        data, sr = sf.read(str(out))
        actual_duration = len(data) / sr
        assert abs(actual_duration - 1.0) < 0.05  # within 50 ms

    @pytest.mark.asyncio
    async def test_trim_audio_start_zero(self, wav_2s: Path, tmp_path: Path):
        """start=0 trims only the tail."""
        out = tmp_path / "trimmed_tail.wav"
        await trim_audio(wav_2s, out, start=0.0, end=1.0)

        data, sr = sf.read(str(out))
        assert abs(len(data) / sr - 1.0) < 0.05

    @pytest.mark.asyncio
    async def test_trim_audio_creates_output_file(self, wav_2s: Path, tmp_path: Path):
        """Output file is created even when parent dirs do not yet exist."""
        out = tmp_path / "nested" / "trimmed.wav"
        await trim_audio(wav_2s, out, start=0.0, end=1.0)
        assert out.exists()

    @pytest.mark.asyncio
    async def test_trim_audio_invalid_range_start_greater_than_end(self, wav_2s: Path, tmp_path: Path):
        """start > end must raise ValueError."""
        out = tmp_path / "invalid.wav"
        with pytest.raises(ValueError):
            await trim_audio(wav_2s, out, start=1.5, end=0.5)

    @pytest.mark.asyncio
    async def test_trim_audio_invalid_range_equal_bounds(self, wav_2s: Path, tmp_path: Path):
        """start == end collapses to zero samples and must raise ValueError."""
        out = tmp_path / "zero.wav"
        with pytest.raises(ValueError):
            await trim_audio(wav_2s, out, start=1.0, end=1.0)

    @pytest.mark.asyncio
    async def test_trim_audio_end_beyond_file_duration(self, wav_2s: Path, tmp_path: Path):
        """end beyond file length is clamped — no error."""
        out = tmp_path / "clamped.wav"
        # File is 2 s; ask for 0 – 99 s.  Should succeed and return ≈ 2 s.
        await trim_audio(wav_2s, out, start=0.0, end=99.0)
        data, sr = sf.read(str(out))
        assert abs(len(data) / sr - 2.0) < 0.1


# ---------------------------------------------------------------------------
# concat_audio
# ---------------------------------------------------------------------------


class TestConcatAudio:
    @pytest.mark.asyncio
    async def test_concat_two_files_duration(self, wav_1s: Path, wav_2s: Path, tmp_path: Path):
        """Concatenating 1 s + 2 s should yield ≈ 3 s total."""
        out = tmp_path / "concat.wav"
        result = await concat_audio([wav_1s, wav_2s], out)

        assert result == out
        assert out.exists()

        data, sr = sf.read(str(out))
        assert abs(len(data) / sr - 3.0) < 0.1

    @pytest.mark.asyncio
    async def test_concat_three_files_duration(self, wav_1s: Path, wav_2s: Path, wav_3s: Path, tmp_path: Path):
        """Concatenating 1 s + 2 s + 3 s should yield ≈ 6 s."""
        out = tmp_path / "concat3.wav"
        await concat_audio([wav_1s, wav_2s, wav_3s], out)

        data, sr = sf.read(str(out))
        assert abs(len(data) / sr - 6.0) < 0.15

    @pytest.mark.asyncio
    async def test_concat_with_crossfade_produces_output(self, wav_1s: Path, wav_2s: Path, tmp_path: Path):
        """crossfade_ms > 0 must still produce a valid WAV output."""
        out = tmp_path / "crossfade.wav"
        await concat_audio([wav_1s, wav_2s], out, crossfade_ms=100)
        assert out.exists()

        data, sr = sf.read(str(out))
        # With 100 ms crossfade the total is slightly shorter than 3 s
        assert len(data) > 0
        assert abs(len(data) / sr - 3.0) <= 0.2

    @pytest.mark.asyncio
    async def test_concat_with_zero_crossfade(self, wav_1s: Path, wav_2s: Path, tmp_path: Path):
        """crossfade_ms=0 is the default; result equals simple concatenation."""
        out_cf0 = tmp_path / "cf0.wav"
        out_default = tmp_path / "default.wav"

        await concat_audio([wav_1s, wav_2s], out_cf0, crossfade_ms=0)
        await concat_audio([wav_1s, wav_2s], out_default)

        d1, _ = sf.read(str(out_cf0))
        d2, _ = sf.read(str(out_default))
        np.testing.assert_array_equal(d1, d2)

    @pytest.mark.asyncio
    async def test_concat_creates_parent_dirs(self, wav_1s: Path, wav_2s: Path, tmp_path: Path):
        out = tmp_path / "sub" / "dir" / "concat.wav"
        await concat_audio([wav_1s, wav_2s], out)
        assert out.exists()

    @pytest.mark.asyncio
    async def test_concat_single_file_raises(self, wav_1s: Path, tmp_path: Path):
        """Fewer than two files raises ValueError (nothing to concatenate meaningfully)."""
        out = tmp_path / "single.wav"
        # _concat_sync raises ValueError when there are no segments — an empty
        # list triggers the guard; a single-element list succeeds technically
        # (it's just a copy), but the schema validates min_length=2 at the API
        # layer.  We test the empty-list edge case for the service directly.
        with pytest.raises(ValueError):
            await concat_audio([], out)


# ---------------------------------------------------------------------------
# apply_gain
# ---------------------------------------------------------------------------


class TestApplyGain:
    @pytest.mark.asyncio
    async def test_apply_positive_gain_output_exists(self, wav_2s: Path, tmp_path: Path):
        """Positive gain produces a valid WAV file."""
        out = tmp_path / "louder.wav"
        result = await apply_gain(wav_2s, out, gain_db=6.0)

        assert result == out
        assert out.exists()

    @pytest.mark.asyncio
    async def test_apply_negative_gain_output_exists(self, wav_2s: Path, tmp_path: Path):
        """Negative gain (attenuation) produces a valid WAV file."""
        out = tmp_path / "quieter.wav"
        await apply_gain(wav_2s, out, gain_db=-6.0)
        assert out.exists()

    @pytest.mark.asyncio
    async def test_apply_zero_gain_matches_input(self, wav_2s: Path, tmp_path: Path):
        """0 dB gain must not change the audio signal (within float rounding)."""
        out = tmp_path / "unity.wav"
        await apply_gain(wav_2s, out, gain_db=0.0)

        original, _ = sf.read(str(wav_2s))
        processed, _ = sf.read(str(out))

        # Allow small differences due to float32 → PCM_16 quantisation round-trip
        assert np.max(np.abs(original - processed)) < 0.01

    @pytest.mark.asyncio
    async def test_apply_large_gain_clips_to_unity(self, wav_2s: Path, tmp_path: Path):
        """Very large positive gain clips to ±1.0 — output amplitude must not exceed 1."""
        out = tmp_path / "clipped.wav"
        await apply_gain(wav_2s, out, gain_db=60.0)

        data, _ = sf.read(str(out))
        # PCM_16 round-trip: values should sit in [-1, 1]
        assert np.max(np.abs(data)) <= 1.0 + 1e-4

    @pytest.mark.asyncio
    async def test_apply_gain_creates_parent_dirs(self, wav_2s: Path, tmp_path: Path):
        out = tmp_path / "deep" / "path" / "gain.wav"
        await apply_gain(wav_2s, out, gain_db=3.0)
        assert out.exists()


# ---------------------------------------------------------------------------
# convert_format
# ---------------------------------------------------------------------------


class TestConvertFormat:
    @pytest.mark.asyncio
    async def test_convert_wav_to_wav(self, wav_2s: Path, tmp_path: Path):
        """WAV → WAV round-trip produces a valid file."""
        out = tmp_path / "converted.wav"
        result = await convert_format(wav_2s, out, target_format="wav")

        assert result.exists()
        assert result.suffix == ".wav"

    @pytest.mark.asyncio
    async def test_convert_wav_to_ogg(self, wav_2s: Path, tmp_path: Path):
        """WAV → OGG conversion writes an .ogg file."""
        out = tmp_path / "converted.ogg"
        result = await convert_format(wav_2s, out, target_format="ogg")

        assert result.exists()
        assert result.suffix == ".ogg"

    @pytest.mark.asyncio
    async def test_convert_wav_to_flac(self, wav_2s: Path, tmp_path: Path):
        """WAV → FLAC conversion writes a .flac file."""
        out = tmp_path / "converted.flac"
        result = await convert_format(wav_2s, out, target_format="flac")

        assert result.exists()
        assert result.suffix == ".flac"

    @pytest.mark.asyncio
    async def test_convert_with_sample_rate(self, wav_2s: Path, tmp_path: Path):
        """Converting with an explicit target_sr resamples the audio."""
        out = tmp_path / "resampled.wav"
        result = await convert_format(wav_2s, out, target_format="wav", target_sr=16000)

        assert result.exists()
        # pydub writes the correct frame rate; verify via soundfile
        data, sr = sf.read(str(result))
        assert sr == 16000

    @pytest.mark.asyncio
    async def test_convert_creates_parent_dirs(self, wav_2s: Path, tmp_path: Path):
        out = tmp_path / "nested" / "converted.wav"
        result = await convert_format(wav_2s, out, target_format="wav")
        assert result.exists()

    @pytest.mark.asyncio
    async def test_convert_unknown_format_falls_back_to_wav(self, wav_2s: Path, tmp_path: Path):
        """An unrecognised format string falls back to wav in the format_map."""
        out = tmp_path / "fallback.xyz"
        result = await convert_format(wav_2s, out, target_format="xyz")
        # The function writes .wav when the key is not in the map
        assert result.exists()
        assert result.suffix == ".wav"


# ---------------------------------------------------------------------------
# get_audio_info
# ---------------------------------------------------------------------------


class TestGetAudioInfo:
    @pytest.mark.asyncio
    async def test_get_audio_info_returns_expected_keys(self, wav_2s: Path):
        info = await get_audio_info(wav_2s)

        assert "duration_seconds" in info
        assert "sample_rate" in info
        assert "channels" in info
        assert "format" in info
        assert "file_size_bytes" in info

    @pytest.mark.asyncio
    async def test_get_audio_info_duration(self, wav_2s: Path):
        """Reported duration must be close to the actual 2-second file length."""
        info = await get_audio_info(wav_2s)
        assert abs(info["duration_seconds"] - 2.0) < 0.05

    @pytest.mark.asyncio
    async def test_get_audio_info_sample_rate(self, wav_2s: Path):
        """Reported sample rate matches what was written."""
        info = await get_audio_info(wav_2s)
        assert info["sample_rate"] == 22050

    @pytest.mark.asyncio
    async def test_get_audio_info_channels_is_mono(self, wav_2s: Path):
        """librosa loads as mono; channels should be 1."""
        info = await get_audio_info(wav_2s)
        assert info["channels"] == 1

    @pytest.mark.asyncio
    async def test_get_audio_info_format_matches_extension(self, wav_2s: Path):
        """Format field must equal the file's lowercase extension."""
        info = await get_audio_info(wav_2s)
        assert info["format"] == "wav"

    @pytest.mark.asyncio
    async def test_get_audio_info_file_size_positive(self, wav_2s: Path):
        """file_size_bytes must be a positive integer."""
        info = await get_audio_info(wav_2s)
        assert isinstance(info["file_size_bytes"], int)
        assert info["file_size_bytes"] > 0

    @pytest.mark.asyncio
    async def test_get_audio_info_file_size_matches_disk(self, wav_2s: Path):
        """file_size_bytes must equal the actual file size on disk."""
        info = await get_audio_info(wav_2s)
        assert info["file_size_bytes"] == wav_2s.stat().st_size
