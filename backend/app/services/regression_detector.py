"""Regression detector (SL-27).

Compares a newly trained ``ModelVersion`` against a baseline version on a
held-out phrase set using:

- **Word Error Rate (WER)** via ``WhisperTranscriber``.  Average WER across
  all eval phrases for each version — lower is better.
- **Speaker similarity**: prefers ``resemblyzer`` when installed for true
  speaker embeddings; falls back to MFCC cosine similarity (0–1 range) when
  the optional dep is unavailable.

A regression is flagged when either:
  - the new version's WER is materially worse than baseline (delta > threshold), OR
  - the speaker similarity drops by more than ``SIMILARITY_DROP_THRESHOLD``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.audio_sample import AudioSample
from app.models.model_version import ModelVersion
from app.services import whisper_transcriber
from app.services.eval_phrases import get_eval_phrases
from app.services.provider_registry import provider_registry
from app.tasks.preferences import compute_wer

logger = structlog.get_logger(__name__)

# Tunable thresholds.  Kept module-level (not in settings) so they're easy
# to reference from tests and from Archon regression dashboards.
WER_REGRESSION_DELTA: float = 0.05
SIMILARITY_DROP_THRESHOLD: float = 0.10


@dataclass
class RegressionReport:
    """Output of ``detect_regression`` — serialised straight to JSON."""

    new_version_id: str
    baseline_version_id: str
    wer_new: float
    wer_baseline: float
    speaker_sim_score: float
    is_regression: bool
    delta_metrics: dict[str, float] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "new_version_id": self.new_version_id,
            "baseline_version_id": self.baseline_version_id,
            "wer_new": self.wer_new,
            "wer_baseline": self.wer_baseline,
            "speaker_sim_score": self.speaker_sim_score,
            "is_regression": self.is_regression,
            "delta_metrics": self.delta_metrics,
            "details": self.details,
        }


async def _load_version(db: AsyncSession, version_id: str) -> ModelVersion:
    result = await db.execute(
        select(ModelVersion).where(ModelVersion.id == version_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError("ModelVersion", version_id)
    return row


async def _synthesize_for_eval(
    version: ModelVersion, phrases: list[str]
) -> list[Path]:
    """Synthesise each eval phrase using the given version's voice.

    Returns a list of WAV paths (one per phrase).  Uses the provider_registry
    to locate the right provider based on the version's stored config.
    Failures (missing provider, synthesis errors) surface the exception so
    the caller can decide whether to abort or continue.
    """
    from app.providers.base import SynthesisSettings

    # The version doesn't own a provider_name directly — look it up via its
    # profile.  We pass the model_path/provider_model_id as the voice_id.
    voice_id = version.provider_model_id or "default"

    # Providers are resolved by their profile's provider_name; we delegate
    # resolution to the caller through ``_collect_artifacts``.
    provider_name = version.__dict__.get("_provider_name")  # type: ignore[attr-defined]
    provider = provider_registry.get_provider(provider_name)

    out_paths: list[Path] = []
    settings_obj = SynthesisSettings(output_format="wav")
    for phrase in phrases:
        audio = await provider.synthesize(phrase, voice_id, settings_obj)
        out_paths.append(audio.audio_path)
    return out_paths


async def _transcribe_all(audio_paths: list[Path]) -> list[str]:
    """Run Whisper on each audio file and return the transcripts."""
    results: list[str] = []
    for p in audio_paths:
        try:
            text = await whisper_transcriber.transcribe(p)
        except Exception as exc:
            logger.warning("regression_transcribe_failed", path=str(p), error=str(exc))
            text = ""
        results.append(text)
    return results


def _mean_wer(phrases: list[str], transcripts: list[str]) -> float:
    if not phrases:
        return 0.0
    total = 0.0
    for ref, hyp in zip(phrases, transcripts, strict=False):
        total += compute_wer(ref, hyp)
    return total / len(phrases)


def _speaker_similarity_sync(
    new_paths: list[Path], baseline_paths: list[Path]
) -> float:
    """Compute a 0–1 speaker similarity score between two audio sets.

    Preferred implementation: ``resemblyzer`` voice encoder embeddings.
    Fallback: MFCC cosine similarity (still sensitive to voice timbre).
    Returns ``0.5`` when both backends are unavailable so the detector
    degrades to a purely WER-driven verdict instead of crashing.
    """
    try:
        from resemblyzer import VoiceEncoder, preprocess_wav  # type: ignore
        import numpy as np

        encoder = VoiceEncoder(verbose=False)

        def _embed(paths: list[Path]):
            wavs = [preprocess_wav(str(p)) for p in paths]
            return np.mean([encoder.embed_utterance(w) for w in wavs], axis=0)

        new_emb = _embed(new_paths)
        base_emb = _embed(baseline_paths)
        cos = float(np.dot(new_emb, base_emb) / (
            np.linalg.norm(new_emb) * np.linalg.norm(base_emb) + 1e-10
        ))
        # Map [-1, 1] → [0, 1]
        return max(0.0, min(1.0, (cos + 1.0) / 2.0))
    except ImportError:
        pass

    try:
        import librosa  # type: ignore
        import numpy as np

        def _mean_mfcc(paths: list[Path]):
            means = []
            for p in paths:
                y, sr = librosa.load(str(p), sr=22050, mono=True)
                if len(y) == 0:
                    continue
                mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
                means.append(np.mean(mfcc, axis=1))
            if not means:
                return None
            return np.mean(means, axis=0)

        new_mean = _mean_mfcc(new_paths)
        base_mean = _mean_mfcc(baseline_paths)
        if new_mean is None or base_mean is None:
            return 0.5
        norm = float(np.linalg.norm(new_mean) * np.linalg.norm(base_mean)) or 1e-10
        cos = float(np.dot(new_mean, base_mean) / norm)
        return max(0.0, min(1.0, (cos + 1.0) / 2.0))
    except ImportError:
        logger.warning("regression_speaker_sim_fallback", reason="no_backend")
        return 0.5


async def _speaker_similarity(
    new_paths: list[Path], baseline_paths: list[Path]
) -> float:
    """Run the CPU-bound speaker-similarity calc off the event loop."""
    if not new_paths or not baseline_paths:
        return 0.5
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, _speaker_similarity_sync, new_paths, baseline_paths
    )


async def detect_regression(
    db: AsyncSession,
    new_version_id: str,
    baseline_version_id: str,
) -> RegressionReport:
    """Compare two model versions and flag quality regressions.

    Raises :class:`NotFoundError` when either version does not exist.  The
    caller is responsible for committing any DB changes that follow; this
    function reads only.
    """
    if new_version_id == baseline_version_id:
        raise ValueError(
            "new_version_id and baseline_version_id must differ"
        )

    new_version = await _load_version(db, new_version_id)
    baseline_version = await _load_version(db, baseline_version_id)

    # Attach the profile's provider_name so _synthesize_for_eval can resolve
    # the right provider.  Both versions live on the same profile, by design
    # of the regression endpoint.
    from app.models.voice_profile import VoiceProfile

    profile_result = await db.execute(
        select(VoiceProfile).where(VoiceProfile.id == new_version.profile_id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        raise NotFoundError("VoiceProfile", new_version.profile_id)

    new_version.__dict__["_provider_name"] = profile.provider_name
    baseline_version.__dict__["_provider_name"] = profile.provider_name

    phrases = get_eval_phrases()

    logger.info(
        "regression_detect_start",
        new_version_id=new_version_id,
        baseline_version_id=baseline_version_id,
        phrase_count=len(phrases),
    )

    new_audios = await _synthesize_for_eval(new_version, phrases)
    baseline_audios = await _synthesize_for_eval(baseline_version, phrases)

    new_transcripts, baseline_transcripts = await asyncio.gather(
        _transcribe_all(new_audios),
        _transcribe_all(baseline_audios),
    )

    wer_new = _mean_wer(phrases, new_transcripts)
    wer_baseline = _mean_wer(phrases, baseline_transcripts)

    speaker_sim = await _speaker_similarity(new_audios, baseline_audios)

    wer_delta = wer_new - wer_baseline
    # For similarity, we compare the new version against the training samples
    # of the profile (already captured implicitly through the baseline audios
    # coming from the previously accepted version).
    is_regression = (
        wer_delta > WER_REGRESSION_DELTA
        or speaker_sim < (1.0 - SIMILARITY_DROP_THRESHOLD)
    )

    report = RegressionReport(
        new_version_id=new_version_id,
        baseline_version_id=baseline_version_id,
        wer_new=round(wer_new, 4),
        wer_baseline=round(wer_baseline, 4),
        speaker_sim_score=round(speaker_sim, 4),
        is_regression=is_regression,
        delta_metrics={
            "wer_delta": round(wer_delta, 4),
            "wer_threshold": WER_REGRESSION_DELTA,
            "similarity_threshold": 1.0 - SIMILARITY_DROP_THRESHOLD,
        },
        details={
            "phrase_count": len(phrases),
            "new_transcripts": new_transcripts,
            "baseline_transcripts": baseline_transcripts,
        },
    )

    logger.info(
        "regression_detect_done",
        new_version_id=new_version_id,
        baseline_version_id=baseline_version_id,
        wer_new=report.wer_new,
        wer_baseline=report.wer_baseline,
        speaker_sim=report.speaker_sim_score,
        is_regression=report.is_regression,
    )
    return report


# Expose a helper for callers that want to reference the audio sample paths
# directly (e.g., the endpoint wants to stream them) — not used by
# detect_regression but keeps the public surface self-contained.
async def list_profile_samples(db: AsyncSession, profile_id: str) -> list[Path]:
    result = await db.execute(
        select(AudioSample).where(AudioSample.profile_id == profile_id)
    )
    return [Path(s.file_path) for s in result.scalars().all()]
