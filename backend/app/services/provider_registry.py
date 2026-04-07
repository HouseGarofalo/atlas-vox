"""Provider discovery and management."""

from __future__ import annotations

import json

import structlog
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.encryption import ENC_PREFIX, decrypt_value
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
        self._gpu_providers: dict[str, TTSProvider] = {}

    def get_provider(self, name: str) -> TTSProvider:
        """Get or create a provider instance by name."""
        # Check GPU providers first (they are pre-instantiated)
        if name in self._gpu_providers:
            return self._gpu_providers[name]

        if name not in PROVIDER_CLASSES:
            from app.core.exceptions import NotFoundError
            raise NotFoundError("Provider", name)

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
        """List all registered provider names (local + GPU)."""
        names = list(PROVIDER_CLASSES.keys())
        for name in self._gpu_providers:
            if name not in names:
                names.append(name)
        return names

    def list_all_known(self) -> list[dict]:
        """List all known providers (local, cloud, and GPU)."""
        result = []
        for name in PROVIDER_DISPLAY_NAMES:
            result.append({
                "name": name,
                "display_name": PROVIDER_DISPLAY_NAMES[name],
                "provider_type": PROVIDER_TYPES.get(name, "local"),
                "implemented": name in PROVIDER_CLASSES or name in self._gpu_providers,
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
                    # Decrypt any values that carry the enc: prefix
                    for key, val in config.items():
                        if isinstance(val, str) and val.startswith(ENC_PREFIX):
                            try:
                                config[key] = decrypt_value(val)
                            except Exception:
                                logger.error(
                                    "provider_config_decrypt_failed",
                                    provider=p.name,
                                    field=key,
                                )
                                # Leave the encrypted value — provider will
                                # fail at runtime, which is safer than
                                # silently dropping the field.
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


async def discover_gpu_providers() -> None:
    """Auto-discover providers from the GPU service and register RemoteProviders.

    Queries the GPU service's ``/providers`` endpoint to learn which providers
    are available, then creates a ``RemoteProvider`` instance for each one and
    registers it in the global ``provider_registry``.

    Silently returns if ``gpu_service_url`` is not configured or if the GPU
    service is unreachable.
    """
    if not settings.gpu_service_url:
        return

    try:
        import httpx

        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.gpu_service_url}/providers")
            if resp.status_code == 200:
                data = resp.json()
                discovered: list[str] = []
                providers_list = data if isinstance(data, list) else data.get("providers", [])
                for p in providers_list:
                    name = p["name"]
                    display = p.get("display_name", name)
                    # Update display-name dicts so list_all_known includes them
                    if name not in PROVIDER_DISPLAY_NAMES:
                        PROVIDER_DISPLAY_NAMES[name] = display
                    if name not in PROVIDER_TYPES:
                        PROVIDER_TYPES[name] = "gpu"

                    from app.providers.remote_provider import RemoteProvider

                    provider_registry._gpu_providers[name] = RemoteProvider(
                        name=name,
                        display_name=display,
                        gpu_service_url=settings.gpu_service_url,
                        timeout=settings.gpu_service_timeout,
                    )
                    discovered.append(name)
                    logger.info(
                        "gpu_provider_discovered",
                        provider=name,
                        display=display,
                    )

                if discovered:
                    logger.info(
                        "gpu_providers_discovery_complete",
                        count=len(discovered),
                        providers=discovered,
                    )
            else:
                logger.warning(
                    "gpu_service_discovery_http_error",
                    status=resp.status_code,
                )
    except Exception as exc:
        logger.warning("gpu_service_discovery_failed", error=str(exc))
