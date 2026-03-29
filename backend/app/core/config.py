"""Application configuration via Pydantic Settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "atlas-vox"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    log_format: str = "json"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database
    database_url: str = "sqlite+aiosqlite:///./atlas_vox.db"

    # Authentication
    auth_disabled: bool = True
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # Redis
    redis_url: str = "redis://localhost:6379/1"

    # Storage
    storage_path: Path = Path("./storage")

    # Provider: ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_model_id: str = "eleven_multilingual_v2"

    # Provider: Azure
    azure_speech_key: str = ""
    azure_speech_region: str = "eastus"

    # Provider: Coqui XTTS
    coqui_xtts_gpu_mode: str = "host_cpu"

    # Provider: StyleTTS2
    styletts2_gpu_mode: str = "host_cpu"

    # Provider: CosyVoice
    cosyvoice_gpu_mode: str = "host_cpu"

    # Provider: Kokoro
    kokoro_enabled: bool = True

    # Provider: Piper
    piper_enabled: bool = True
    piper_model_path: Path = Path("./storage/models/piper")

    # Provider: Dia
    dia_gpu_mode: str = "host_cpu"

    # Provider: Dia2
    dia2_gpu_mode: str = "host_cpu"

    # GPU Service (remote provider bridge)
    gpu_service_url: str = ""  # e.g., "http://host.docker.internal:8200"
    gpu_service_timeout: int = 120

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    @model_validator(mode="after")
    def validate_jwt_secret(self) -> "Settings":
        """Ensure a real JWT secret is set when authentication is enabled."""
        if not self.auth_disabled and self.jwt_secret_key == "change-me-in-production":
            raise ValueError(
                "jwt_secret_key must be changed from the default value when "
                "AUTH_DISABLED is False. Set a strong random secret in JWT_SECRET_KEY."
            )
        return self

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
