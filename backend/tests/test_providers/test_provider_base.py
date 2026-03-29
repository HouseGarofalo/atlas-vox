"""Tests for provider base classes and registry."""

from __future__ import annotations

import pytest

from app.providers.base import (
    ProviderCapabilities,
    SynthesisSettings,
    TTSProvider,
)
from app.services.provider_registry import PROVIDER_CLASSES, provider_registry


class TestProviderRegistry:
    def test_all_providers_registered(self):
        assert len(PROVIDER_CLASSES) >= 9  # 9 local/cloud, GPU providers added dynamically
        expected_core = {"kokoro", "coqui_xtts", "piper", "elevenlabs", "azure_speech",
                         "styletts2", "cosyvoice", "dia", "dia2"}
        assert expected_core.issubset(set(PROVIDER_CLASSES.keys()))

    def test_list_available_returns_registered(self):
        available = provider_registry.list_available()
        assert "kokoro" in available
        assert len(available) >= 9

    def test_list_all_known_includes_metadata(self):
        all_known = provider_registry.list_all_known()
        assert len(all_known) >= 9
        for p in all_known:
            assert "name" in p
            assert "display_name" in p
            assert "provider_type" in p
            assert isinstance(p["implemented"], bool)
        # At least the 9 core providers should be implemented
        implemented = [p for p in all_known if p["implemented"]]
        assert len(implemented) >= 9

    def test_get_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            provider_registry.get_provider("nonexistent")

    def test_get_provider_returns_instance(self):
        provider = provider_registry.get_provider("kokoro")
        assert isinstance(provider, TTSProvider)

    def test_provider_singleton(self):
        p1 = provider_registry.get_provider("kokoro")
        p2 = provider_registry.get_provider("kokoro")
        assert p1 is p2


class TestProviderCapabilities:
    @pytest.mark.asyncio
    async def test_kokoro_capabilities(self):
        provider = provider_registry.get_provider("kokoro")
        caps = await provider.get_capabilities()
        assert isinstance(caps, ProviderCapabilities)
        assert caps.supports_cloning is False
        assert caps.gpu_mode == "none"
        assert "en" in caps.supported_languages

    @pytest.mark.asyncio
    async def test_coqui_capabilities(self):
        provider = provider_registry.get_provider("coqui_xtts")
        caps = await provider.get_capabilities()
        # Cloning and fine-tuning depend on TTS library being installed
        assert isinstance(caps.supports_cloning, bool)
        assert isinstance(caps.supports_fine_tuning, bool)
        assert isinstance(caps, ProviderCapabilities)

    @pytest.mark.asyncio
    async def test_elevenlabs_capabilities(self):
        provider = provider_registry.get_provider("elevenlabs")
        caps = await provider.get_capabilities()
        assert caps.supports_cloning is True
        assert caps.supports_streaming is True
        assert caps.gpu_mode == "none"  # Cloud provider

    @pytest.mark.asyncio
    async def test_piper_capabilities(self):
        provider = provider_registry.get_provider("piper")
        caps = await provider.get_capabilities()
        assert caps.supports_cloning is False
        assert caps.supports_fine_tuning is False  # Piper CPU doesn't support fine-tuning
        assert caps.gpu_mode == "none"


class TestSynthesisSettings:
    def test_default_settings(self):
        s = SynthesisSettings()
        assert s.speed == 1.0
        assert s.pitch == 0.0
        assert s.volume == 1.0
        assert s.output_format == "wav"
