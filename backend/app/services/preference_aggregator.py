"""Preference aggregation (SL-26).

Rolls up ``SynthesisFeedback`` rows for a given voice profile into a summary
of favored voice_settings ranges and favored text characteristics.  The
summary is consumed by the (future) recommender and the Quality Dashboard
and is recomputed nightly by ``app.tasks.preferences.rollup_preferences``.

Design notes
------------
- Pure-python statistics (mean + population stdev).  Avoids adding numpy as a
  runtime dependency for this service; the audio pipeline already pulls in
  numpy, but the aggregator must work in a lightweight worker process too.
- Only numeric ``settings_json`` keys contribute to favored ranges.  Nested
  dicts (e.g., provider-specific ``voice_settings``) are flattened with dot
  notation to keep the JSON schema stable over time.
- Null-safe: if a profile has no feedback, an empty-but-valid summary is
  returned so callers never have to branch on ``None``.
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.synthesis_feedback import RATING_DOWN, RATING_UP, SynthesisFeedback
from app.models.synthesis_history import SynthesisHistory

logger = structlog.get_logger(__name__)


@dataclass
class NumericRange:
    """Mean + stdev + sample count for a single numeric setting key."""

    mean: float
    stdev: float
    count: int

    def to_dict(self) -> dict:
        return {"mean": self.mean, "stdev": self.stdev, "count": self.count}


@dataclass
class TextCharacteristics:
    """Aggregate text metrics across positively-rated syntheses."""

    avg_char_count: float = 0.0
    avg_word_count: float = 0.0
    sample_count: int = 0

    def to_dict(self) -> dict:
        return {
            "avg_char_count": self.avg_char_count,
            "avg_word_count": self.avg_word_count,
            "sample_count": self.sample_count,
        }


@dataclass
class PreferenceSummary:
    """Per-profile rollup of user feedback — persisted as ``summary_json``."""

    profile_id: str
    total_up: int = 0
    total_down: int = 0
    favored_voice_settings: dict[str, NumericRange] = field(default_factory=dict)
    favored_text: TextCharacteristics = field(default_factory=TextCharacteristics)
    computed_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "total_up": self.total_up,
            "total_down": self.total_down,
            "favored_voice_settings": {
                k: v.to_dict() for k, v in self.favored_voice_settings.items()
            },
            "favored_text": self.favored_text.to_dict(),
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
        }


# Keys inside ``settings_json`` that must NOT be aggregated as numeric
# preferences — they are provider metadata, not tuning dials.
_IGNORED_SETTINGS_KEYS = frozenset({"preset_id"})


def _flatten_numeric(
    prefix: str, value: object, sink: dict[str, list[float]]
) -> None:
    """Recursively collect numeric (int/float, non-bool) values from settings.

    ``bool`` is technically an ``int`` subclass but carries no useful range
    information, so it is excluded.
    """
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        if math.isfinite(value):
            sink.setdefault(prefix, []).append(float(value))
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if k in _IGNORED_SETTINGS_KEYS:
                continue
            next_key = f"{prefix}.{k}" if prefix else k
            _flatten_numeric(next_key, v, sink)


async def aggregate_preferences(
    db: AsyncSession, profile_id: str
) -> PreferenceSummary:
    """Compute a ``PreferenceSummary`` for a single profile.

    Joins ``SynthesisFeedback`` → ``SynthesisHistory`` filtered on
    ``profile_id``.  Positive ratings populate the favored-settings and
    text-characteristics buckets; negative ratings only contribute to counts.
    """
    stmt = (
        select(SynthesisFeedback, SynthesisHistory)
        .join(
            SynthesisHistory,
            SynthesisHistory.id == SynthesisFeedback.history_id,
        )
        .where(SynthesisHistory.profile_id == profile_id)
    )
    rows = (await db.execute(stmt)).all()

    summary = PreferenceSummary(profile_id=profile_id)
    if not rows:
        return summary

    numeric_samples: dict[str, list[float]] = {}
    char_counts: list[int] = []
    word_counts: list[int] = []

    for feedback, history in rows:
        if feedback.rating == RATING_UP:
            summary.total_up += 1
        elif feedback.rating == RATING_DOWN:
            summary.total_down += 1
        else:
            # Unknown ratings are simply ignored — keeps the aggregator
            # forward-compatible with future rating values.
            continue

        # Only positively-rated syntheses shape the favored ranges/text metrics.
        if feedback.rating != RATING_UP:
            continue

        if history.settings_json:
            try:
                parsed = json.loads(history.settings_json)
            except (TypeError, ValueError):
                parsed = None
            if isinstance(parsed, dict):
                _flatten_numeric("", parsed, numeric_samples)

        if history.text:
            char_counts.append(len(history.text))
            word_counts.append(len([w for w in history.text.split() if w]))

    for key, values in numeric_samples.items():
        if not values:
            continue
        mean = statistics.fmean(values)
        stdev = statistics.pstdev(values) if len(values) > 1 else 0.0
        summary.favored_voice_settings[key] = NumericRange(
            mean=round(mean, 6),
            stdev=round(stdev, 6),
            count=len(values),
        )

    if char_counts:
        summary.favored_text = TextCharacteristics(
            avg_char_count=round(statistics.fmean(char_counts), 3),
            avg_word_count=round(statistics.fmean(word_counts), 3),
            sample_count=len(char_counts),
        )

    logger.info(
        "preference_aggregation_done",
        profile_id=profile_id,
        up=summary.total_up,
        down=summary.total_down,
        settings_keys=len(summary.favored_voice_settings),
        text_samples=summary.favored_text.sample_count,
    )
    return summary


def summary_to_json(summary: PreferenceSummary) -> str:
    """Serialise a ``PreferenceSummary`` for persistence as ``summary_json``."""
    return json.dumps(summary.to_dict())
