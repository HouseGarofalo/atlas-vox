"""VQ-36 — per-profile quality dashboard aggregation.

Rolls up the quality signals this session's other tasks produce into a
single payload the frontend can render as charts:

- WER time-series from ``synthesis_history.quality_wer`` (written post-synth
  by the SL-28 Whisper-check Celery task).
- Per-version metrics from ``model_version.metrics_json`` (SL-27 regression
  detector populates WER / MOS proxy / speaker similarity; the training
  task adds method + duration).
- Rating distribution from ``synthesis_feedback`` (SL-25).
- Sample health breakdown from ``audio_sample.analysis_json`` (the
  ``passed`` boolean written by the audio quality validator).
- Overall scalar quality score combining the signals for dashboard KPIs.

Everything is computed in a single async call — the page renders instantly
instead of fanning out to five endpoints.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio_sample import AudioSample
from app.models.model_version import ModelVersion
from app.models.synthesis_feedback import SynthesisFeedback
from app.models.synthesis_history import SynthesisHistory
from app.models.voice_profile import VoiceProfile

logger = structlog.get_logger(__name__)


@dataclass
class WerPoint:
    """One dot on the WER-over-time chart."""

    history_id: str
    created_at: str  # ISO-8601
    quality_wer: float


@dataclass
class VersionMetric:
    """Quality rollup for a single model version."""

    version_id: str
    version_number: int
    created_at: str
    quality_wer: float | None = None
    mos: float | None = None
    speaker_similarity: float | None = None
    is_regression: bool | None = None
    method: str | None = None
    is_active: bool = False


@dataclass
class RatingDistribution:
    """Thumbs up/down counts for this profile's synthesis outputs."""

    up: int = 0
    down: int = 0
    total: int = 0
    up_pct: float = 0.0


