"""Pydantic schemas for the admin settings API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SystemSettingResponse(BaseModel):
    """Single system setting returned by the API."""

    id: str
    category: str
    key: str
    value: str  # Masked with ******** if is_secret
    value_type: str  # string, int, float, bool, json
    is_secret: bool
    description: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class SystemSettingUpdate(BaseModel):
    """Update a single system setting."""

    value: str
    value_type: str | None = None
    is_secret: bool | None = None
    description: str | None = None


class BulkSettingItem(BaseModel):
    """Single item in a bulk update."""

    key: str
    value: str
    value_type: str | None = None
    is_secret: bool | None = None
    description: str | None = None


class BulkSettingsUpdate(BaseModel):
    """Update multiple settings at once within a category."""

    category: str
    settings: list[BulkSettingItem] = Field(max_length=100)


class SystemInfoResponse(BaseModel):
    """System diagnostics information."""

    app_name: str
    app_env: str
    version: str
    debug: bool
    uptime_seconds: float
    database_type: str
    provider_count: int
    active_providers: int
    profile_count: int
    total_synthesis: int
    redis_connected: bool
    celery_connected: bool
    healing_enabled: bool
    healing_running: bool


class BackupResponse(BaseModel):
    """Encrypted settings backup."""

    data: str  # Encrypted JSON blob
    settings_count: int
    created_at: datetime


class RestoreRequest(BaseModel):
    """Restore settings from backup."""

    data: str  # Encrypted JSON blob
