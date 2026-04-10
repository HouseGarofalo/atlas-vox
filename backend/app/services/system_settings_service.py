"""Service layer for system settings — CRUD with encryption for secrets."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_value, encrypt_value
from app.models.system_setting import SystemSetting

logger = structlog.get_logger("atlas_vox.services.system_settings")

SECRET_MASK = "••••••••"

# ── Default settings seeded on first startup ────────────────────────────
DEFAULT_SETTINGS: list[dict[str, Any]] = [
    # ── General ──────────────────────────────────────────────────────────
    {
        "category": "general",
        "key": "app_name",
        "value": "atlas-vox",
        "value_type": "string",
        "is_secret": False,
        "description": "Application display name",
    },
    {
        "category": "general",
        "key": "log_level",
        "value": "INFO",
        "value_type": "string",
        "is_secret": False,
        "description": "Logging level (DEBUG, INFO, WARNING, ERROR)",
    },
    {
        "category": "general",
        "key": "debug",
        "value": "false",
        "value_type": "bool",
        "is_secret": False,
        "description": "Enable debug mode",
    },
    {
        "category": "general",
        "key": "cors_origins",
        "value": '["http://localhost:3000","http://localhost:5173"]',
        "value_type": "json",
        "is_secret": False,
        "description": "Allowed CORS origins (JSON array)",
    },
    # ── Auth ──────────────────────────────────────────────────────────────
    {
        "category": "auth",
        "key": "auth_disabled",
        "value": "true",
        "value_type": "bool",
        "is_secret": False,
        "description": "Disable authentication (single-user mode)",
    },
    {
        "category": "auth",
        "key": "jwt_expire_minutes",
        "value": "1440",
        "value_type": "int",
        "is_secret": False,
        "description": "JWT token expiration in minutes",
    },
    {
        "category": "auth",
        "key": "jwt_secret_key",
        "value": "",
        "value_type": "string",
        "is_secret": True,
        "description": "JWT signing secret (leave empty to use .env value)",
    },
    {
        "category": "auth",
        "key": "encryption_key",
        "value": "",
        "value_type": "string",
        "is_secret": True,
        "description": "Encryption key for secrets at rest (leave empty to use .env value)",
    },
    # ── Storage ──────────────────────────────────────────────────────────
    {
        "category": "storage",
        "key": "storage_path",
        "value": "./storage",
        "value_type": "string",
        "is_secret": False,
        "description": "Base path for audio files and models",
    },
    {
        "category": "storage",
        "key": "max_upload_size_mb",
        "value": "50",
        "value_type": "int",
        "is_secret": False,
        "description": "Maximum upload file size in MB",
    },
    {
        "category": "storage",
        "key": "retention_days",
        "value": "7",
        "value_type": "int",
        "is_secret": False,
        "description": "Days to retain synthesized audio files",
    },
    # ── Providers ────────────────────────────────────────────────────────
    {
        "category": "providers",
        "key": "default_provider",
        "value": "kokoro",
        "value_type": "string",
        "is_secret": False,
        "description": "Default TTS provider",
    },
    {
        "category": "providers",
        "key": "gpu_service_url",
        "value": "",
        "value_type": "string",
        "is_secret": False,
        "description": "GPU worker service URL (e.g., http://host.docker.internal:8200)",
    },
    {
        "category": "providers",
        "key": "gpu_service_timeout",
        "value": "120",
        "value_type": "int",
        "is_secret": False,
        "description": "GPU service request timeout in seconds",
    },
    {
        "category": "providers",
        "key": "elevenlabs_api_key",
        "value": "",
        "value_type": "string",
        "is_secret": True,
        "description": "ElevenLabs API key",
    },
    {
        "category": "providers",
        "key": "azure_speech_key",
        "value": "",
        "value_type": "string",
        "is_secret": True,
        "description": "Azure Cognitive Services Speech key",
    },
    {
        "category": "providers",
        "key": "azure_speech_region",
        "value": "eastus",
        "value_type": "string",
        "is_secret": False,
        "description": "Azure Speech region",
    },
    # ── Healing ──────────────────────────────────────────────────────────
    {
        "category": "healing",
        "key": "enabled",
        "value": "true",
        "value_type": "bool",
        "is_secret": False,
        "description": "Enable self-healing engine",
    },
    {
        "category": "healing",
        "key": "health_interval",
        "value": "30",
        "value_type": "float",
        "is_secret": False,
        "description": "Health check interval in seconds",
    },
    {
        "category": "healing",
        "key": "telemetry_interval",
        "value": "15",
        "value_type": "float",
        "is_secret": False,
        "description": "Telemetry collection interval in seconds",
    },
    {
        "category": "healing",
        "key": "detection_interval",
        "value": "30",
        "value_type": "float",
        "is_secret": False,
        "description": "Anomaly detection loop interval in seconds",
    },
    {
        "category": "healing",
        "key": "health_failure_threshold",
        "value": "3",
        "value_type": "int",
        "is_secret": False,
        "description": "Consecutive health failures before triggering remediation",
    },
    {
        "category": "healing",
        "key": "error_rate_spike_multiplier",
        "value": "3.0",
        "value_type": "float",
        "is_secret": False,
        "description": "Error rate spike multiplier above baseline",
    },
    {
        "category": "healing",
        "key": "latency_p99_threshold_ms",
        "value": "5000",
        "value_type": "float",
        "is_secret": False,
        "description": "P99 latency threshold in milliseconds",
    },
    {
        "category": "healing",
        "key": "errors_per_minute_threshold",
        "value": "10",
        "value_type": "int",
        "is_secret": False,
        "description": "Error volume threshold per minute",
    },
    {
        "category": "healing",
        "key": "max_restarts_per_hour",
        "value": "5",
        "value_type": "int",
        "is_secret": False,
        "description": "Maximum service restarts per hour",
    },
    {
        "category": "healing",
        "key": "max_fixes_per_hour",
        "value": "3",
        "value_type": "int",
        "is_secret": False,
        "description": "Maximum MCP code fixes per hour",
    },
    {
        "category": "healing",
        "key": "mcp_server_path",
        "value": "",
        "value_type": "string",
        "is_secret": False,
        "description": "Path to Claude Code Agent MCP server",
    },
    {
        "category": "healing",
        "key": "project_root",
        "value": "",
        "value_type": "string",
        "is_secret": False,
        "description": "Project root path for MCP code fixes",
    },
    {
        "category": "healing",
        "key": "celery_backlog_threshold",
        "value": "100",
        "value_type": "int",
        "is_secret": False,
        "description": "Celery pending tasks threshold for backlog alert",
    },
    {
        "category": "healing",
        "key": "memory_threshold_mb",
        "value": "2048",
        "value_type": "int",
        "is_secret": False,
        "description": "Python process RSS memory threshold in MB",
    },
    {
        "category": "healing",
        "key": "disk_usage_threshold_pct",
        "value": "90",
        "value_type": "int",
        "is_secret": False,
        "description": "Disk usage percentage threshold for storage directory",
    },
    # ── Notifications ────────────────────────────────────────────────────
    {
        "category": "notifications",
        "key": "webhook_url",
        "value": "",
        "value_type": "string",
        "is_secret": False,
        "description": "Webhook URL for system notifications",
    },
    {
        "category": "notifications",
        "key": "notification_email",
        "value": "",
        "value_type": "string",
        "is_secret": False,
        "description": "Email address for system alerts",
    },
]


def _cast_typed_value(raw: str, value_type: str) -> Any:
    """Convert a raw string to the appropriate Python type."""
    if value_type == "int":
        return int(raw)
    elif value_type == "float":
        return float(raw)
    elif value_type == "bool":
        return raw.lower() in ("true", "1", "yes")
    elif value_type == "json":
        return json.loads(raw)
    return raw  # string


class SystemSettingsService:
    """Async CRUD for system settings with encryption for secrets."""

    # ── Read ─────────────────────────────────────────────────────────────

    @staticmethod
    async def get_all(
        db: AsyncSession, category: str | None = None, *, unmask: bool = False
    ) -> list[dict[str, Any]]:
        """Return all settings, optionally filtered by category.

        Secrets are masked unless *unmask* is True (internal use only).
        """
        query = select(SystemSetting).order_by(
            SystemSetting.category, SystemSetting.key
        )
        if category:
            query = query.where(SystemSetting.category == category)
        result = await db.execute(query)
        rows = result.scalars().all()
        return [_row_to_dict(r, unmask=unmask) for r in rows]

    @staticmethod
    async def get(
        db: AsyncSession, category: str, key: str, *, unmask: bool = False
    ) -> dict[str, Any] | None:
        """Return a single setting or None."""
        query = select(SystemSetting).where(
            SystemSetting.category == category,
            SystemSetting.key == key,
        )
        result = await db.execute(query)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _row_to_dict(row, unmask=unmask)

    @staticmethod
    async def get_typed(db: AsyncSession, category: str, key: str) -> Any:
        """Return the setting value cast to its declared type.

        Returns None if the setting does not exist.
        """
        query = select(SystemSetting).where(
            SystemSetting.category == category,
            SystemSetting.key == key,
        )
        result = await db.execute(query)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        raw = _decrypt_if_needed(row)
        return _cast_typed_value(raw, row.value_type)

    # ── Write ────────────────────────────────────────────────────────────

    @staticmethod
    async def set(
        db: AsyncSession,
        category: str,
        key: str,
        value: str,
        *,
        value_type: str | None = None,
        is_secret: bool | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create or update a setting (upsert)."""
        query = select(SystemSetting).where(
            SystemSetting.category == category,
            SystemSetting.key == key,
        )
        result = await db.execute(query)
        row = result.scalar_one_or_none()

        if row is None:
            row = SystemSetting(
                id=str(uuid.uuid4()),
                category=category,
                key=key,
                value_type=value_type or "string",
                is_secret=is_secret if is_secret is not None else False,
                description=description or "",
            )
            db.add(row)

        # Update fields
        if value_type is not None:
            row.value_type = value_type
        if is_secret is not None:
            row.is_secret = is_secret
        if description is not None:
            row.description = description

        # Encrypt if secret
        if row.is_secret and value:
            row.value = encrypt_value(value)
        else:
            row.value = value

        row.updated_at = datetime.now(UTC)
        await db.flush()
        logger.info("setting_updated", category=category, key=key)
        return _row_to_dict(row)

    @staticmethod
    async def set_bulk(
        db: AsyncSession,
        category: str,
        settings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Batch upsert multiple settings in one category."""
        results = []
        for item in settings:
            result = await SystemSettingsService.set(
                db,
                category=category,
                key=item["key"],
                value=item["value"],
                value_type=item.get("value_type"),
                is_secret=item.get("is_secret"),
                description=item.get("description"),
            )
            results.append(result)
        await db.flush()
        return results

    @staticmethod
    async def delete(db: AsyncSession, category: str, key: str) -> bool:
        """Delete a setting. Returns True if it existed."""
        result = await db.execute(
            delete(SystemSetting).where(
                SystemSetting.category == category,
                SystemSetting.key == key,
            )
        )
        deleted = result.rowcount > 0  # type: ignore[union-attr]
        if deleted:
            logger.info("setting_deleted", category=category, key=key)
        return deleted

    # ── Seeding ──────────────────────────────────────────────────────────

    @staticmethod
    async def seed_defaults(db: AsyncSession) -> int:
        """Seed default settings that don't yet exist.

        Only inserts — never overwrites existing values.  Returns count of
        new settings created.
        """
        created = 0
        for default in DEFAULT_SETTINGS:
            existing = await db.execute(
                select(SystemSetting.id).where(
                    SystemSetting.category == default["category"],
                    SystemSetting.key == default["key"],
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue  # Don't overwrite

            # For secrets, try to pull value from env-based Settings
            value = default["value"]
            if default["is_secret"] and not value:
                value = _get_env_value(default["category"], default["key"])

            row = SystemSetting(
                id=str(uuid.uuid4()),
                category=default["category"],
                key=default["key"],
                value=encrypt_value(value) if default["is_secret"] and value else value,
                value_type=default["value_type"],
                is_secret=default["is_secret"],
                description=default["description"],
            )
            db.add(row)
            created += 1

        if created:
            await db.flush()
            logger.info("settings_seeded", count=created)
        return created

    # ── Backup / Restore ─────────────────────────────────────────────────

    @staticmethod
    async def export_all(db: AsyncSession) -> list[dict[str, Any]]:
        """Export all settings for backup (values remain encrypted)."""
        query = select(SystemSetting).order_by(
            SystemSetting.category, SystemSetting.key
        )
        result = await db.execute(query)
        rows = result.scalars().all()
        return [
            {
                "category": r.category,
                "key": r.key,
                "value": r.value,  # Keep encryption intact
                "value_type": r.value_type,
                "is_secret": r.is_secret,
                "description": r.description,
            }
            for r in rows
        ]

    @staticmethod
    async def import_all(
        db: AsyncSession, settings_data: list[dict[str, Any]]
    ) -> int:
        """Import settings from backup. Overwrites existing values."""
        count = 0
        for item in settings_data:
            query = select(SystemSetting).where(
                SystemSetting.category == item["category"],
                SystemSetting.key == item["key"],
            )
            result = await db.execute(query)
            row = result.scalar_one_or_none()

            if row is None:
                row = SystemSetting(
                    id=str(uuid.uuid4()),
                    category=item["category"],
                    key=item["key"],
                )
                db.add(row)

            row.value = item["value"]
            row.value_type = item.get("value_type", "string")
            row.is_secret = item.get("is_secret", False)
            row.description = item.get("description", "")
            row.updated_at = datetime.now(UTC)
            count += 1

        await db.flush()
        logger.info("settings_imported", count=count)
        return count


# ── Helpers ──────────────────────────────────────────────────────────────


def _decrypt_if_needed(row: SystemSetting) -> str:
    """Decrypt a setting value if it's encrypted."""
    if row.is_secret and row.value:
        try:
            return decrypt_value(row.value)
        except Exception:
            return ""
    return row.value


def _row_to_dict(row: SystemSetting, *, unmask: bool = False) -> dict[str, Any]:
    """Convert a SystemSetting row to a response dict."""
    value = row.value
    if row.is_secret:
        if unmask:
            value = _decrypt_if_needed(row)
        else:
            value = SECRET_MASK if row.value else ""
    return {
        "id": row.id,
        "category": row.category,
        "key": row.key,
        "value": value,
        "value_type": row.value_type,
        "is_secret": row.is_secret,
        "description": row.description,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _get_env_value(category: str, key: str) -> str:
    """Try to pull a default value from the env-based Settings class."""
    try:
        from app.core.config import settings

        env_map: dict[tuple[str, str], str] = {
            ("auth", "jwt_secret_key"): settings.jwt_secret_key,
            ("auth", "encryption_key"): settings.encryption_key,
            ("providers", "elevenlabs_api_key"): settings.elevenlabs_api_key,
            ("providers", "azure_speech_key"): settings.azure_speech_key,
            ("providers", "azure_speech_region"): settings.azure_speech_region,
            ("providers", "gpu_service_url"): settings.gpu_service_url,
        }
        return env_map.get((category, key), "")
    except Exception:
        return ""
