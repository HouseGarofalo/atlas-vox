"""Tests for the provider registry."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.base import ProviderCapabilities
from app.services.provider_registry import (
    PROVIDER_CLASSES,
    PROVIDER_DISPLAY_NAMES,
    ProviderRegistry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_registry() -> ProviderRegistry:
    """Return a new ProviderRegistry instance (not the module singleton)."""
    return ProviderRegistry()


# ---------------------------------------------------------------------------
# get_provider
# ---------------------------------------------------------------------------

def test_registry_get_unknown_provider():
    from app.core.exceptions import NotFoundError
    registry = _fresh_registry()
    with pytest.raises(NotFoundError, match="Provider.*not found"):
        registry.get_provider("this_does_not_exist")


def test_registry_get_kokoro_instantiates():
    registry = _fresh_registry()
    provider = registry.get_provider("kokoro")
    assert provider is not None


def test_registry_get_provider_returns_same_instance():
    """Second call should return the cached instance, not a new one."""
    registry = _fresh_registry()
    p1 = registry.get_provider("kokoro")
    p2 = registry.get_provider("kokoro")
    assert p1 is p2


# ---------------------------------------------------------------------------
# list_available
# ---------------------------------------------------------------------------

def test_registry_list_available():
    registry = _fresh_registry()
    available = registry.list_available()
    # Must include at least the 9 core providers
    assert len(available) >= 9
    # Spot-check a few names
    for name in ("kokoro", "piper", "elevenlabs", "coqui_xtts", "styletts2"):
        assert name in available


# ---------------------------------------------------------------------------
# apply_config / get_provider_config
# ---------------------------------------------------------------------------

def test_registry_apply_config_stores_config():
    registry = _fresh_registry()
    config = {"api_key": "sk-test", "model": "v2"}
    registry.apply_config("elevenlabs", config)

    stored = registry.get_provider_config("elevenlabs")
    assert stored == config


def test_registry_apply_config_forces_provider_reload():
    """apply_config must evict the cached instance so the new config is picked up."""
    registry = _fresh_registry()

    # Warm up the cache
    p1 = registry.get_provider("kokoro")

    registry.apply_config("kokoro", {"custom_key": "val"})

    # After config change the cached instance must be cleared
    assert "kokoro" not in registry._instances

    # Getting it again should produce a fresh (potentially reconfigured) instance
    p2 = registry.get_provider("kokoro")
    assert p2 is not p1


def test_registry_get_provider_config_unknown_returns_empty():
    registry = _fresh_registry()
    assert registry.get_provider_config("no_such_provider") == {}


# ---------------------------------------------------------------------------
# list_all_known
# ---------------------------------------------------------------------------

def test_registry_list_all_known():
    registry = _fresh_registry()
    all_known = registry.list_all_known()

    assert len(all_known) >= 9

    # Each entry has the expected structure
    for entry in all_known:
        assert "name" in entry
        assert "display_name" in entry
        assert "provider_type" in entry
        assert "implemented" in entry


def test_registry_list_all_known_marks_implemented():
    registry = _fresh_registry()
    all_known = registry.list_all_known()

    implemented = {e["name"] for e in all_known if e["implemented"]}
    for name in PROVIDER_CLASSES:
        assert name in implemented, f"{name} should be marked as implemented"


# ---------------------------------------------------------------------------
# get_capabilities
# ---------------------------------------------------------------------------

async def test_registry_get_capabilities_kokoro():
    registry = _fresh_registry()
    caps = await registry.get_capabilities("kokoro")
    assert isinstance(caps, ProviderCapabilities)
    # Kokoro is CPU-only, should not require GPU
    assert caps.requires_gpu is False


async def test_registry_get_capabilities_unknown():
    from app.core.exceptions import NotFoundError
    registry = _fresh_registry()
    with pytest.raises(NotFoundError, match="Provider.*not found"):
        await registry.get_capabilities("totally_fake_provider")


# ---------------------------------------------------------------------------
# GPU provider registration
# ---------------------------------------------------------------------------

def test_registry_gpu_provider_registered():
    registry = _fresh_registry()

    mock_gpu_provider = MagicMock()
    registry._gpu_providers["fish_speech"] = mock_gpu_provider

    # list_available must include the GPU provider
    assert "fish_speech" in registry.list_available()

    # get_provider should return the GPU instance (not try to instantiate via PROVIDER_CLASSES)
    result = registry.get_provider("fish_speech")
    assert result is mock_gpu_provider
