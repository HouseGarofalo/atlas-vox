"""API key schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    scopes: list[str] = ["read", "synthesize"]


class ApiKeyCreateResponse(BaseModel):
    """Returned once on creation — includes the full key (never shown again)."""

    id: str
    name: str
    key: str  # Full key, shown only once
    key_prefix: str
    scopes: list[str]
    created_at: datetime


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    key_prefix: str
    scopes: str
    active: bool
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyListResponse(BaseModel):
    api_keys: list[ApiKeyResponse]
    count: int
