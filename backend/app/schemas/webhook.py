"""Webhook schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WebhookCreate(BaseModel):
    url: str = Field(..., max_length=1000)
    events: list[str] = Field(..., min_length=1)  # training.completed, training.failed
    secret: str | None = None


class WebhookUpdate(BaseModel):
    url: str | None = Field(None, max_length=1000)
    events: list[str] | None = None
    secret: str | None = None
    active: bool | None = None


class WebhookResponse(BaseModel):
    """Webhook response schema.

    The ``secret`` field is intentionally excluded — it is never returned to
    callers.  Use ``secret_set`` to determine whether a signing secret has been
    configured without exposing the value.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    events: str
    active: bool
    created_at: datetime
    updated_at: datetime
    # Indicates whether a secret is configured, without exposing the value.
    secret_set: bool = False

    @model_validator(mode="before")
    @classmethod
    def _derive_secret_set(cls, data: Any) -> Any:
        """Populate secret_set from the ORM object or raw dict without leaking the value."""
        if hasattr(data, "secret"):
            # ORM object — read the attribute directly then strip it from the
            # namespace so it never reaches a response field.
            object.__setattr__(data, "_secret_set", bool(data.secret))
            # Build a plain dict so Pydantic doesn't accidentally map `secret`.
            return {
                "id": data.id,
                "url": data.url,
                "events": data.events,
                "active": data.active,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
                "secret_set": bool(data.secret),
            }
        if isinstance(data, dict):
            # Ensure the raw secret is never forwarded; derive secret_set instead.
            secret = data.pop("secret", None)
            data.setdefault("secret_set", bool(secret))
        return data


class WebhookListResponse(BaseModel):
    webhooks: list[WebhookResponse]
    count: int