@dataclass
class SampleHealth:
    """How many training samples passed/failed the audio-quality checks."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    unknown: int = 0
    pass_rate_pct: float = 0.0


@dataclass
class QualityDashboard:
    """Top-level payload returned by :func:`build_quality_dashboard`."""

    profile_id: str
    profile_name: str
    generated_at: str
    # Scalar KPIs for the dashboard header.
    overall_score: float  # 0..100
    recent_wer: float | None
    active_version_id: str | None
    # Time-series + rollups for charts.
    wer_series: list[WerPoint] = field(default_factory=list)
    version_metrics: list[VersionMetric] = field(default_factory=list)
    rating_distribution: RatingDistribution = field(default_factory=RatingDistribution)
    sample_health: SampleHealth = field(default_factory=SampleHealth)
    # Summary stats.
    synthesis_count: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


# WER below this is treated as "good"; above this is "flagged".
_WER_GOOD = 0.10
_WER_BAD = 0.30


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _score_from_wer(avg_wer: float | None) -> float:
    """Map an average WER into a 0..100 score (lower WER → higher score)."""
    if avg_wer is None:
        return 50.0  # neutral when unknown
    # WER 0.00 → 100, 0.10 → 90, 0.30 → 40, 0.60+ → 0.
    if avg_wer <= _WER_GOOD:
        return 100.0 - (avg_wer / _WER_GOOD) * 10.0
    if avg_wer <= _WER_BAD:
        return 90.0 - ((avg_wer - _WER_GOOD) / (_WER_BAD - _WER_GOOD)) * 50.0
    return max(0.0, 40.0 - ((avg_wer - _WER_BAD) / 0.3) * 40.0)


def _score_from_rating(dist: RatingDistribution) -> float:
    if dist.total == 0:
        return 50.0
    return dist.up_pct  # already 0..100


def _score_from_sample_health(health: SampleHealth) -> float:
    if health.total == 0:
        return 50.0
    return health.pass_rate_pct


async def build_quality_dashboard(
    db: AsyncSession, profile_id: str, *, wer_limit: int = 50,
) -> QualityDashboard:
    """Aggregate every quality signal we have for ``profile_id`` into one payload."""
    # 1. Profile lookup — 404-worthy if missing.
    profile = (
        await db.execute(
            select(VoiceProfile).where(VoiceProfile.id == profile_id)
        )
    ).scalar_one_or_none()
    if profile is None:
        raise ValueError("Profile not found")

    warnings: list[str] = []

    # 2. WER time-series: the most recent `wer_limit` syntheses that have
    # been Whisper-checked. Older rows (pre-SL-28 migration) have
    # quality_wer=NULL and don't appear on the chart.
    wer_rows = (
        await db.execute(
            select(
                SynthesisHistory.id,
                SynthesisHistory.created_at,
                SynthesisHistory.quality_wer,
            )
            .where(
                SynthesisHistory.profile_id == profile_id,
                SynthesisHistory.quality_wer.is_not(None),
            )
            .order_by(SynthesisHistory.created_at.desc())
            .limit(wer_limit)
        )
    ).all()
    # Chart wants chronological order, oldest → newest.
    wer_series = list(reversed([
        WerPoint(
            history_id=r[0],
            created_at=(r[1].isoformat() if isinstance(r[1], datetime) else str(r[1])),
            quality_wer=float(r[2]),
        )
        for r in wer_rows
    ]))
    recent_wer = wer_series[-1].quality_wer if wer_series else None
    avg_wer = (
        sum(p.quality_wer for p in wer_series) / len(wer_series)
        if wer_series else None
    )

    # 3. Version metrics.
    versions = (
        await db.execute(
            select(ModelVersion)
            .where(ModelVersion.profile_id == profile_id)
            .order_by(ModelVersion.version_number.asc())
        )
    ).scalars().all()
    version_metrics: list[VersionMetric] = []
    for v in versions:
        metrics: dict[str, Any] = {}
        if v.metrics_json:
            try:
                parsed = json.loads(v.metrics_json)
                if isinstance(parsed, dict):
                    metrics = parsed
            except (ValueError, TypeError):
                warnings.append(f"version {v.version_number} has malformed metrics_json")
        version_metrics.append(VersionMetric(
            version_id=v.id,
            version_number=v.version_number,
            created_at=v.created_at.isoformat() if isinstance(v.created_at, datetime) else str(v.created_at),
            quality_wer=_coerce_float(metrics.get("quality_wer")),
            mos=_coerce_float(metrics.get("mos")),
            speaker_similarity=_coerce_float(metrics.get("speaker_similarity")),
            is_regression=_coerce_bool(metrics.get("is_regression")),
            method=metrics.get("method") if isinstance(metrics.get("method"), str) else None,
            is_active=(profile.active_version_id == v.id),
        ))

    # 4. Rating distribution — thumbs up/down on any synthesis history
    # row belonging to this profile.
    rating_rows = (
        await db.execute(
            select(SynthesisFeedback.rating, func.count().label("n"))
            .join(
                SynthesisHistory,
                SynthesisFeedback.history_id == SynthesisHistory.id,
            )
            .where(SynthesisHistory.profile_id == profile_id)
            .group_by(SynthesisFeedback.rating)
        )
    ).all()
    rating = RatingDistribution()
    for r, n in rating_rows:
        if r == "up":
            rating.up = int(n)
        elif r == "down":
            rating.down = int(n)
    rating.total = rating.up + rating.down
    rating.up_pct = (rating.up / rating.total * 100.0) if rating.total else 0.0

    # 5. Sample health.
    sample_rows = (
        await db.execute(
            select(AudioSample.analysis_json).where(
                AudioSample.profile_id == profile_id
            )
        )
    ).all()
    health = SampleHealth(total=len(sample_rows))
    for (payload,) in sample_rows:
        if not payload:
            health.unknown += 1
            continue
        try:
            parsed = json.loads(payload) if isinstance(payload, str) else payload
        except (ValueError, TypeError):
            health.unknown += 1
            continue
        if isinstance(parsed, dict) and "passed" in parsed:
            if parsed["passed"]:
                health.passed += 1
            else:
                health.failed += 1
        else:
            health.unknown += 1
    judged = health.passed + health.failed
    health.pass_rate_pct = (health.passed / judged * 100.0) if judged else 0.0

    # 6. Synthesis count (any status, any quality).
    synth_count = (
        await db.execute(
            select(func.count())
            .select_from(SynthesisHistory)
            .where(SynthesisHistory.profile_id == profile_id)
        )
    ).scalar() or 0

    # 7. Overall score — mean of the three orthogonal signals.
    overall = (
        _score_from_wer(avg_wer) * 0.5
        + _score_from_rating(rating) * 0.3
        + _score_from_sample_health(health) * 0.2
    )
    overall = _clamp(overall, 0.0, 100.0)

    if not wer_series:
        warnings.append("no Whisper-check data yet — WER chart will be empty")
    if not versions:
        warnings.append("no trained versions yet — version metrics will be empty")

    logger.info(
        "quality_dashboard_built",
        profile_id=profile_id,
        synthesis_count=synth_count,
        versions=len(version_metrics),
        wer_points=len(wer_series),
        overall_score=round(overall, 1),
    )

    return QualityDashboard(
        profile_id=profile_id,
        profile_name=profile.name,
        generated_at=datetime.now(UTC).isoformat(),
        overall_score=round(overall, 1),
        recent_wer=recent_wer,
        active_version_id=profile.active_version_id,
        wer_series=wer_series,
        version_metrics=version_metrics,
        rating_distribution=rating,
        sample_health=health,
        synthesis_count=int(synth_count),
        warnings=warnings,
    )


def _coerce_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _coerce_bool(v: Any) -> bool | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in {"true", "1", "yes", "y"}
    return None
