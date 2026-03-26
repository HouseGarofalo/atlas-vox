"""Provider discovery and management."""

from __future__ import annotations

import json

import structlog
from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.provider import Provider
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
        self._config_overrides: dict[str, dict] = {}

    def get_provider(self, name: str) -> TTSProvider:
        """Get or create a provider instance by name."""
        if name not in PROVIDER_CLASSES:
            raise ValueError(f"Unknown provider: {name}")

        if name not in self._instances:
            instance = PROVIDER_CLASSES[name]()
            if name in self._config_overrides:
                instance.configure(self._config_overrides[name])
            self._instances[name] = instance
            logger.info("provider_instantiated", provider=name)

        return self._instances[name]

    def apply_config(self, name: str, config: dict) -> None:
        """Store config overrides and force provider reload."""
        self._config_overrides[name] = config
        self._instances.pop(name, None)
        logger.info("provider_config_applied", provider=name)

    def get_provider_config(self, name: str) -> dict:
        """Return stored config overrides for a provider."""
        return self._config_overrides.get(name, {})

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


async def seed_providers() -> None:
    """Ensure all known providers exist in the database."""
    async with async_session_factory() as session:
        for name, display_name in PROVIDER_DISPLAY_NAMES.items():
            result = await session.execute(select(Provider).where(Provider.name == name))
            existing = result.scalar_one_or_none()
            if existing is None:
                provider = Provider(
                    name=name,
                    display_name=display_name,
                    provider_type=PROVIDER_TYPES.get(name, "local"),
                    enabled=False,
                    gpu_mode="none",
                )
                session.add(provider)
                logger.info("provider_seeded", provider=name)
        await session.commit()


async def load_provider_configs() -> None:
    """Load stored provider configs from DB into the registry on startup."""
    loaded: list[str] = []
    skipped: list[str] = []
    async with async_session_factory() as session:
        result = await session.execute(
            select(Provider).where(Provider.config_json.isnot(None))
        )
        providers = result.scalars().all()
        for p in providers:
            try:
                config = json.loads(p.config_json)
                if config:  # skip empty dicts
                    provider_registry.apply_config(p.name, config)
                    loaded.append(p.name)
                    logger.info("provider_config_loaded", provider=p.name)
                else:
                    skipped.append(p.name)
            except (json.JSONDecodeError, TypeError):
                skipped.append(p.name)
                logger.warning("provider_config_invalid_json", provider=p.name)

    if loaded:
        logger.info(
            "provider_configs_restored",
            count=len(loaded),
            providers=loaded,
        )
    else:
        logger.info("provider_configs_none_persisted")
