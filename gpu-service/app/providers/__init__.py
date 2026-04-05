"""GPU TTS provider registry.

Import order is not significant — all providers are discovered via the
``PROVIDER_REGISTRY`` dict which maps canonical name to class.
Providers that are not yet implemented are silently skipped.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

PROVIDER_REGISTRY: dict[str, type] = {}

try:
    from app.providers.chatterbox_provider import ChatterboxProvider
    PROVIDER_REGISTRY["chatterbox"] = ChatterboxProvider
except ImportError:
    logger.debug("chatterbox_provider not available")
    ChatterboxProvider = None  # type: ignore[assignment, misc]

try:
    from app.providers.f5_tts_provider import F5TTSProvider
    PROVIDER_REGISTRY["f5_tts"] = F5TTSProvider
except ImportError:
    logger.debug("f5_tts_provider not available")
    F5TTSProvider = None  # type: ignore[assignment, misc]

try:
    from app.providers.fish_speech import FishSpeechProvider
    PROVIDER_REGISTRY["fish_speech"] = FishSpeechProvider
except ImportError:
    logger.debug("fish_speech not available")
    FishSpeechProvider = None  # type: ignore[assignment, misc]

try:
    from app.providers.openvoice_provider import OpenVoiceProvider
    PROVIDER_REGISTRY["openvoice_v2"] = OpenVoiceProvider
except ImportError:
    logger.debug("openvoice_provider not available")
    OpenVoiceProvider = None  # type: ignore[assignment, misc]

try:
    from app.providers.orpheus_provider import OrpheusProvider
    PROVIDER_REGISTRY["orpheus"] = OrpheusProvider
except ImportError:
    logger.debug("orpheus_provider not available")
    OrpheusProvider = None  # type: ignore[assignment, misc]

try:
    from app.providers.piper_training_provider import PiperTrainingProvider
    PROVIDER_REGISTRY["piper_training"] = PiperTrainingProvider
except ImportError:
    logger.debug("piper_training_provider not available")
    PiperTrainingProvider = None  # type: ignore[assignment, misc]

__all__ = [
    "PROVIDER_REGISTRY",
]
