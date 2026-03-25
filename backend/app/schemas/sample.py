"""Audio sample schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SampleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    filename: str
    original_filename: str
    format: str
    duration_seconds: float | None
    sample_rate: int | None
    file_size_bytes: int | None
    preprocessed: bool
    created_at: datetime


class SampleAnalysis(BaseModel):
    sample_id: str
    duration_seconds: float
    sample_rate: int
    pitch_mean: float | None = None
    pitch_std: float | None = None
    energy_mean: float | None = None
    energy_std: float | None = None


class SampleListResponse(BaseModel):
    samples: list[SampleResponse]
    count: int
