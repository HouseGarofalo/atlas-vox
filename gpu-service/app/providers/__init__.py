"""GPU TTS provider registry.

Import order is not significant — all providers are discovered via the
``PROVIDER_REGISTRY`` dict which maps canonical name to class.
"""

from __future__ import annotations

from app.providers.chatterbox_provider import ChatterboxProvider
from app.providers.f5_tts_provider import F5TTSProvider
from app.providers.fish_speech import FishSpeechProvider
from app.providers.openvoice_provider import OpenVoiceProvider
from app.providers.orpheus_provider import OrpheusProvider
from app.providers.piper_training_provider import PiperTrainingProvider

PROVIDER_REGISTRY: dict[str, type] = {
    "fish_speech": FishSpeechProvider,
    "chatterbox": ChatterboxProvider,
    "f5_tts": F5TTSProvider,
    "openvoice_v2": OpenVoiceProvider,
    "orpheus": OrpheusProvider,
    "piper_training": PiperTrainingProvider,
}

__all__ = [
    "PROVIDER_REGISTRY",
    "FishSpeechProvider",
    "ChatterboxProvider",
    "F5TTSProvider",
    "OpenVoiceProvider",
    "OrpheusProvider",
    "PiperTrainingProvider",
]
