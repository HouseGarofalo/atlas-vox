"""Quality assessment schemas — audio sample quality and training readiness."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QualityIssueSchema(BaseModel):
    """A single detected quality problem."""

    code: str = Field(..., description="Machine-readable issue code, e.g. 'clipping'")
    severity: str = Field(..., description="'error', 'warning', or 'info'")
    message: str = Field(..., description="Human-readable description")
    value: float | None = Field(None, description="Measured value that triggered the issue")
    threshold: float | None = Field(None, description="The threshold the value violated")


class AudioQualityReportSchema(BaseModel):
    """Full quality assessment of a single audio sample."""

    passed: bool = Field(..., description="True when no error-severity issues were found")
    score: float = Field(..., ge=0.0, le=100.0, description="Overall quality score 0–100")
    issues: list[QualityIssueSchema] = Field(default_factory=list)
    metrics: dict = Field(
        default_factory=dict,
        description=(
            "Raw audio metrics: snr_db, rms_db, peak_db, clipping_ratio, "
            "silence_ratio, duration, sample_rate"
        ),
    )


class TrainingReadinessSchema(BaseModel):
    """Assessment of whether a profile's samples are ready for training."""

    ready: bool = Field(..., description="True when the profile can proceed to training")
    score: float = Field(..., ge=0.0, le=100.0, description="Readiness score 0–100")
    sample_count: int = Field(..., ge=0, description="Number of samples evaluated")
    total_duration: float = Field(..., ge=0.0, description="Total audio duration in seconds")
    issues: list[QualityIssueSchema] = Field(default_factory=list)
    recommendations: list[str] = Field(
        default_factory=list,
        description="Human-readable actions to improve readiness",
    )


class VoiceQualityScoreSchema(BaseModel):
    """Post-training voice quality assessment."""

    overall: float = Field(..., ge=0.0, le=100.0, description="Weighted overall score")
    naturalness: float = Field(..., ge=0.0, le=100.0, description="Prosody/naturalness score")
    intelligibility: float = Field(..., ge=0.0, le=100.0, description="Spectral clarity score")
    speaker_similarity: float = Field(
        ..., ge=0.0, le=100.0,
        description="MFCC cosine similarity to original samples"
    )
    consistency: float = Field(
        ..., ge=0.0, le=100.0,
        description="How consistent the original samples are with each other"
    )
    details: dict = Field(
        default_factory=dict,
        description="Raw scoring details (cosine similarities, F0 variance, etc.)",
    )
