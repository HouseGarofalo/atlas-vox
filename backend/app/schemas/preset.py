"""Persona preset schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PresetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    speed: float = Field(1.0, ge=0.5, le=2.0)
    pitch: float = Field(0.0, ge=-50.0, le=50.0)
    volume: float = Field(1.0, ge=0.0, le=2.0)


class PresetUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    speed: float | None = Field(None, ge=0.5, le=2.0)
    pitch: float | None = Field(None, ge=-50.0, le=50.0)
    volume: float | None = Field(None, ge=0.0, le=2.0)


class PresetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    speed: float
    pitch: float
    volume: float
    is_system: bool
    created_at: datetime
    updated_at: datetime


class PresetListResponse(BaseModel):
    presets: list[PresetResponse]
    count: int
