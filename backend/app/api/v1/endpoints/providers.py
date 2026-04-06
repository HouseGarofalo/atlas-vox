"""Provider management endpoints."""


import json
import time
from datetime import UTC, datetime, timezone

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession, require_scope
from app.core.encryption import ENC_PREFIX, decrypt_value, encrypt_value
from app.models.provider import Provider
from app.schemas.provider import (
    PROVIDER_CONFIG_SCHEMAS,
    PROVIDER_FIELD_DEFINITIONS,
    ProviderCapabilitiesSchema,
    ProviderConfigResponse,
    ProviderHealthSchema,
    ProviderListResponse,
    ProviderResponse,
    ProviderTestRequest,
    ProviderTestResponse,
    mask_secret,
)
from app.services.provider_registry import PROVIDER_DISPLAY_NAMES, provider_registry

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=ProviderListResponse)
async def list_providers(user: CurrentUser) -> ProviderListResponse:
    """List all known TTS providers with implementation status."""
    logger.info("list_providers_called")
    providers = []
    for info in provider_registry.list_all_known():
        caps = None
        if info["implemented"]:
            try:
                raw_caps = await provider_registry.get_capabilities(info["name"])
                caps = ProviderCapabilitiesSchema(**raw_caps.__dict__)
            except Exception as exc:
                logger.warning("provider_capabilities_failed", provider=info["name"], error=str(exc))

        providers.append(
            ProviderResponse(
                id=info["name"],
                name=info["name"],
                display_name=info["display_name"],
                provider_type=info["provider_type"],
                enabled=info["implemented"],
                gpu_mode=caps.gpu_mode if caps else "none",
                capabilities=caps,
                health=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
    logger.info("list_providers_returned", count=len(providers))
    return ProviderListResponse(providers=providers, count=len(providers))


@router.get("/{name}")
async def get_provider(name: str, user: CurrentUser) -> ProviderResponse:
    """Get details for a specific provider."""
    logger.info("get_provider_called", provider=name)
    known = {p["name"]: p for p in provider_registry.list_all_known()}
    if name not in known:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Provider '{name}' not found")

    info = known[name]
    caps = None
    if info["implemented"]:
        try:
            raw_caps = await provider_registry.get_capabilities(name)
            caps = ProviderCapabilitiesSchema(**raw_caps.__dict__)
        except Exception as exc:
            logger.warning("provider_capabilities_failed", provider=name, error=str(exc))

    return ProviderResponse(
        id=name,
        name=name,
        display_name=info["display_name"],
        provider_type=info["provider_type"],
        enabled=info["implemented"],
        gpu_mode=caps.gpu_mode if caps else "none",
        capabilities=caps,
        health=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@router.post("/{name}/health", response_model=ProviderHealthSchema)
async def check_provider_health(name: str, user: CurrentUser) -> ProviderHealthSchema:
    """Run a health check on a provider."""
    logger.info("check_provider_health_called", provider=name)
    available = provider_registry.list_available()
    if name not in available:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{name}' not available",
        )

    health = await provider_registry.health_check(name)
    logger.info("check_provider_health_returned", provider=name, healthy=health.healthy)
    return ProviderHealthSchema(**health.__dict__)


@router.get("/{name}/voices")
async def list_provider_voices(name: str, user: CurrentUser) -> dict:
    """List available voices for a provider."""
    logger.info("list_provider_voices_called", provider=name)
    available = provider_registry.list_available()
    if name not in available:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{name}' not available",
        )

    provider = provider_registry.get_provider(name)
    voices = await provider.list_voices()
    logger.info("list_provider_voices_returned", provider=name, count=len(voices))
    return {
        "provider": name,
        "voices": [{"voice_id": v.voice_id, "name": v.name, "language": v.language} for v in voices],
        "count": len(voices),
    }


# --- Admin Provider Configuration Endpoints ---


@router.get("/{name}/config", response_model=ProviderConfigResponse)
async def get_provider_config(
    name: str, db: DbSession, user: CurrentUser,
) -> ProviderConfigResponse:
    """Get the configuration for a provider, including its schema for UI rendering."""
    logger.info("get_provider_config_called", provider=name)
    if name not in PROVIDER_DISPLAY_NAMES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{name}' not found",
        )

    # Get DB row
    result = await db.execute(select(Provider).where(Provider.name == name))
    db_provider = result.scalar_one_or_none()

    # Build config dict starting from schema defaults
    schema_cls = PROVIDER_CONFIG_SCHEMAS.get(name)
    if schema_cls:
        defaults = schema_cls().model_dump()
    else:
        defaults = {}

    # Overlay DB-stored config (decrypt encrypted values)
    db_config: dict = {}
    if db_provider and db_provider.config_json:
        try:
            db_config = json.loads(db_provider.config_json)
            for key, val in db_config.items():
                if isinstance(val, str) and val.startswith(ENC_PREFIX):
                    try:
                        db_config[key] = decrypt_value(val)
                    except Exception:
                        logger.error("provider_config_decrypt_failed", provider=name, field=key)
        except (json.JSONDecodeError, TypeError):
            pass
    merged = {**defaults, **db_config}

    # Overlay registry runtime overrides
    runtime = provider_registry.get_provider_config(name)
    merged.update(runtime)

    # Mask secret fields
    field_defs = PROVIDER_FIELD_DEFINITIONS.get(name, [])
    secret_fields = {f.name for f in field_defs if f.is_secret}
    masked = {}
    for key, val in merged.items():
        if key in secret_fields and isinstance(val, str) and val:
            masked[key] = mask_secret(val)
        else:
            masked[key] = val

    return ProviderConfigResponse(
        enabled=db_provider.enabled if db_provider else False,
        gpu_mode=db_provider.gpu_mode if db_provider else "none",
        config=masked,
        config_schema=field_defs,
    )


