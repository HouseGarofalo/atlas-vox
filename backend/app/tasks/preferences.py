"""Celery tasks for the self-learning feedback flywheel.

- ``rollup_preferences`` (SL-26): nightly aggregation of SynthesisFeedback
  into per-profile PreferenceSummary rows.
- ``verify_synthesis`` (SL-28): runs Whisper on a freshly produced synthesis
  output to compute WER against the original input text.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import structlog

from app.tasks.celery_app import celery_app
from app.tasks.utils import run_async, worker_session

logger = structlog.get_logger(__name__)

# WER above this threshold flags a synthesis as potentially low-quality.
# Kept in sync with the flag threshold surfaced to clients in
# ``app.api.v1.endpoints.synthesis.QUALITY_WER_FLAG_THRESHOLD``.
QUALITY_WER_FLAG_THRESHOLD = 0.3


# ---------------------------------------------------------------------------
# SL-26 — nightly preference rollup
# ---------------------------------------------------------------------------

async def _rollup_preferences_async() -> dict:
    """Async body of ``rollup_preferences`` — uses a worker-scoped DB session."""
    from sqlalchemy import distinct, select

    from app.models.preference_summary import PreferenceSummary as PreferenceSummaryModel
    from app.models.synthesis_feedback import SynthesisFeedback
    from app.models.synthesis_history import SynthesisHistory
    from app.services.preference_aggregator import (
        aggregate_preferences,
        summary_to_json,
    )

    async with worker_session() as db:
        # Find every profile that has at least one feedback row.
        stmt = (
            select(distinct(SynthesisHistory.profile_id))
            .join(
                SynthesisFeedback,
                SynthesisFeedback.history_id == SynthesisHistory.id,
            )
        )
        profile_ids = [row[0] for row in (await db.execute(stmt)).all()]

        updated = 0
        for pid in profile_ids:
            summary = await aggregate_preferences(db, pid)
            summary.computed_at = datetime.now(UTC)

            existing = await db.execute(
                select(PreferenceSummaryModel).where(
                    PreferenceSummaryModel.profile_id == pid
                )
            )
            row = existing.scalar_one_or_none()
            if row is None:
                row = PreferenceSummaryModel(
                    profile_id=pid,
                    summary_json=summary_to_json(summary),
                    computed_at=summary.computed_at,
                )
                db.add(row)
            else:
                row.summary_json = summary_to_json(summary)
                row.computed_at = summary.computed_at
            updated += 1

        await db.commit()
        logger.info("preference_rollup_done", profiles=updated)
        return {"profiles_updated": updated}


@celery_app.task(name="app.tasks.preferences.rollup_preferences")
def rollup_preferences() -> dict:
    """Nightly rollup — one PreferenceSummary row per profile with feedback."""
    logger.info("preference_rollup_start")
    return run_async(_rollup_preferences_async())


# ---------------------------------------------------------------------------
# SL-28 — Whisper verification of each synthesis
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[A-Za-z0-9']+")


def _normalise_tokens(text: str) -> list[str]:
    """Lowercase, strip punctuation, split into word tokens for WER."""
    return [m.group(0).lower() for m in _WORD_RE.finditer(text or "")]


def compute_wer(reference: str, hypothesis: str) -> float:
    """Compute classic word error rate using edit distance.

    WER = (substitutions + deletions + insertions) / reference_word_count.
    Returns 0.0 when the reference is empty (no words to get wrong).
    """
    ref = _normalise_tokens(reference)
    hyp = _normalise_tokens(hypothesis)

    if not ref:
        return 0.0
    if not hyp:
        return 1.0

    # Levenshtein edit distance in O(len(ref) * len(hyp)) time / O(len(hyp)) space.
    prev_row = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, start=1):
        curr_row = [i]
        for j, h in enumerate(hyp, start=1):
            cost = 0 if r == h else 1
            curr_row.append(min(
                curr_row[j - 1] + 1,       # insertion
                prev_row[j] + 1,           # deletion
                prev_row[j - 1] + cost,    # substitution
            ))
        prev_row = curr_row
    return prev_row[-1] / len(ref)


async def _verify_synthesis_async(history_id: str) -> dict:
    from sqlalchemy import select

    from app.models.synthesis_history import SynthesisHistory
    from app.services import whisper_transcriber

    async with worker_session() as db:
        result = await db.execute(
            select(SynthesisHistory).where(SynthesisHistory.id == history_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            logger.warning("verify_synthesis_history_missing", history_id=history_id)
            return {"history_id": history_id, "skipped": "missing"}
        if not row.output_path:
            logger.info("verify_synthesis_no_output_path", history_id=history_id)
            return {"history_id": history_id, "skipped": "no_output"}

        audio_path = Path(row.output_path)
        if not audio_path.exists():
            logger.info(
                "verify_synthesis_audio_missing",
                history_id=history_id,
                path=str(audio_path),
            )
            return {"history_id": history_id, "skipped": "audio_missing"}

        try:
            transcript = await whisper_transcriber.transcribe(audio_path)
        except Exception as exc:
            logger.warning(
                "verify_synthesis_transcribe_failed",
                history_id=history_id,
                error=str(exc),
            )
            return {"history_id": history_id, "skipped": "transcribe_failed"}

        wer = compute_wer(row.text or "", transcript)
        row.quality_wer = wer
        await db.commit()

        logger.info(
            "verify_synthesis_done",
            history_id=history_id,
            wer=round(wer, 4),
            flagged=wer > QUALITY_WER_FLAG_THRESHOLD,
        )
        return {"history_id": history_id, "wer": wer}


@celery_app.task(name="app.tasks.preferences.verify_synthesis")
def verify_synthesis(history_id: str) -> dict:
    """Whisper-transcribe a synthesis output and persist its WER."""
    logger.info("verify_synthesis_start", history_id=history_id)
    return run_async(_verify_synthesis_async(history_id))
