"""Audio quality validation and scoring for training samples."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Optional heavy deps — fail gracefully so tests can mock without librosa installed.
try:
    import librosa
    import numpy as np
    _LIBROSA_AVAILABLE = True
except ImportError:  # pragma: no cover
    librosa = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    _LIBROSA_AVAILABLE = False

# ──────────────────────────────────────────────────────────────────────────────
# Domain objects
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class QualityIssue:
    """A detected quality problem in an audio sample."""

    code: str           # e.g. "clipping", "too_quiet", "too_short"
    severity: str       # "error", "warning", "info"
    message: str
    value: float | None = None
    threshold: float | None = None


@dataclass
class AudioQualityReport:
    """Full quality assessment of a single audio sample."""

    passed: bool
    score: float                            # 0–100 overall quality score
    issues: list[QualityIssue] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)  # snr_db, rms_db, peak_db, …

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "score": self.score,
            "issues": [
                {
                    "code": i.code,
                    "severity": i.severity,
                    "message": i.message,
                    "value": i.value,
                    "threshold": i.threshold,
                }
                for i in self.issues
            ],
            "metrics": self.metrics,
        }


@dataclass
class TrainingReadiness:
    """Assessment of whether a profile's samples are ready for training."""

    ready: bool
    score: float                            # 0–100 readiness score
    sample_count: int
    total_duration: float
    issues: list[QualityIssue] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ready": self.ready,
            "score": self.score,
            "sample_count": self.sample_count,
            "total_duration": self.total_duration,
            "issues": [
                {"code": i.code, "severity": i.severity, "message": i.message}
                for i in self.issues
            ],
            "recommendations": self.recommendations,
        }


@dataclass
class VoiceQualityScore:
    """Post-training voice quality assessment."""

    overall: float              # 0–100
    naturalness: float          # 0–100
    intelligibility: float      # 0–100
    speaker_similarity: float   # 0–100 — closeness to original samples
    consistency: float          # 0–100 — stability across texts
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "overall": self.overall,
            "naturalness": self.naturalness,
            "intelligibility": self.intelligibility,
            "speaker_similarity": self.speaker_similarity,
            "consistency": self.consistency,
            "details": self.details,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Thresholds
# ──────────────────────────────────────────────────────────────────────────────

_DURATION_MIN_ERROR = 1.0       # seconds
_DURATION_MAX_ERROR = 60.0
_DURATION_MIN_WARN = 3.0
_DURATION_MAX_WARN = 30.0

_CLIP_THRESHOLD = 0.99          # peak magnitude considered clipping
_CLIP_ERROR_RATIO = 0.05        # > 5 % of samples clipping → error

_RMS_TOO_QUIET_DB = -40.0       # dB
_RMS_TOO_LOUD_DB = -3.0
_RMS_WARN_LOW_DB = -20.0
_RMS_WARN_HIGH_DB = -6.0

_SNR_WARN_DB = 15.0
_SILENCE_RATIO_WARN = 0.50      # > 50 % silence

_SAMPLE_RATE_WARN = 16_000      # Hz

# Penalty weights per issue severity (removed from 100)
_PENALTY = {"error": 25.0, "warning": 10.0, "info": 2.0}

# ──────────────────────────────────────────────────────────────────────────────
# Synchronous implementation (runs in executor)
# ──────────────────────────────────────────────────────────────────────────────

