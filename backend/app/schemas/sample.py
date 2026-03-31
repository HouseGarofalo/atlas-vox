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
    transcript: str | None = None
    transcript_source: str | None = None
    created_at: datetime


class SampleAnalysis(BaseModel):
    sample_id: str
    duration_seconds: float
    sample_rate: int
    pitch_mean: float | None = None
    pitch_std: float | None = None
    energy_mean: float | None = None
    energy_std: float | None = None


class PronunciationAssessment(BaseModel):
    sample_id: str
    accuracy_score: float
    fluency_score: float
    completeness_score: float
    pronunciation_score: float
    word_scores: list[dict] | None = None


class TranscribeRequest(BaseModel):
    locale: str = "en-US"


class TranscribeResponse(BaseModel):
    sample_id: str
    transcript: str
    source: str = "azure_stt"


class SampleListResponse(BaseModel):
    samples: list[SampleResponse]
    count: int
