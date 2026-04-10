"""Pydantic schemas for the Audio Design Studio endpoints."""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AudioFormat(str, Enum):
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    FLAC = "flac"


class EffectType(str, Enum):
    NOISE_REDUCTION = "noise_reduction"
    NORMALIZE = "normalize"
    TRIM_SILENCE = "trim_silence"
    GAIN = "gain"


VALID_SAMPLE_RATES = {8000, 16000, 22050, 44100, 48000, 96000}

FILE_ID_PATTERN = re.compile(r"^[a-f0-9]{16}$")

MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class QualityIssueBrief(BaseModel):
    code: str
    severity: str
    message: str


class AudioQualityBrief(BaseModel):
    """Compact quality summary returned with uploads."""

    passed: bool
    score: float
    snr_db: float | None = None
    rms_db: float | None = None
    issues: list[QualityIssueBrief] = []


class AudioFileInfo(BaseModel):
    """Metadata returned for an uploaded or processed audio file."""

    file_id: str
    filename: str
    original_filename: str
    duration_seconds: float
    sample_rate: int
    channels: int
    format: str
    file_size_bytes: int
    audio_url: str


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

class AudioUploadResponse(BaseModel):
    file: AudioFileInfo
    quality: AudioQualityBrief | None = None


# ---------------------------------------------------------------------------
# Trim
# ---------------------------------------------------------------------------

class TrimRequest(BaseModel):
    file_id: str
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)

    @field_validator("file_id")
    @classmethod
    def validate_file_id(cls, v: str) -> str:
        if not FILE_ID_PATTERN.match(v):
            raise ValueError("file_id must be a 16-character hex string")
        return v

    @model_validator(mode="after")
    def validate_range(self) -> TrimRequest:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        return self


# ---------------------------------------------------------------------------
# Concat
# ---------------------------------------------------------------------------

class ConcatRequest(BaseModel):
    file_ids: list[str] = Field(min_length=2, max_length=50)
    crossfade_ms: int = Field(default=0, ge=0, le=5000)

    @field_validator("file_ids")
    @classmethod
    def validate_file_ids(cls, v: list[str]) -> list[str]:
        for fid in v:
            if not FILE_ID_PATTERN.match(fid):
                raise ValueError(f"Invalid file_id: {fid}")
        return v


# ---------------------------------------------------------------------------
# Effects chain
# ---------------------------------------------------------------------------

class EffectConfig(BaseModel):
    """A single effect to apply."""

    type: EffectType
    strength: float | None = Field(default=None, ge=0.0, le=1.0, description="0.0-1.0 for noise_reduction")
    target_db: float | None = Field(default=None, description="Target dB for normalize")
    threshold_db: float | None = Field(default=None, ge=-80, le=0, description="Threshold for trim_silence")
    gain_db: float | None = Field(default=None, ge=-60, le=60, description="Gain in dB")


class EffectsChainRequest(BaseModel):
    file_id: str
    effects: list[EffectConfig] = Field(min_length=1, max_length=20)

    @field_validator("file_id")
    @classmethod
    def validate_file_id(cls, v: str) -> str:
        if not FILE_ID_PATTERN.match(v):
            raise ValueError("file_id must be a 16-character hex string")
        return v


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

class ExportRequest(BaseModel):
    file_id: str
    format: AudioFormat = Field(default=AudioFormat.WAV)
    sample_rate: int | None = Field(default=None, description="Target sample rate, None keeps original")

    @field_validator("file_id")
    @classmethod
    def validate_file_id(cls, v: str) -> str:
        if not FILE_ID_PATTERN.match(v):
            raise ValueError("file_id must be a 16-character hex string")
        return v

    @field_validator("sample_rate")
    @classmethod
    def validate_sample_rate(cls, v: int | None) -> int | None:
        if v is not None and v not in VALID_SAMPLE_RATES:
            raise ValueError(f"Unsupported sample rate: {v}. Allowed: {sorted(VALID_SAMPLE_RATES)}")
        return v


class ExportResponse(BaseModel):
    file_id: str
    filename: str
    audio_url: str
    format: str
    sample_rate: int
    duration_seconds: float
    file_size_bytes: int


# ---------------------------------------------------------------------------
# File listing
# ---------------------------------------------------------------------------

class AudioFileListResponse(BaseModel):
    files: list[AudioFileInfo]
    count: int
    total: int = 0


# ---------------------------------------------------------------------------
# Isolate (standalone — not tied to a profile/sample)
# ---------------------------------------------------------------------------

class IsolateFileRequest(BaseModel):
    file_id: str

    @field_validator("file_id")
    @classmethod
    def validate_file_id(cls, v: str) -> str:
        if not FILE_ID_PATTERN.match(v):
            raise ValueError("file_id must be a 16-character hex string")
        return v


class IsolateFileResponse(BaseModel):
    file: AudioFileInfo


# ---------------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    file_id: str

    @field_validator("file_id")
    @classmethod
    def validate_file_id(cls, v: str) -> str:
        if not FILE_ID_PATTERN.match(v):
            raise ValueError("file_id must be a 16-character hex string")
        return v


class AnalyzeResponse(BaseModel):
    file_id: str
    duration_seconds: float
    sample_rate: int
    quality: AudioQualityBrief
    pitch_mean: float | None = None
    pitch_std: float | None = None
    energy_mean: float | None = None
    energy_std: float | None = None
    spectral_centroid_mean: float | None = None
    rms_db: float | None = None
