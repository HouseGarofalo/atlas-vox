"""Service layer for synthesis feedback (SL-25)."""

from __future__ import annotations

import json

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.synthesis_feedback import SynthesisFeedback
from app.models.synthesis_history import SynthesisHistory

logger = structlog.get_logger(__name__)


async def create_feedback(
    db: AsyncSession,
    history_id: str,
    rating: str,
    tags: list[str] | None = None,
    note: str | None = None,
    user_id: str | None = None,
) -> SynthesisFeedback:
    """Persist a thumbs up/down rating for a synthesis history row.

    Raises ``NotFoundError`` if ``history_id`` does not map to an existing
    row.  The caller is responsible for validating the rating value.
    """
    result = await db.execute(
        select(SynthesisHistory).where(SynthesisHistory.id == history_id)
    )
    history = result.scalar_one_or_none()
    if history is None:
        raise NotFoundError("SynthesisHistory", history_id)

    feedback = SynthesisFeedback(
        history_id=history_id,
        rating=rating,
        tags=json.dumps(tags) if tags is not None else None,
        note=note,
        user_id=user_id,
    )
    db.add(feedback)
    await db.flush()

    logger.info(
        "synthesis_feedback_created",
        feedback_id=feedback.id,
        history_id=history_id,
        rating=rating,
        tag_count=len(tags) if tags else 0,
    )
    return feedback


async def list_feedback_for_history(
    db: AsyncSession, history_id: str
) -> list[SynthesisFeedback]:
    """Return all feedback entries for a given synthesis history row.

    Returns an empty list if the history row has no feedback (or does not
    exist) — the endpoint layer handles 404 separately when needed.
    """
    result = await db.execute(
        select(SynthesisFeedback)
        .where(SynthesisFeedback.history_id == history_id)
        .order_by(SynthesisFeedback.created_at.desc())
    )
    return list(result.scalars().all())


async def aggregate_feedback_for_profile(
    db: AsyncSession, profile_id: str
) -> dict[str, int]:
    """Count up/down feedback for all history rows belonging to a profile.

    Returns ``{"up": int, "down": int, "total": int}``.
    """
    stmt = (
        select(SynthesisFeedback.rating, func.count(SynthesisFeedback.id))
        .join(
            SynthesisHistory,
            SynthesisHistory.id == SynthesisFeedback.history_id,
        )
        .where(SynthesisHistory.profile_id == profile_id)
        .group_by(SynthesisFeedback.rating)
    )
    result = await db.execute(stmt)
    counts: dict[str, int] = {"up": 0, "down": 0}
    for rating, cnt in result.all():
        if rating in counts:
            counts[rating] = int(cnt)
    counts["total"] = counts["up"] + counts["down"]
    return counts


def feedback_to_response_dict(row: SynthesisFeedback) -> dict:
    """Serialise a row into a dict suitable for ``FeedbackResponse``."""
    tags: list[str] | None = None
    if row.tags:
        try:
            tags = json.loads(row.tags)
            if not isinstance(tags, list):
                tags = None
        except (ValueError, TypeError):
            tags = None
    return {
        "id": row.id,
        "history_id": row.history_id,
        "rating": row.rating,
        "tags": tags,
        "note": row.note,
        "user_id": row.user_id,
        "created_at": row.created_at,
    }
