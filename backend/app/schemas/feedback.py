"""Synthesis feedback schemas (SL-25)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.synthesis_feedback import VALID_RATINGS


class FeedbackCreate(BaseModel):
    """Inbound payload for POST /synthesis/{history_id}/feedback."""

    rating: str = Field(..., description="Either 'up' or 'down'")
    tags: list[str] | None = Field(
        default=None,
        description="Optional free-form labels, e.g. ['too_fast', 'robotic']",
    )
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("rating")
    @classmethod
    def _check_rating(cls, v: str) -> str:
        if v not in VALID_RATINGS:
            raise ValueError(
                f"rating must be one of {sorted(VALID_RATINGS)}, got '{v}'"
            )
        return v

    @field_validator("tags")
    @classmethod
    def _check_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        # Cap tag count and length to keep storage bounded.
        if len(v) > 20:
            raise ValueError("tags may contain at most 20 entries")
        for t in v:
            if not isinstance(t, str) or not t.strip():
                raise ValueError("each tag must be a non-empty string")
            if len(t) > 50:
                raise ValueError("each tag must be at most 50 chars")
        return [t.strip() for t in v]


class FeedbackResponse(BaseModel):
    """Serialised SynthesisFeedback row returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    history_id: str
    rating: str
    tags: list[str] | None = None
    note: str | None = None
    user_id: str | None = None
    created_at: datetime


class ProfileFeedbackSummary(BaseModel):
    """Aggregate counts for a voice profile.

    Returned by ``GET /profiles/{profile_id}/feedback-summary``.
    """

    profile_id: str
    up: int = Field(..., ge=0)
    down: int = Field(..., ge=0)
    total: int = Field(..., ge=0)
