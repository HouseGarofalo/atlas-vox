"""Provider schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProviderCapabilitiesSchema(BaseModel):
    supports_cloning: bool = False
    supports_fine_tuning: bool = False
    supports_streaming: bool = False
    supports_ssml: bool = False
    supports_zero_shot: bool = False
    supports_batch: bool = False
    requires_gpu: bool = False
    gpu_mode: str = "none"
    min_samples_for_cloning: int = 0
    max_text_length: int = 5000
    supported_languages: list[str] = ["en"]
    supported_output_formats: list[str] = ["wav"]


class ProviderHealthSchema(BaseModel):
    name: str
    healthy: bool
    latency_ms: int | None = None
    error: str | None = None


class ProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    display_name: str
    provider_type: str
    enabled: bool
    gpu_mode: str
    capabilities: ProviderCapabilitiesSchema | None = None
    health: ProviderHealthSchema | None = None
    created_at: datetime
    updated_at: datetime


class ProviderConfigUpdate(BaseModel):
    enabled: bool | None = None
    gpu_mode: str | None = None
    config_json: str | None = None


class ProviderListResponse(BaseModel):
    providers: list[ProviderResponse]
    count: int
