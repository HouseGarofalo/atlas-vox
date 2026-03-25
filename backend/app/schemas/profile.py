"""Voice profile schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    language: str = "en"
    provider_name: str
    tags: list[str] | None = None


class ProfileUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    language: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    language: str
    provider_name: str
    status: str
    tags: list[str] | None = None
    active_version_id: str | None
    sample_count: int = 0
    version_count: int = 0
    created_at: datetime
    updated_at: datetime


class ProfileListResponse(BaseModel):
    profiles: list[ProfileResponse]
    count: int
