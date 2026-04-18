"""Tests for the inaudible deepfake watermarking service (SC-45)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from app.services.audio_watermark import (
    BIT_REPEAT,
    CARRIER_STRIDE,
    PAYLOAD_LENGTH,
    embed_watermark,
    make_payload,
    verify_watermark,
)


SAMPLE_RATE = 22050
# Long enough to carry the full watermark frame (37 bytes × 8 bits ×
# BIT_REPEAT × CARRIER_STRIDE samples) with room to spare.
DEFAULT_LENGTH = CARRIER_STRIDE * BIT_REPEAT * (PAYLOAD_LENGTH + 5) * 8 + 1000


def _write_signal(path: Path, samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    sf.write(str(path), samples.astype(np.float32), sample_rate)


def _speech_like_signal(length: int = DEFAULT_LENGTH, seed: int = 42) -> np.ndarray:
    """Produce a low-noise, speech-like signal for watermark testing."""
    rng = np.random.default_rng(seed)
    # Sum of a few sinusoids plus a small amount of noise — covers enough
    # frequency content that a watermark has something to modulate.
    t = np.arange(length) / SAMPLE_RATE
    signal = (
        0.3 * np.sin(2 * np.pi * 220 * t)
        + 0.2 * np.sin(2 * np.pi * 440 * t)
        + 0.1 * np.sin(2 * np.pi * 880 * t)
        + 0.01 * rng.standard_normal(length)
    )
    return signal.astype(np.float32)


def test_embed_verify_roundtrip(tmp_path: Path):
    wav = tmp_path / "audio.wav"
    _write_signal(wav, _speech_like_signal())

    payload = "av:profile-abc:history-xyz"
    embed_watermark(wav, payload)

    result = verify_watermark(wav)
    assert result is not None
    assert result["payload"] == payload
    assert result["confidence"] == 1.0


def test_verify_returns_none_for_unwatermarked_silence(tmp_path: Path):
    wav = tmp_path / "silence.wav"
    _write_signal(wav, np.zeros(DEFAULT_LENGTH, dtype=np.float32))
    assert verify_watermark(wav) is None


def test_verify_returns_none_for_fresh_noise(tmp_path: Path):
    """Random noise has no valid magic prefix — verifier must return None."""
    wav = tmp_path / "noise.wav"
    rng = np.random.default_rng(7)
    noise = 0.01 * rng.standard_normal(DEFAULT_LENGTH).astype(np.float32)
    _write_signal(wav, noise)
    assert verify_watermark(wav) is None


def test_watermark_survives_5pct_sample_loss(tmp_path: Path):
    """Zeroing 5% of samples at random should still leave the payload recoverable."""
    wav = tmp_path / "audio.wav"
    _write_signal(wav, _speech_like_signal(length=DEFAULT_LENGTH * 2))

    payload = make_payload("profileABCDEFG", "historyZZZZZZ")
    embed_watermark(wav, payload)

    data, sr = sf.read(str(wav))
    data = np.asarray(data, dtype=np.float32)
    rng = np.random.default_rng(13)
    n_lose = int(len(data) * 0.05)
    lose_idx = rng.choice(len(data), size=n_lose, replace=False)
    data[lose_idx] = 0.0
    sf.write(str(wav), data, sr)

    result = verify_watermark(wav)
    assert result is not None
    assert result["payload"] == payload
    # Some bits will be corrupted, but framing still matches and the
    # recovered confidence should be well above 0.5.
    assert result["confidence"] >= 0.9


def test_embed_raises_when_audio_too_short(tmp_path: Path):
    wav = tmp_path / "short.wav"
    _write_signal(wav, np.zeros(100, dtype=np.float32))
    with pytest.raises(ValueError, match="too short"):
        embed_watermark(wav, "av:x:y")


def test_make_payload_truncates_ids():
    payload = make_payload(
        "profile-" + "x" * 64, "history-" + "y" * 64
    )
    # Must still fit inside PAYLOAD_LENGTH bytes (32).
    assert len(payload.encode("utf-8")) <= PAYLOAD_LENGTH
    assert payload.startswith("av:")


def test_verify_missing_file_returns_none(tmp_path: Path):
    missing = tmp_path / "does-not-exist.wav"
    assert verify_watermark(missing) is None


def test_embed_mono_stereo_downmix(tmp_path: Path):
    """Stereo input should still produce a recoverable watermark."""
    wav = tmp_path / "stereo.wav"
    mono = _speech_like_signal()
    stereo = np.stack([mono, mono * 0.9], axis=-1)
    sf.write(str(wav), stereo.astype(np.float32), SAMPLE_RATE)

    payload = "av:p:h"
    embed_watermark(wav, payload)
    result = verify_watermark(wav)
    assert result is not None
    assert result["payload"] == payload
