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
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3100", "http://localhost:5173"]

    # Database
    database_url: str = "sqlite+aiosqlite:///./atlas_vox.db"

    # Authentication
    auth_disabled: bool = True
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # Encryption — separate from JWT so rotating JWT secret doesn't break encrypted data.
    # If empty, falls back to jwt_secret_key for backward compatibility.
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    encryption_key: str = ""

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
    azure_cnv_company_name: str = "Atlas Vox"

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
    gpu_service_api_key: str = ""

    # Self-healing engine
    healing_enabled: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    @model_validator(mode="after")
    def validate_secrets(self) -> "Settings":
        """Ensure real secrets are set when authentication is enabled."""
        if not self.auth_disabled:
            if self.jwt_secret_key == "change-me-in-production":
                raise ValueError(
                    "jwt_secret_key must be changed from the default value when "
                    "AUTH_DISABLED is False. Set a strong random secret in JWT_SECRET_KEY."
                )
            if not self.encryption_key:
                raise ValueError(
                    "ENCRYPTION_KEY must be set when AUTH_DISABLED is False. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
        if self.is_production:
            if self.jwt_secret_key == "change-me-in-production":
                raise ValueError(
                    "jwt_secret_key must be changed from the default in production."
                )
            if not self.encryption_key:
                raise ValueError(
                    "ENCRYPTION_KEY must be set in production to protect provider API keys. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
            if self.encryption_key == self.jwt_secret_key:
                import warnings
                warnings.warn(
                    "ENCRYPTION_KEY and JWT_SECRET_KEY should be different values. "
                    "Rotating JWT keys will break encrypted provider configs if they share the same key.",
                    UserWarning,
                    stacklevel=2,
                )
            if "*" in self.cors_origins:
                import warnings
                warnings.warn(
                    "CORS_ORIGINS contains '*' in production — this allows requests from any origin. "
                    "Set explicit origins for security.",
                    UserWarning,
                    stacklevel=2,
                )
            localhost_origins = [o for o in self.cors_origins if "localhost" in o or "127.0.0.1" in o]
            if localhost_origins:
                import warnings
                warnings.warn(
                    f"CORS_ORIGINS contains localhost origins in production: {localhost_origins}. "
                    "Remove these and use your production domain instead.",
                    UserWarning,
                    stacklevel=2,
                )
        return self

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def app_version(self) -> str:
        try:
            from importlib.metadata import version
            return version("atlas-vox")
        except Exception:
            return "0.1.0-dev"


settings = Settings()
