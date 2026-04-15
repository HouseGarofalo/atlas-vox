"""Provider schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ProviderCapabilitiesSchema(BaseModel):
    supports_cloning: bool = False
    supports_fine_tuning: bool = False
    supports_streaming: bool = False
    supports_ssml: bool = False
    supports_zero_shot: bool = False
    supports_batch: bool = False
    supports_word_boundaries: bool = False
    supports_pronunciation_assessment: bool = False
    supports_transcription: bool = False
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


# --- Per-provider config schemas ---


class ElevenLabsConfig(BaseModel):
    api_key: str = ""
    model_id: str = "eleven_multilingual_v2"
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = False


class AzureSpeechConfig(BaseModel):
    subscription_key: str = ""
    region: str = "eastus"
    auth_mode: str = "auto"  # "api_key", "entra_token", "auto"
    resource_id: str = ""  # Full ARM resource ID for Entra ID composite token
    endpoint: str = ""  # Custom domain endpoint URL
    tenant_id: str = ""  # Azure AD tenant ID (for service principal)
    client_id: str = ""  # Azure AD app/client ID (for service principal)
    client_secret: str = ""  # Azure AD client secret (for service principal)


class CoquiXttsConfig(BaseModel):
    gpu_mode: str = "host_cpu"


class StyleTTS2Config(BaseModel):
    gpu_mode: str = "host_cpu"


class CosyVoiceConfig(BaseModel):
    gpu_mode: str = "host_cpu"


class PiperConfig(BaseModel):
    model_path: str = "./storage/models/piper"


class KokoroConfig(BaseModel):
    pass


class DiaConfig(BaseModel):
    gpu_mode: str = "host_cpu"


class Dia2Config(BaseModel):
    gpu_mode: str = "host_cpu"


# --- Field schema for dynamic UI rendering ---


class ProviderFieldSchema(BaseModel):
    name: str
    field_type: str  # "text", "password", "select"
    label: str
    required: bool = False
    is_secret: bool = False
    options: list[str] | None = None
    default: str | None = None


PROVIDER_CONFIG_SCHEMAS: dict[str, type[BaseModel]] = {
    "elevenlabs": ElevenLabsConfig,
    "azure_speech": AzureSpeechConfig,
    "coqui_xtts": CoquiXttsConfig,
    "styletts2": StyleTTS2Config,
    "cosyvoice": CosyVoiceConfig,
    "piper": PiperConfig,
    "kokoro": KokoroConfig,
    "dia": DiaConfig,
    "dia2": Dia2Config,
}

_GPU_MODE_OPTIONS = ["host_cpu", "docker_gpu", "auto"]
_AZURE_REGION_OPTIONS = [
    # North America
    "---North America",
    "eastus", "eastus2", "westus", "westus2", "westus3",
    "centralus", "northcentralus", "southcentralus", "westcentralus",
    "canadacentral", "canadaeast",
    # Europe
    "---Europe",
    "northeurope", "westeurope", "uksouth", "ukwest",
    "francecentral", "germanywestcentral", "norwayeast",
    "swedencentral", "switzerlandnorth", "polandcentral",
    "italynorth", "spaincentral",
    # Asia Pacific
    "---Asia Pacific",
    "eastasia", "southeastasia", "japaneast", "japanwest",
    "koreacentral", "koreasouth", "centralindia", "southindia",
    "westindia",
    # Middle East & Africa
    "---Middle East & Africa",
    "uaenorth", "southafricanorth", "qatarcentral", "israelcentral",
    # South America
    "---South America",
    "brazilsouth", "brazilsoutheast",
    # Australia
    "---Australia",
    "australiaeast", "australiasoutheast", "australiacentral",
]

_ELEVENLABS_MODEL_OPTIONS = [
    "eleven_multilingual_v2",
    "eleven_turbo_v2_5",
    "eleven_flash_v2_5",
]

_AZURE_AUTH_MODE_OPTIONS = ["auto", "api_key", "entra_token"]

PROVIDER_FIELD_DEFINITIONS: dict[str, list[ProviderFieldSchema]] = {
    "elevenlabs": [
        ProviderFieldSchema(
            name="api_key", field_type="password", label="API Key",
            required=True, is_secret=True,
        ),
        ProviderFieldSchema(
            name="model_id", field_type="select", label="Model",
            options=_ELEVENLABS_MODEL_OPTIONS,
            default="eleven_multilingual_v2",
        ),
        ProviderFieldSchema(
            name="stability", field_type="text", label="Stability (0.0–1.0)",
            default="0.5",
        ),
        ProviderFieldSchema(
            name="similarity_boost", field_type="text", label="Similarity Boost (0.0–1.0)",
            default="0.75",
        ),
        ProviderFieldSchema(
            name="style", field_type="text", label="Style Exaggeration (0.0–1.0)",
            default="0.0",
        ),
        ProviderFieldSchema(
            name="use_speaker_boost", field_type="select", label="Speaker Boost",
            options=["false", "true"],
            default="false",
        ),
    ],
    "azure_speech": [
        ProviderFieldSchema(
            name="auth_mode", field_type="select", label="Auth Mode",
            options=_AZURE_AUTH_MODE_OPTIONS, default="auto",
        ),
        ProviderFieldSchema(
            name="subscription_key", field_type="password", label="Subscription Key (optional with Entra ID)",
            required=False, is_secret=True,
        ),
        ProviderFieldSchema(
            name="region", field_type="select", label="Region",
            options=_AZURE_REGION_OPTIONS, default="eastus",
        ),
        ProviderFieldSchema(
            name="resource_id", field_type="text",
            label="Resource ID (ARM path, required for Entra ID)",
        ),
        ProviderFieldSchema(
            name="endpoint", field_type="text",
            label="Custom Endpoint URL (for Entra ID / AI Foundry)",
        ),
        ProviderFieldSchema(
            name="tenant_id", field_type="text",
            label="Tenant ID (for Service Principal auth)",
        ),
        ProviderFieldSchema(
            name="client_id", field_type="text",
            label="Client / App ID (for custom app registration or Service Principal)",
        ),
        ProviderFieldSchema(
            name="client_secret", field_type="password",
            label="Client Secret (for Service Principal auth)",
            is_secret=True,
        ),
    ],
    "coqui_xtts": [
        ProviderFieldSchema(
            name="gpu_mode", field_type="select", label="GPU Mode",
            options=_GPU_MODE_OPTIONS, default="host_cpu",
        ),
    ],
    "styletts2": [
        ProviderFieldSchema(
            name="gpu_mode", field_type="select", label="GPU Mode",
            options=_GPU_MODE_OPTIONS, default="host_cpu",
        ),
    ],
    "cosyvoice": [
        ProviderFieldSchema(
            name="gpu_mode", field_type="select", label="GPU Mode",
            options=_GPU_MODE_OPTIONS, default="host_cpu",
        ),
    ],
    "dia": [
        ProviderFieldSchema(
            name="gpu_mode", field_type="select", label="GPU Mode",
            options=_GPU_MODE_OPTIONS, default="host_cpu",
        ),
    ],
    "dia2": [
        ProviderFieldSchema(
            name="gpu_mode", field_type="select", label="GPU Mode",
            options=_GPU_MODE_OPTIONS, default="host_cpu",
        ),
    ],
    "piper": [
        ProviderFieldSchema(
            name="model_path", field_type="text", label="Model Path",
            default="./storage/models/piper",
        ),
    ],
    "kokoro": [],
}


# --- Admin response/request schemas ---


class ProviderConfigResponse(BaseModel):
    enabled: bool
    gpu_mode: str
    config: dict[str, Any]
    config_schema: list[ProviderFieldSchema]


class ProviderTestRequest(BaseModel):
    text: str = "Hello, this is a test of the text to speech system."
    voice_id: str | None = None


class ProviderTestResponse(BaseModel):
    success: bool
    audio_url: str | None = None
    duration_seconds: float | None = None
    latency_ms: int = 0
    error: str | None = None


# --- Masking utility ---


def mask_secret(value: str) -> str:
    if not value or len(value) <= 4:
        return "****"
    return "****" + value[-4:]