def _validate_sync(audio_path: Path) -> AudioQualityReport:
    """CPU-bound quality validation — called via run_in_executor."""
    if not _LIBROSA_AVAILABLE:
        logger.warning("librosa_unavailable", path=str(audio_path))
        return AudioQualityReport(
            passed=False,
            score=0.0,
            issues=[
                QualityIssue(
                    code="librosa_missing",
                    severity="error",
                    message="librosa / numpy not installed — cannot validate audio",
                )
            ],
        )

    issues: list[QualityIssue] = []

    # Load audio (keep native sample rate)
    y, sr = librosa.load(str(audio_path), sr=None, mono=True)
    if len(y) == 0:
        return AudioQualityReport(
            passed=False,
            score=0.0,
            issues=[
                QualityIssue(
                    code="empty_audio",
                    severity="error",
                    message="Audio file is empty or could not be decoded",
                )
            ],
        )

    duration = len(y) / sr

    # ── Duration ──────────────────────────────────────────────────────────────
    if duration < _DURATION_MIN_ERROR:
        issues.append(QualityIssue(
            code="too_short",
            severity="error",
            message=f"Audio is {duration:.1f}s — minimum required is {_DURATION_MIN_ERROR}s",
            value=duration,
            threshold=_DURATION_MIN_ERROR,
        ))
    elif duration < _DURATION_MIN_WARN:
        issues.append(QualityIssue(
            code="short_duration",
            severity="warning",
            message=f"Audio is {duration:.1f}s — recommended minimum is {_DURATION_MIN_WARN}s",
            value=duration,
            threshold=_DURATION_MIN_WARN,
        ))

    if duration > _DURATION_MAX_ERROR:
        issues.append(QualityIssue(
            code="too_long",
            severity="error",
            message=f"Audio is {duration:.1f}s — maximum allowed is {_DURATION_MAX_ERROR}s",
            value=duration,
            threshold=_DURATION_MAX_ERROR,
        ))
    elif duration > _DURATION_MAX_WARN:
        issues.append(QualityIssue(
            code="long_duration",
            severity="warning",
            message=f"Audio is {duration:.1f}s — recommended maximum is {_DURATION_MAX_WARN}s",
            value=duration,
            threshold=_DURATION_MAX_WARN,
        ))

    # ── Sample rate ───────────────────────────────────────────────────────────
    if sr < _SAMPLE_RATE_WARN:
        issues.append(QualityIssue(
            code="low_sample_rate",
            severity="warning",
            message=f"Sample rate is {sr} Hz — recommended minimum is {_SAMPLE_RATE_WARN} Hz",
            value=float(sr),
            threshold=float(_SAMPLE_RATE_WARN),
        ))

    # ── Clipping ──────────────────────────────────────────────────────────────
    peak = float(np.max(np.abs(y)))
    clipping_ratio = float(np.mean(np.abs(y) >= _CLIP_THRESHOLD))
    if clipping_ratio > _CLIP_ERROR_RATIO:
        issues.append(QualityIssue(
            code="clipping",
            severity="error",
            message=(
                f"{clipping_ratio*100:.1f}% of samples are clipping "
                f"(threshold: {_CLIP_ERROR_RATIO*100:.0f}%)"
            ),
            value=round(clipping_ratio, 4),
            threshold=_CLIP_ERROR_RATIO,
        ))
    elif clipping_ratio > 0:
        issues.append(QualityIssue(
            code="minor_clipping",
            severity="warning",
            message=f"Minor clipping detected in {clipping_ratio*100:.2f}% of samples",
            value=round(clipping_ratio, 4),
            threshold=_CLIP_ERROR_RATIO,
        ))

    # ── RMS loudness ──────────────────────────────────────────────────────────
    rms_linear = float(np.sqrt(np.mean(y ** 2)))
    rms_db = float(20.0 * np.log10(rms_linear + 1e-10))

    if rms_db < _RMS_TOO_QUIET_DB:
        issues.append(QualityIssue(
            code="too_quiet",
            severity="error",
            message=f"RMS level is {rms_db:.1f} dB — too quiet for training",
            value=round(rms_db, 2),
            threshold=_RMS_TOO_QUIET_DB,
        ))
    elif rms_db < _RMS_WARN_LOW_DB:
        issues.append(QualityIssue(
            code="quiet_audio",
            severity="warning",
            message=f"RMS level is {rms_db:.1f} dB — consider normalizing",
            value=round(rms_db, 2),
            threshold=_RMS_WARN_LOW_DB,
        ))
    elif rms_db > _RMS_TOO_LOUD_DB:
        issues.append(QualityIssue(
            code="too_loud",
            severity="error",
            message=f"RMS level is {rms_db:.1f} dB — audio will cause distortion",
            value=round(rms_db, 2),
            threshold=_RMS_TOO_LOUD_DB,
        ))
    elif rms_db > _RMS_WARN_HIGH_DB:
        issues.append(QualityIssue(
            code="loud_audio",
            severity="warning",
            message=f"RMS level is {rms_db:.1f} dB — slightly over recommended range",
            value=round(rms_db, 2),
            threshold=_RMS_WARN_HIGH_DB,
        ))

    # ── SNR estimation via loudest-vs-quietest segment comparison ─────────────
    frame_length = int(sr * 0.025)     # 25 ms frames
    hop_length = frame_length // 2
    rms_frames = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    rms_frames = rms_frames[rms_frames > 1e-10]
    snr_db = 0.0
    if len(rms_frames) >= 4:
        n = max(1, len(rms_frames) // 10)
        signal_power = float(np.mean(np.sort(rms_frames)[-n:] ** 2))
        noise_power = float(np.mean(np.sort(rms_frames)[:n] ** 2))
        if noise_power > 0:
            snr_db = float(10.0 * np.log10(signal_power / noise_power))
        else:
            snr_db = 60.0   # treat zero noise as very clean
    if snr_db < _SNR_WARN_DB:
        issues.append(QualityIssue(
            code="low_snr",
            severity="warning",
            message=f"Estimated SNR is {snr_db:.1f} dB — background noise may degrade training",
            value=round(snr_db, 2),
            threshold=_SNR_WARN_DB,
        ))

    # ── Silence ratio ─────────────────────────────────────────────────────────
    silence_mask = np.abs(y) < librosa.db_to_amplitude(_RMS_TOO_QUIET_DB)
    silence_ratio = float(np.mean(silence_mask))
    if silence_ratio > _SILENCE_RATIO_WARN:
        issues.append(QualityIssue(
            code="excessive_silence",
            severity="warning",
            message=f"{silence_ratio*100:.0f}% of the audio is silence — consider trimming",
            value=round(silence_ratio, 4),
            threshold=_SILENCE_RATIO_WARN,
        ))

    # ── Score ─────────────────────────────────────────────────────────────────
    score = 100.0
    for issue in issues:
        score -= _PENALTY.get(issue.severity, 0.0)
    score = max(0.0, min(100.0, score))

    has_errors = any(i.severity == "error" for i in issues)

    metrics = {
        "duration": round(duration, 3),
        "sample_rate": sr,
        "rms_db": round(rms_db, 2),
        "peak_db": round(float(20.0 * np.log10(peak + 1e-10)), 2),
        "clipping_ratio": round(clipping_ratio, 6),
        "silence_ratio": round(silence_ratio, 4),
        "snr_db": round(snr_db, 2),
    }

    logger.debug(
        "audio_quality_validated",
        path=str(audio_path),
        score=score,
        passed=not has_errors,
        issue_count=len(issues),
    )
    return AudioQualityReport(passed=not has_errors, score=score, issues=issues, metrics=metrics)


def _score_voice_sync(
    original_samples: list[Path],
    synthesized_audio: Path,
    reference_text: str,
) -> VoiceQualityScore:
    """CPU-bound voice quality scoring — called via run_in_executor."""
    if not _LIBROSA_AVAILABLE:
        logger.warning("librosa_unavailable_for_scoring")
        return VoiceQualityScore(
            overall=0.0,
            naturalness=0.0,
            intelligibility=0.0,
            speaker_similarity=0.0,
            consistency=0.0,
            details={"error": "librosa not installed"},
        )

    # ── Load synthesized audio ────────────────────────────────────────────────
    y_synth, sr_synth = librosa.load(str(synthesized_audio), sr=22050, mono=True)
    if len(y_synth) == 0:
        return VoiceQualityScore(
            overall=0.0,
            naturalness=0.0,
            intelligibility=0.0,
            speaker_similarity=0.0,
            consistency=0.0,
            details={"error": "synthesized audio is empty"},
        )

    # ── MFCC of synthesized audio ─────────────────────────────────────────────
    n_mfcc = 13
    mfcc_synth = librosa.feature.mfcc(y=y_synth, sr=sr_synth, n_mfcc=n_mfcc)
    mean_synth = np.mean(mfcc_synth, axis=1)

    # ── Speaker similarity: mean cosine distance to each original sample ──────
    similarities: list[float] = []
    original_mfcc_means: list[np.ndarray] = []
    for orig_path in original_samples:
        try:
            y_orig, sr_orig = librosa.load(str(orig_path), sr=22050, mono=True)
            if len(y_orig) == 0:
                continue
            mfcc_orig = librosa.feature.mfcc(y=y_orig, sr=sr_orig, n_mfcc=n_mfcc)
            mean_orig = np.mean(mfcc_orig, axis=1)
            original_mfcc_means.append(mean_orig)

            # Cosine similarity → [0, 1]
            dot = float(np.dot(mean_orig, mean_synth))
            norm = float(np.linalg.norm(mean_orig) * np.linalg.norm(mean_synth))
            cos_sim = dot / norm if norm > 0 else 0.0
            # Map [-1, 1] → [0, 100]
            similarities.append((cos_sim + 1.0) / 2.0 * 100.0)
        except Exception as exc:
            logger.warning("original_sample_load_failed", path=str(orig_path), error=str(exc))

    speaker_similarity = float(np.mean(similarities)) if similarities else 50.0

    # ── Naturalness: prosody variance (higher is more natural, up to a point) ─
    # Use pitch (F0) variance as a proxy for prosody richness.
    try:
        f0, voiced_flag, _ = librosa.pyin(
            y_synth,
            fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C7"),
            sr=sr_synth,
        )
        f0_voiced = f0[voiced_flag] if f0 is not None and voiced_flag is not None else np.array([])
        # A naturalness proxy: normalise std/mean of F0.
        if len(f0_voiced) > 4:
            f0_mean = float(np.mean(f0_voiced))
            f0_std = float(np.std(f0_voiced))
            jitter_ratio = f0_std / (f0_mean + 1e-10)
            # Ideal jitter ≈ 0.05–0.15; penalise flat (robotic) or chaotic speech
            naturalness = 100.0 - abs(jitter_ratio - 0.10) * 400.0
            naturalness = max(0.0, min(100.0, naturalness))
        else:
            naturalness = 50.0  # cannot determine — neutral score
    except Exception:
        naturalness = 50.0

    # ── Intelligibility: spectral clarity via high-frequency energy ratio ─────
    # Human speech consonants live 2–8 kHz; voiced vowels 100–2 kHz.
    # A clear recording will have a healthy ratio of high-to-total energy.
    spec = np.abs(librosa.stft(y_synth))
    freq_bins = librosa.fft_frequencies(sr=sr_synth)
    high_freq_mask = freq_bins >= 2000
    total_energy = float(np.sum(spec ** 2)) + 1e-10
    high_energy = float(np.sum(spec[high_freq_mask, :] ** 2))
    clarity_ratio = high_energy / total_energy
    # Typical speech: clarity_ratio ≈ 0.15–0.45
    intelligibility = min(100.0, clarity_ratio / 0.45 * 100.0)
    intelligibility = max(0.0, intelligibility)

    # ── Consistency: MFCC distance variance across original samples ───────────
    consistency = 100.0
    if len(original_mfcc_means) >= 2:
        inter_distances: list[float] = []
        for i in range(len(original_mfcc_means)):
            for j in range(i + 1, len(original_mfcc_means)):
                d = float(np.linalg.norm(original_mfcc_means[i] - original_mfcc_means[j]))
                inter_distances.append(d)
        dist_variance = float(np.std(inter_distances)) if inter_distances else 0.0
        # Normalise: variance ≤ 5 → full score; variance ≥ 50 → 0
        consistency = max(0.0, 100.0 - dist_variance * 2.0)

    # ── Overall weighted score ────────────────────────────────────────────────
    overall = (
        naturalness * 0.30
        + intelligibility * 0.25
        + speaker_similarity * 0.30
        + consistency * 0.15
    )
    overall = max(0.0, min(100.0, overall))

    details = {
        "mfcc_cosine_similarities": [round(s, 2) for s in similarities],
        "f0_naturalness_raw": round(naturalness, 2),
        "spectral_clarity_ratio": round(clarity_ratio, 4),
        "consistency_variance": round(
            float(np.std([float(np.linalg.norm(m)) for m in original_mfcc_means]))
            if original_mfcc_means
            else 0.0,
            4,
        ),
    }

    logger.debug(
        "voice_quality_scored",
        synthesized=str(synthesized_audio),
        overall=round(overall, 2),
        naturalness=round(naturalness, 2),
        intelligibility=round(intelligibility, 2),
        speaker_similarity=round(speaker_similarity, 2),
        consistency=round(consistency, 2),
    )
    return VoiceQualityScore(
        overall=round(overall, 2),
        naturalness=round(naturalness, 2),
        intelligibility=round(intelligibility, 2),
        speaker_similarity=round(speaker_similarity, 2),
        consistency=round(consistency, 2),
        details=details,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Public async API
# ──────────────────────────────────────────────────────────────────────────────

async def validate_audio_quality(audio_path: Path) -> AudioQualityReport:
    """Validate a single audio file's quality for voice training.

    CPU-heavy work (librosa) is dispatched to a thread pool executor so the
    FastAPI event loop is never blocked.

    Args:
        audio_path: Absolute path to the audio file.

    Returns:
        AudioQualityReport with pass/fail verdict, 0-100 score, issues, and
        raw metrics (snr_db, rms_db, peak_db, clipping_ratio, silence_ratio,
        duration, sample_rate).
    """
    logger.info("validate_audio_quality_start", path=str(audio_path))
    loop = asyncio.get_running_loop()
    report = await loop.run_in_executor(None, partial(_validate_sync, audio_path))
    logger.info(
        "validate_audio_quality_done",
        path=str(audio_path),
        score=report.score,
        passed=report.passed,
        issues=len(report.issues),
    )
    return report


async def assess_training_readiness(
    samples: list[dict],        # [{path, duration, quality_report}, …]
    provider_name: str,
    min_samples: int = 2,
) -> TrainingReadiness:
    """Assess whether collected samples are ready for training.

    Args:
        samples: List of sample dicts.  Each must contain at least ``path``
            (str or Path).  ``duration`` (float, seconds) and
            ``quality_report`` (AudioQualityReport or its dict serialisation)
            are optional — if absent they will be computed on the fly.
        provider_name: The provider being used (for threshold overrides).
        min_samples: Minimum number of samples required.

    Returns:
        TrainingReadiness with pass/fail verdict, 0-100 readiness score, and
        human-readable recommendations.
    """
    logger.info(
        "assess_training_readiness_start",
        provider=provider_name,
        sample_count=len(samples),
    )

    issues: list[QualityIssue] = []
    recommendations: list[str] = []

    # ── Ensure every sample has an AudioQualityReport ─────────────────────────
    resolved: list[dict] = []
    for s in samples:
        path = Path(s["path"])
        if "quality_report" in s and isinstance(s["quality_report"], AudioQualityReport):
            report = s["quality_report"]
        elif "quality_report" in s and isinstance(s["quality_report"], dict):
            # Re-hydrate from dict representation
            raw = s["quality_report"]
            issue_objs = [
                QualityIssue(
                    code=i["code"],
                    severity=i["severity"],
                    message=i["message"],
                    value=i.get("value"),
                    threshold=i.get("threshold"),
                )
                for i in raw.get("issues", [])
            ]
            report = AudioQualityReport(
                passed=raw["passed"],
                score=raw["score"],
                issues=issue_objs,
                metrics=raw.get("metrics", {}),
            )
        else:
            report = await validate_audio_quality(path)

        duration = s.get("duration") or report.metrics.get("duration", 0.0)
        resolved.append({"path": path, "duration": float(duration), "report": report})

    sample_count = len(resolved)
    total_duration = sum(r["duration"] for r in resolved)

    # ── Sample count check ────────────────────────────────────────────────────
    if sample_count < min_samples:
        issues.append(QualityIssue(
            code="insufficient_samples",
            severity="error",
            message=(
                f"Only {sample_count} sample(s) available — "
                f"minimum {min_samples} required"
            ),
            value=float(sample_count),
            threshold=float(min_samples),
        ))
        needed = min_samples - sample_count
        recommendations.append(
            f"Add at least {needed} more recording(s) to meet the minimum sample requirement."
        )

    # ── Duration checks ───────────────────────────────────────────────────────
    _DURATION_MIN_ERROR_TRAIN = 10.0
    _DURATION_MIN_WARN_TRAIN = 30.0

    if total_duration < _DURATION_MIN_ERROR_TRAIN:
        issues.append(QualityIssue(
            code="insufficient_duration",
            severity="error",
            message=(
                f"Total audio duration is {total_duration:.1f}s — "
                f"minimum {_DURATION_MIN_ERROR_TRAIN}s required"
            ),
            value=round(total_duration, 2),
            threshold=_DURATION_MIN_ERROR_TRAIN,
        ))
        deficit = _DURATION_MIN_ERROR_TRAIN - total_duration
        recommendations.append(
            f"Add approximately {deficit:.0f}s more audio to reach the minimum required duration."
        )
    elif total_duration < _DURATION_MIN_WARN_TRAIN:
        issues.append(QualityIssue(
            code="low_total_duration",
            severity="warning",
            message=(
                f"Total audio is {total_duration:.1f}s — "
                f"{_DURATION_MIN_WARN_TRAIN}s recommended for best results"
            ),
            value=round(total_duration, 2),
            threshold=_DURATION_MIN_WARN_TRAIN,
        ))
        recommendations.append(
            f"Consider adding {_DURATION_MIN_WARN_TRAIN - total_duration:.0f}s "
            "more audio for better voice quality."
        )

    # ── Per-sample quality checks ─────────────────────────────────────────────
    scores = []
    for idx, item in enumerate(resolved, start=1):
        report = item["report"]
        scores.append(report.score)

        sample_errors = [i for i in report.issues if i.severity == "error"]
        if sample_errors:
            for err in sample_errors:
                issues.append(QualityIssue(
                    code=f"sample_{idx}_{err.code}",
                    severity="warning",   # Downgrade to warning at batch level
                    message=f"Sample {idx} ({item['path'].name}): {err.message}",
                    value=err.value,
                    threshold=err.threshold,
                ))
            primary_issue = sample_errors[0]
            recommendations.append(
                f"Re-record sample {idx} ({item['path'].name}): {primary_issue.message}"
            )

    # ── Average quality check ─────────────────────────────────────────────────
    avg_quality = float(sum(scores) / len(scores)) if scores else 0.0
    _QUALITY_MIN = 50.0
    if avg_quality < _QUALITY_MIN:
        issues.append(QualityIssue(
            code="low_average_quality",
            severity="error",
            message=(
                f"Average sample quality score is {avg_quality:.0f}/100 — "
                f"minimum {_QUALITY_MIN:.0f} required"
            ),
            value=round(avg_quality, 2),
            threshold=_QUALITY_MIN,
        ))
        recommendations.append(
            "Overall sample quality is low. Re-record in a quiet environment "
            "with consistent microphone positioning."
        )

    # ── Readiness score ───────────────────────────────────────────────────────
    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    readiness_score = 100.0 - (error_count * 25.0) - (warning_count * 5.0)
    readiness_score = max(0.0, min(100.0, readiness_score))

    ready = error_count == 0

    if not recommendations and ready:
        recommendations.append(
            f"All {sample_count} samples passed quality checks. "
            "Profile is ready for training."
        )

    logger.info(
        "assess_training_readiness_done",
        provider=provider_name,
        ready=ready,
        score=readiness_score,
        sample_count=sample_count,
        total_duration=total_duration,
        error_count=error_count,
        warning_count=warning_count,
    )
    return TrainingReadiness(
        ready=ready,
        score=round(readiness_score, 2),
        sample_count=sample_count,
        total_duration=round(total_duration, 3),
        issues=issues,
        recommendations=recommendations,
    )


async def score_voice_quality(
    original_samples: list[Path],
    synthesized_audio: Path,
    reference_text: str,
) -> VoiceQualityScore:
    """Score trained voice quality by comparing synthesis output to originals.

    Uses MFCC-based spectral similarity (cosine distance), F0 variance as a
    naturalness proxy, and spectral clarity as an intelligibility proxy.  No
    external ML models are required — only numpy/librosa.

    Args:
        original_samples: Paths to the original training sample audio files.
        synthesized_audio: Path to the synthesized audio to evaluate.
        reference_text: The text that was synthesized (logged for traceability).

    Returns:
        VoiceQualityScore with 0-100 sub-scores and a raw details dict.
    """
    logger.info(
        "score_voice_quality_start",
        synthesized=str(synthesized_audio),
        original_count=len(original_samples),
        reference_text_length=len(reference_text),
    )
    loop = asyncio.get_running_loop()
    score = await loop.run_in_executor(
        None,
        partial(_score_voice_sync, original_samples, synthesized_audio, reference_text),
    )
    logger.info(
        "score_voice_quality_done",
        synthesized=str(synthesized_audio),
        overall=score.overall,
    )
    return score
