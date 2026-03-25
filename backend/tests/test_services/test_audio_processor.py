"""Tests for audio processor service."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from app.services.audio_processor import (
    AudioAnalysis,
    PreprocessConfig,
    analyze_audio,
    preprocess_audio,
)


@pytest.fixture
def sample_wav(tmp_path: Path) -> Path:
    """Create a simple test WAV file."""
    sr = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Generate a 440 Hz sine wave
    audio = 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
    path = tmp_path / "test.wav"
    sf.write(str(path), audio, sr)
    return path


@pytest.fixture
def empty_wav(tmp_path: Path) -> Path:
    """Create an empty WAV file."""
    path = tmp_path / "empty.wav"
    sf.write(str(path), np.array([], dtype=np.float32), 16000)
    return path


class TestPreprocessAudio:
    @pytest.mark.asyncio
    async def test_preprocess_resamples(self, sample_wav: Path, tmp_path: Path):
        output = tmp_path / "out.wav"
        config = PreprocessConfig(target_sample_rate=16000)
        result = await preprocess_audio(sample_wav, output, config)

        assert result == output
        assert output.exists()

        data, sr = sf.read(str(output))
        assert sr == 16000

    @pytest.mark.asyncio
    async def test_preprocess_normalizes(self, sample_wav: Path, tmp_path: Path):
        output = tmp_path / "out.wav"
        config = PreprocessConfig(normalize=True, target_sample_rate=16000)
        await preprocess_audio(sample_wav, output, config)

        data, _ = sf.read(str(output))
        peak = np.max(np.abs(data))
        assert peak > 0.9  # Should be close to 1.0 after normalization

    @pytest.mark.asyncio
    async def test_preprocess_empty_raises(self, empty_wav: Path, tmp_path: Path):
        output = tmp_path / "out.wav"
        with pytest.raises(ValueError, match="empty"):
            await preprocess_audio(empty_wav, output)

    @pytest.mark.asyncio
    async def test_preprocess_creates_parent_dirs(self, sample_wav: Path, tmp_path: Path):
        output = tmp_path / "nested" / "dir" / "out.wav"
        await preprocess_audio(sample_wav, output)
        assert output.exists()


class TestAnalyzeAudio:
    @pytest.mark.asyncio
    async def test_analyze_returns_metrics(self, sample_wav: Path):
        analysis = await analyze_audio(sample_wav)

        assert isinstance(analysis, AudioAnalysis)
        assert analysis.duration_seconds > 0
        assert analysis.sample_rate > 0
        assert analysis.pitch_mean is not None
        assert analysis.energy_mean is not None
        assert analysis.spectral_centroid_mean is not None

    @pytest.mark.asyncio
    async def test_analyze_empty(self, empty_wav: Path):
        analysis = await analyze_audio(empty_wav)
        assert analysis.duration_seconds == 0.0

    @pytest.mark.asyncio
    async def test_analyze_to_json(self, sample_wav: Path):
        analysis = await analyze_audio(sample_wav)
        json_str = analysis.to_json()
        import json
        data = json.loads(json_str)
        assert "duration_seconds" in data
        assert "pitch_mean" in data
