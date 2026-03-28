"""Tests for RemoteProvider with offline service."""

from __future__ import annotations

import pytest

from app.providers.remote_provider import RemoteProvider


@pytest.mark.asyncio
async def test_remote_provider_health_offline():
    """RemoteProvider health check returns unhealthy when service is offline."""
    rp = RemoteProvider("test", "Test", "http://localhost:99999", timeout=2)
    health = await rp.health_check()
    assert health.healthy is False
    assert health.error is not None
    # Error message varies by OS but should indicate connection failure
    error_lower = health.error.lower()
    assert "connect" in error_lower or "refused" in error_lower or "not reachable" in error_lower


@pytest.mark.asyncio
async def test_remote_provider_list_voices_offline():
    """RemoteProvider returns empty voices when service is offline."""
    rp = RemoteProvider("test", "Test", "http://localhost:99999", timeout=2)
    voices = await rp.list_voices()
    assert voices == []


@pytest.mark.asyncio
async def test_remote_provider_get_capabilities_offline():
    """RemoteProvider returns default capabilities when service is offline."""
    rp = RemoteProvider("test", "Test", "http://localhost:99999", timeout=2)
    caps = await rp.get_capabilities()
    # Should return sensible defaults rather than raising
    assert caps.supports_cloning is True
    assert caps.requires_gpu is True
    assert caps.gpu_mode == "docker_gpu"


@pytest.mark.asyncio
async def test_remote_provider_capabilities_cached():
    """RemoteProvider caches capabilities after first call."""
    rp = RemoteProvider("test", "Test", "http://localhost:99999", timeout=2)
    caps1 = await rp.get_capabilities()
    caps2 = await rp.get_capabilities()
    assert caps1 is caps2  # Same object — cached


@pytest.mark.asyncio
async def test_remote_provider_attributes():
    """RemoteProvider stores name/display_name/url correctly."""
    rp = RemoteProvider("my_provider", "My Provider", "http://gpu.local:8080/", timeout=30)
    assert rp._name == "my_provider"
    assert rp._display_name == "My Provider"
    assert rp._base_url == "http://gpu.local:8080"  # trailing slash stripped
    assert rp._timeout == 30
