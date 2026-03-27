"""Configuration for the Atlas Vox GPU Service."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """GPU service settings.

    All settings can be overridden via environment variables with the ``GPU_`` prefix.
    For example, ``GPU_PORT=8201`` sets the port to 8201.
    """

    host: str = "0.0.0.0"
    port: int = 8200
    storage_path: str = "./storage"
    default_device: str = "cuda:0"
    device_map: dict[str, str] = {}
    auto_load_providers: list[str] = []
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    log_level: str = "INFO"

    model_config = {
        "env_prefix": "GPU_",
        "env_nested_delimiter": "__",
    }


settings = Settings()
