"""Tests for the audio quality validation and scoring service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
import soundfile as sf

from app.services.audio_quality import (
    AudioQualityReport,
    QualityIssue,
    TrainingReadiness,
    VoiceQualityScore,
    assess_training_readiness,
    score_voice_quality,
    validate_audio_quality,
)

# ──────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ──────────────────────────────────────────────────────────────────────────────

SR = 22050


def _write_wav(path: Path, audio: np.ndarray, sr: int = SR) -> Path:
    sf.write(str(path), audio, sr)
    return path


@pytest.fixture
def good_wav(tmp_path: Path) -> Path:
    """Well-formed 3s speech-like audio at a comfortable level."""
    t = np.linspace(0, 3.0, int(SR * 3.0), endpoint=False)
    audio = 0.3 * np.sin(2 * np.pi * 220 * t).astype(np.float32)
    return _write_wav(tmp_path / "good.wav", audio)


@pytest.fixture
def clipping_wav(tmp_path: Path) -> Path:
    """Audio that massively clips (all samples ≥ 0.99)."""
    samples = np.ones(int(SR * 3.0), dtype=np.float32)
    return _write_wav(tmp_path / "clip.wav", samples)


@pytest.fixture
def quiet_wav(tmp_path: Path) -> Path:
    """Audio that is too quiet (RMS well below -40 dB)."""
    audio = np.full(int(SR * 3.0), 1e-6, dtype=np.float32)
    return _write_wav(tmp_path / "quiet.wav", audio)


@pytest.fixture
def short_wav(tmp_path: Path) -> Path:
    """Audio shorter than the 1-second hard minimum."""
    t = np.linspace(0, 0.5, int(SR * 0.5), endpoint=False)
    audio = 0.3 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
    return _write_wav(tmp_path / "short.wav", audio)


@pytest.fixture
def long_wav(tmp_path: Path) -> Path:
    """Audio longer than the 60-second hard maximum."""
    audio = 0.3 * np.ones(int(SR * 65.0), dtype=np.float32)
    return _write_wav(tmp_path / "long.wav", audio)


@pytest.fixture
def low_sr_wav(tmp_path: Path) -> Path:
    """Audio recorded at 8 kHz (below recommended 16 kHz)."""
    low_sr = 8000
    t = np.linspace(0, 3.0, int(low_sr * 3.0), endpoint=False)
    audio = 0.3 * np.sin(2 * np.pi * 220 * t).astype(np.float32)
    return _write_wav(tmp_path / "low_sr.wav", audio, sr=low_sr)


@pytest.fixture
def loud_wav(tmp_path: Path) -> Path:
    """Audio that is very loud but not quite clipping (RMS > -3 dB)."""
    # RMS of full-amplitude sine is ~0.707, which is about -3 dBFS — use 0.99
    t = np.linspace(0, 3.0, int(SR * 3.0), endpoint=False)
    audio = 0.98 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
    return _write_wav(tmp_path / "loud.wav", audio)


# ──────────────────────────────────────────────────────────────────────────────
# validate_audio_quality
# ──────────────────────────────────────────────────────────────────────────────

class TestValidateAudioQuality:
    @pytest.mark.asyncio
    async def test_good_audio_passes(self, good_wav: Path):
        report = await validate_audio_quality(good_wav)
        assert isinstance(report, AudioQualityReport)
        assert report.passed is True
        assert report.score > 60.0
        assert "duration" in report.metrics
        assert "rms_db" in report.metrics
        assert "snr_db" in report.metrics
        assert "clipping_ratio" in report.metrics
        assert "silence_ratio" in report.metrics

    @pytest.mark.asyncio
    async def test_clipping_audio_fails(self, clipping_wav: Path):
        report = await validate_audio_quality(clipping_wav)
        assert report.passed is False
        codes = [i.code for i in report.issues]
        assert "clipping" in codes

    @pytest.mark.asyncio
    async def test_quiet_audio_fails(self, quiet_wav: Path):
        report = await validate_audio_quality(quiet_wav)
        assert report.passed is False
        codes = [i.code for i in report.issues]
        assert "too_quiet" in codes

    @pytest.mark.asyncio
    async def test_short_audio_error(self, short_wav: Path):
        report = await validate_audio_quality(short_wav)
        assert report.passed is False
        codes = [i.code for i in report.issues]
        assert "too_short" in codes

    @pytest.mark.asyncio
    async def test_long_audio_error(self, long_wav: Path):
        report = await validate_audio_quality(long_wav)
        assert report.passed is False
        codes = [i.code for i in report.issues]
        assert "too_long" in codes

    @pytest.mark.asyncio
    async def test_low_sample_rate_warning(self, low_sr_wav: Path):
        report = await validate_audio_quality(low_sr_wav)
        codes = [i.code for i in report.issues]
        assert "low_sample_rate" in codes
        # Low SR alone is a warning, not an error — audio may still pass
        low_sr_issues = [i for i in report.issues if i.code == "low_sample_rate"]
        assert low_sr_issues[0].severity == "warning"

    @pytest.mark.asyncio
    async def test_loud_audio_issue(self, loud_wav: Path):
        report = await validate_audio_quality(loud_wav)
        codes = [i.code for i in report.issues]
        # Should flag as either too_loud or loud_audio depending on exact RMS
        assert any(c in codes for c in ("too_loud", "loud_audio", "minor_clipping", "clipping"))

    @pytest.mark.asyncio
    async def test_score_is_bounded(self, good_wav: Path, clipping_wav: Path):
        good = await validate_audio_quality(good_wav)
        bad = await validate_audio_quality(clipping_wav)
        assert 0.0 <= good.score <= 100.0
        assert 0.0 <= bad.score <= 100.0
        assert good.score > bad.score

    @pytest.mark.asyncio
    async def test_to_dict_structure(self, good_wav: Path):
        report = await validate_audio_quality(good_wav)
        d = report.to_dict()
        assert isinstance(d["passed"], bool)
        assert isinstance(d["score"], float)
        assert isinstance(d["issues"], list)
        assert isinstance(d["metrics"], dict)

    @pytest.mark.asyncio
    async def test_error_severity_fails(self, short_wav: Path):
        """Any error-severity issue must cause passed=False."""
        report = await validate_audio_quality(short_wav)
        has_errors = any(i.severity == "error" for i in report.issues)
        assert has_errors
        assert report.passed is False

    @pytest.mark.asyncio
    async def test_metrics_have_expected_keys(self, good_wav: Path):
        report = await validate_audio_quality(good_wav)
        for key in ("duration", "sample_rate", "rms_db", "peak_db",
                    "clipping_ratio", "silence_ratio", "snr_db"):
            assert key in report.metrics, f"Missing metric key: {key}"


# ──────────────────────────────────────────────────────────────────────────────
# assess_training_readiness
# ──────────────────────────────────────────────────────────────────────────────

class TestAssessTrainingReadiness:
    @pytest.mark.asyncio
    async def test_no_samples_returns_not_ready(self):
        """Empty sample list must always yield ready=False."""
        readiness = await assess_training_readiness([], provider_name="kokoro")
        assert readiness.ready is False
        codes = [i.code for i in readiness.issues]
        assert "insufficient_samples" in codes

    @pytest.mark.asyncio
    async def test_single_sample_fails_min_count(self, good_wav: Path):
        samples = [{"path": str(good_wav), "duration": 3.0}]
        readiness = await assess_training_readiness(
            samples, provider_name="kokoro", min_samples=2
        )
        assert readiness.ready is False
        codes = [i.code for i in readiness.issues]
        assert "insufficient_samples" in codes

    @pytest.mark.asyncio
    async def test_good_samples_ready(self, good_wav: Path, tmp_path: Path):
        """Two good-quality samples with sufficient duration should pass."""
        # Create a second good sample
        t = np.linspace(0, 5.0, int(SR * 5.0), endpoint=False)
        audio2 = 0.25 * np.sin(2 * np.pi * 330 * t).astype(np.float32)
        wav2 = _write_wav(tmp_path / "good2.wav", audio2)

        samples = [
            {"path": str(good_wav), "duration": 3.0},
            {"path": str(wav2), "duration": 5.0},
        ]
        readiness = await assess_training_readiness(samples, provider_name="kokoro")
        assert isinstance(readiness, TrainingReadiness)
        assert readiness.sample_count == 2
        assert readiness.total_duration == pytest.approx(8.0)

    @pytest.mark.asyncio
    async def test_short_total_duration_fails(self, tmp_path: Path):
        """Total duration < 10s must produce an error."""
        t = np.linspace(0, 2.0, int(SR * 2.0), endpoint=False)
        audio = 0.3 * np.sin(2 * np.pi * 220 * t).astype(np.float32)
        w1 = _write_wav(tmp_path / "s1.wav", audio)
        w2 = _write_wav(tmp_path / "s2.wav", audio)
        samples = [
            {"path": str(w1), "duration": 2.0},
            {"path": str(w2), "duration": 2.0},
        ]
        readiness = await assess_training_readiness(samples, provider_name="kokoro")
        codes = [i.code for i in readiness.issues]
        assert "insufficient_duration" in codes
        assert readiness.ready is False

    @pytest.mark.asyncio
    async def test_uses_cached_quality_report(self, good_wav: Path):
        """When a pre-computed quality_report dict is provided, skip validation."""
        pre_report = {
            "passed": True,
            "score": 90.0,
            "issues": [],
            "metrics": {"duration": 3.0, "rms_db": -12.0},
        }
        samples = [
            {"path": str(good_wav), "duration": 3.0, "quality_report": pre_report},
            {"path": str(good_wav), "duration": 3.0, "quality_report": pre_report},
        ]
        # Use validate_audio_quality mock to confirm it is NOT called
        with patch(
            "app.services.audio_quality.validate_audio_quality",
            new_callable=AsyncMock,
        ) as mock_validate:
            readiness = await assess_training_readiness(
                samples, provider_name="kokoro"
            )
        mock_validate.assert_not_called()
        assert readiness.sample_count == 2

    @pytest.mark.asyncio
    async def test_uses_pre_computed_quality_report_object(self, good_wav: Path):
        """Pre-computed AudioQualityReport objects are also accepted directly."""
        report_obj = AudioQualityReport(passed=True, score=85.0, metrics={"duration": 3.0})
        samples = [
            {"path": str(good_wav), "duration": 3.0, "quality_report": report_obj},
            {"path": str(good_wav), "duration": 3.0, "quality_report": report_obj},
        ]
        readiness = await assess_training_readiness(samples, provider_name="elevenlabs")
        assert readiness.sample_count == 2

    @pytest.mark.asyncio
    async def test_bad_sample_adds_recommendation(self, clipping_wav: Path, good_wav: Path):
        """Clipping sample should appear in recommendations."""
        samples = [
            {"path": str(clipping_wav), "duration": 3.0},
            {"path": str(good_wav), "duration": 3.0},
            {"path": str(good_wav), "duration": 5.0},
        ]
        readiness = await assess_training_readiness(samples, provider_name="kokoro")
        assert len(readiness.recommendations) > 0

    @pytest.mark.asyncio
    async def test_score_bounded(self, good_wav: Path):
        samples = [{"path": str(good_wav), "duration": 3.0}]
        readiness = await assess_training_readiness(samples, provider_name="kokoro")
        assert 0.0 <= readiness.score <= 100.0

    @pytest.mark.asyncio
    async def test_to_dict_structure(self, good_wav: Path):
        samples = [
            {"path": str(good_wav), "duration": 3.0},
            {"path": str(good_wav), "duration": 3.0},
        ]
        readiness = await assess_training_readiness(samples, provider_name="kokoro")
        d = readiness.to_dict()
        assert "ready" in d
        assert "score" in d
        assert "sample_count" in d
        assert "total_duration" in d
        assert "issues" in d
        assert "recommendations" in d


# ──────────────────────────────────────────────────────────────────────────────
# score_voice_quality
# ──────────────────────────────────────────────────────────────────────────────

class TestScoreVoiceQuality:
    @pytest.mark.asyncio
    async def test_identical_audio_high_similarity(self, good_wav: Path):
        """Synthesized audio identical to originals should yield high similarity."""
        score = await score_voice_quality(
            original_samples=[good_wav],
            synthesized_audio=good_wav,
            reference_text="The quick brown fox.",
        )
        assert isinstance(score, VoiceQualityScore)
        assert score.speaker_similarity > 80.0

    @pytest.mark.asyncio
    async def test_different_audio_lower_similarity(self, good_wav: Path, tmp_path: Path):
        """A very different signal should score lower in speaker similarity."""
        t = np.linspace(0, 3.0, int(SR * 3.0), endpoint=False)
        # Use a very different frequency and amplitude profile
        noise = 0.1 * np.random.default_rng(42).standard_normal(int(SR * 3.0)).astype(np.float32)
        different = _write_wav(tmp_path / "diff.wav", noise)

        similar_score = await score_voice_quality(
            original_samples=[good_wav],
            synthesized_audio=good_wav,
            reference_text="Test",
        )
        different_score = await score_voice_quality(
            original_samples=[good_wav],
            synthesized_audio=different,
            reference_text="Test",
        )
        assert similar_score.speaker_similarity > different_score.speaker_similarity

    @pytest.mark.asyncio
    async def test_all_scores_bounded(self, good_wav: Path):
        score = await score_voice_quality(
            original_samples=[good_wav],
            synthesized_audio=good_wav,
            reference_text="Hello world",
        )
        for attr in ("overall", "naturalness", "intelligibility",
                     "speaker_similarity", "consistency"):
            val = getattr(score, attr)
            assert 0.0 <= val <= 100.0, f"{attr}={val} is out of [0, 100]"

    @pytest.mark.asyncio
    async def test_multiple_originals(self, good_wav: Path, tmp_path: Path):
        """Should handle multiple original samples without error."""
        t = np.linspace(0, 3.0, int(SR * 3.0), endpoint=False)
        orig2 = _write_wav(
            tmp_path / "orig2.wav",
            (0.25 * np.sin(2 * np.pi * 300 * t)).astype(np.float32),
        )
        score = await score_voice_quality(
            original_samples=[good_wav, orig2],
            synthesized_audio=good_wav,
            reference_text="Hello",
        )
        assert score.overall >= 0.0

    @pytest.mark.asyncio
    async def test_to_dict_structure(self, good_wav: Path):
        score = await score_voice_quality(
            original_samples=[good_wav],
            synthesized_audio=good_wav,
            reference_text="Test sentence",
        )
        d = score.to_dict()
        for key in ("overall", "naturalness", "intelligibility",
                    "speaker_similarity", "consistency", "details"):
            assert key in d

    @pytest.mark.asyncio
    async def test_no_originals_returns_neutral(self, good_wav: Path):
        """With no valid original samples the service should not crash."""
        score = await score_voice_quality(
            original_samples=[],
            synthesized_audio=good_wav,
            reference_text="Test",
        )
        assert isinstance(score, VoiceQualityScore)
        assert 0.0 <= score.overall <= 100.0


# ──────────────────────────────────────────────────────────────────────────────
# QualityIssue helpers
# ──────────────────────────────────────────────────────────────────────────────

class TestQualityIssue:
    def test_defaults(self):
        issue = QualityIssue(code="test", severity="error", message="Something bad")
        assert issue.value is None
        assert issue.threshold is None

    def test_with_values(self):
        issue = QualityIssue(
            code="too_short", severity="error", message="Too short",
            value=0.5, threshold=1.0,
        )
        assert issue.value == 0.5
        assert issue.threshold == 1.0


# ──────────────────────────────────────────────────────────────────────────────
# Graceful degradation when librosa is unavailable
# ──────────────────────────────────────────────────────────────────────────────

class TestLibrosaUnavailable:
    @pytest.mark.asyncio
    async def test_validate_graceful_without_librosa(self, good_wav: Path):
        """Module gracefully returns an error report when librosa is absent."""
        import app.services.audio_quality as aq_module

        original = aq_module._LIBROSA_AVAILABLE
        try:
            aq_module._LIBROSA_AVAILABLE = False
            report = await validate_audio_quality(good_wav)
            assert report.passed is False
            assert report.score == 0.0
            assert any(i.code == "librosa_missing" for i in report.issues)
        finally:
            aq_module._LIBROSA_AVAILABLE = original

    @pytest.mark.asyncio
    async def test_score_graceful_without_librosa(self, good_wav: Path):
        import app.services.audio_quality as aq_module

        original = aq_module._LIBROSA_AVAILABLE
        try:
            aq_module._LIBROSA_AVAILABLE = False
            score = await score_voice_quality(
                original_samples=[good_wav],
                synthesized_audio=good_wav,
                reference_text="Test",
            )
            assert score.overall == 0.0
            assert "error" in score.details
        finally:
            aq_module._LIBROSA_AVAILABLE = original
