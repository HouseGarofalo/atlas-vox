"""Synthesis schemas."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class OutputFormat(str, Enum):
    """Allowed audio output formats — constrained to prevent injection via ffmpeg."""
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    FLAC = "flac"


# Keys that must NEVER appear in voice_settings (prevents API key override)
VOICE_SETTINGS_BLOCKED_KEYS = frozenset({
    "api_key", "subscription_key", "model_id", "model_path",
    "gpu_mode", "enabled", "config_json", "secret_key",
    "access_token", "auth_token", "password",
})


class SynthesisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    profile_id: str
    preset_id: str | None = None
    speed: float = Field(1.0, ge=0.5, le=2.0)
    pitch: float = Field(0.0, ge=-50.0, le=50.0)
    volume: float = Field(1.0, ge=0.0, le=2.0)
    output_format: OutputFormat = OutputFormat.WAV
    ssml: bool = False  # If true, text is treated as SSML
    include_word_boundaries: bool = False
    voice_settings: dict | None = None  # Provider-specific voice tuning (e.g., stability, similarity_boost)
    version_id: str | None = None  # Synthesize with specific model version without activating it
    preprocess: bool = False  # If true, apply text preprocessing (number/date/abbreviation expansion)

    @field_validator("voice_settings")
    @classmethod
    def validate_voice_settings(cls, v: dict | None) -> dict | None:
        if v is None:
            return v
        blocked = set(v.keys()) & VOICE_SETTINGS_BLOCKED_KEYS
        if blocked:
            raise ValueError(f"Blocked keys in voice_settings: {', '.join(sorted(blocked))}")
        return v


class WordBoundaryItem(BaseModel):
    text: str
    offset_ms: int
    duration_ms: int
    word_index: int


class SynthesisResponse(BaseModel):
    id: str
    audio_url: str
    duration_seconds: float | None = None
    latency_ms: int
    profile_id: str
    provider_name: str
    word_boundaries: list[WordBoundaryItem] | None = None


class BatchSynthesisRequest(BaseModel):
    lines: list[str] = Field(..., max_length=100)
    profile_id: str
    preset_id: str | None = None
    speed: float = Field(1.0, ge=0.5, le=2.0)
    pitch: float = Field(0.0, ge=-50.0, le=50.0)
    output_format: OutputFormat = OutputFormat.WAV

    @field_validator("lines")
    @classmethod
    def validate_lines(cls, v: list[str]) -> list[str]:
        total_chars = sum(len(line) for line in v)
        if total_chars > 50000:
            raise ValueError(f"Total text length ({total_chars:,} chars) exceeds 50,000 char limit for batch")
        return v


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