class ProviderConfigUpdateRequest(BaseModel):
    enabled: bool | None = None
    gpu_mode: str | None = None
    config: dict | None = None


@router.put("/{name}/config", response_model=ProviderConfigResponse)
async def update_provider_config(
    name: str,
    body: ProviderConfigUpdateRequest,
    db: DbSession,
    user: CurrentUser,
    _admin=require_scope("admin"),
) -> ProviderConfigResponse:
    """Update the configuration for a provider."""
    if name not in PROVIDER_DISPLAY_NAMES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{name}' not found",
        )

    # Get or create DB row
    result = await db.execute(select(Provider).where(Provider.name == name))
    db_provider = result.scalar_one_or_none()
    if db_provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{name}' not found in database. Run seed_providers first.",
        )

    # Load existing config from DB and decrypt for comparison
    existing_config: dict = {}
    if db_provider.config_json:
        try:
            existing_config = json.loads(db_provider.config_json)
            for key, val in existing_config.items():
                if isinstance(val, str) and val.startswith(ENC_PREFIX):
                    try:
                        existing_config[key] = decrypt_value(val)
                    except Exception:
                        logger.error("provider_config_decrypt_failed", provider=name, field=key)
        except (json.JSONDecodeError, TypeError):
            pass

    # Handle incoming config — preserve secrets that are masked
    if body.config is not None:
        field_defs = PROVIDER_FIELD_DEFINITIONS.get(name, [])
        secret_fields = {f.name for f in field_defs if f.is_secret}
        new_config = dict(body.config)
        for key in secret_fields:
            if key in new_config:
                val = new_config[key]
                if isinstance(val, str) and val.startswith("****"):
                    # Keep existing value — user sent back the masked version
                    if key in existing_config:
                        new_config[key] = existing_config[key]
                    else:
                        del new_config[key]
        merged_config = {**existing_config, **new_config}
    else:
        merged_config = existing_config

    # Encrypt secret fields before persisting to DB
    field_defs = PROVIDER_FIELD_DEFINITIONS.get(name, [])
    secret_fields = {f.name for f in field_defs if f.is_secret}
    config_for_db = dict(merged_config)
    for key in secret_fields:
        if key in config_for_db:
            val = config_for_db[key]
            if isinstance(val, str) and val and not val.startswith(ENC_PREFIX):
                config_for_db[key] = encrypt_value(val)

    # Update DB row
    if body.enabled is not None:
        db_provider.enabled = body.enabled
    if body.gpu_mode is not None:
        db_provider.gpu_mode = body.gpu_mode
    db_provider.config_json = json.dumps(config_for_db)
    await db.flush()

    # Apply decrypted config to runtime registry (in-memory stays plaintext)
    provider_registry.apply_config(name, merged_config)

    logger.info("provider_config_updated", provider=name)

    # Return masked config
    field_defs = PROVIDER_FIELD_DEFINITIONS.get(name, [])
    secret_fields = {f.name for f in field_defs if f.is_secret}
    masked = {}
    for key, val in merged_config.items():
        if key in secret_fields and isinstance(val, str) and val:
            masked[key] = mask_secret(val)
        else:
            masked[key] = val

    return ProviderConfigResponse(
        enabled=db_provider.enabled,
        gpu_mode=db_provider.gpu_mode,
        config=masked,
        config_schema=field_defs,
    )


@router.post("/{name}/test", response_model=ProviderTestResponse)
async def test_provider(name: str, body: ProviderTestRequest, user: CurrentUser) -> ProviderTestResponse:
    """Test a provider by running a quick synthesis."""
    logger.info("test_provider_called", provider=name, text_length=len(body.text))
    available = provider_registry.list_available()
    if name not in available:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{name}' not available",
        )

    from app.providers.base import SynthesisSettings

    provider = provider_registry.get_provider(name)
    synth_settings = SynthesisSettings()

    # Determine voice_id: use provided or pick first available
    voice_id = body.voice_id
    if not voice_id:
        try:
            voices = await provider.list_voices()
            if voices:
                voice_id = voices[0].voice_id
            else:
                voice_id = "default"
        except Exception:
            voice_id = "default"

    start = time.perf_counter()
    try:
        result = await provider.synthesize(body.text, voice_id, synth_settings)
        latency = int((time.perf_counter() - start) * 1000)

        # Build a URL-friendly audio path
        audio_url = f"/storage/output/{result.audio_path.name}"

        logger.info("test_provider_succeeded", provider=name, latency_ms=latency)
        return ProviderTestResponse(
            success=True,
            audio_url=audio_url,
            duration_seconds=result.duration_seconds,
            latency_ms=latency,
        )
    except Exception as e:
        latency = int((time.perf_counter() - start) * 1000)
        logger.warning("provider_test_failed", provider=name, error=str(e))
        return ProviderTestResponse(
            success=False,
            latency_ms=latency,
            error=str(e),
        )
