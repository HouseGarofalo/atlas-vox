"""Provider discovery and management."""

from __future__ import annotations

import structlog

from app.providers.azure_speech import AzureSpeechProvider
from app.providers.base import ProviderCapabilities, ProviderHealth, TTSProvider
from app.providers.coqui_xtts import CoquiXTTSProvider
from app.providers.cosyvoice import CosyVoiceProvider
from app.providers.dia import DiaProvider
from app.providers.dia2 import Dia2Provider
from app.providers.elevenlabs import ElevenLabsProvider
from app.providers.kokoro_tts import KokoroTTSProvider
from app.providers.piper_tts import PiperTTSProvider
from app.providers.styletts2 import StyleTTS2Provider

logger = structlog.get_logger(__name__)

# Registry of all 9 available providers
PROVIDER_CLASSES: dict[str, type[TTSProvider]] = {
    "kokoro": KokoroTTSProvider,
    "coqui_xtts": CoquiXTTSProvider,
    "piper": PiperTTSProvider,
    "elevenlabs": ElevenLabsProvider,
    "azure_speech": AzureSpeechProvider,
    "styletts2": StyleTTS2Provider,
    "cosyvoice": CosyVoiceProvider,
    "dia": DiaProvider,
    "dia2": Dia2Provider,
}

PROVIDER_DISPLAY_NAMES: dict[str, str] = {
    "kokoro": "Kokoro",
    "coqui_xtts": "Coqui XTTS v2",
    "piper": "Piper",
    "elevenlabs": "ElevenLabs",
    "azure_speech": "Azure AI Speech",
    "styletts2": "StyleTTS2",
    "cosyvoice": "CosyVoice",
    "dia": "Nari-labs Dia",
    "dia2": "Nari-labs Dia2",
}

PROVIDER_TYPES: dict[str, str] = {
    "kokoro": "local",
    "coqui_xtts": "local",
    "piper": "local",
    "elevenlabs": "cloud",
    "azure_speech": "cloud",
    "styletts2": "local",
    "cosyvoice": "local",
    "dia": "local",
    "dia2": "local",
}


class ProviderRegistry:
    """Manages provider instances and provides discovery."""

    def __init__(self) -> None:
        self._instances: dict[str, TTSProvider] = {}

    def get_provider(self, name: str) -> TTSProvider:
        """Get or create a provider instance by name."""
        if name not in PROVIDER_CLASSES:
            raise ValueError(f"Unknown provider: {name}")

        if name not in self._instances:
            self._instances[name] = PROVIDER_CLASSES[name]()
            logger.info("provider_instantiated", provider=name)

        return self._instances[name]

    def list_available(self) -> list[str]:
        """List all registered provider names."""
        return list(PROVIDER_CLASSES.keys())

    def list_all_known(self) -> list[dict]:
        """List all known providers (even those not yet implemented)."""
        result = []
        for name in PROVIDER_DISPLAY_NAMES:
            result.append({
                "name": name,
                "display_name": PROVIDER_DISPLAY_NAMES[name],
                "provider_type": PROVIDER_TYPES.get(name, "local"),
                "implemented": name in PROVIDER_CLASSES,
            })
        return result

    async def get_capabilities(self, name: str) -> ProviderCapabilities:
        """Get capabilities for a provider."""
        provider = self.get_provider(name)
        return await provider.get_capabilities()

    async def health_check(self, name: str) -> ProviderHealth:
        """Run health check on a provider."""
        try:
            provider = self.get_provider(name)
            return await provider.health_check()
        except Exception as e:
            return ProviderHealth(name=name, healthy=False, error=str(e))


# Singleton registry
provider_registry = ProviderRegistry()
