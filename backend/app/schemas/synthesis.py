"""Synthesis schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SynthesisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    profile_id: str
    preset_id: str | None = None
    speed: float = Field(1.0, ge=0.5, le=2.0)
    pitch: float = Field(0.0, ge=-50.0, le=50.0)
    volume: float = Field(1.0, ge=0.0, le=2.0)
    output_format: str = "wav"  # wav, mp3, ogg
    ssml: bool = False  # If true, text is treated as SSML


class SynthesisResponse(BaseModel):
    id: str
    audio_url: str
    duration_seconds: float | None = None
    latency_ms: int
    profile_id: str
    provider_name: str


class BatchSynthesisRequest(BaseModel):
    lines: list[str] = Field(..., max_length=100)
    profile_id: str
    preset_id: str | None = None
    speed: float = 1.0
    pitch: float = 0.0
    output_format: str = "wav"


class CompareRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    profile_ids: list[str] = Field(..., min_length=2)
    speed: float = 1.0
    pitch: float = 0.0


class CompareResult(BaseModel):
    profile_id: str
    profile_name: str
    provider_name: str
    audio_url: str
    duration_seconds: float | None = None
    latency_ms: int


class CompareResponse(BaseModel):
    text: str
    results: list[CompareResult]
