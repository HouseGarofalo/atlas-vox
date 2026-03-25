"""Training job and model version schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TrainingStart(BaseModel):
    provider_name: str | None = None  # Override profile's provider
    config: dict | None = None  # Provider-specific training config


class TrainingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    provider_name: str
    status: str
    progress: float
    error_message: str | None
    result_version_id: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TrainingJobListResponse(BaseModel):
    jobs: list[TrainingJobResponse]
    count: int


class ModelVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    version_number: int
    provider_model_id: str | None
    model_path: str | None
    config_json: str | None
    metrics_json: str | None
    created_at: datetime


class ModelVersionListResponse(BaseModel):
    versions: list[ModelVersionResponse]
    count: int
