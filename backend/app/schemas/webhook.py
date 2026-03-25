"""Webhook schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    events: str
    active: bool
    created_at: datetime
    updated_at: datetime


class WebhookListResponse(BaseModel):
    webhooks: list[WebhookResponse]
    count: int
