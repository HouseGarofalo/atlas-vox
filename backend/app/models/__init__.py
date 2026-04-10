"""Import all models so SQLAlchemy Base.metadata registers them."""

# Self-healing models
from app.healing.models import Incident  # noqa: F401
from app.models.api_key import ApiKey  # noqa: F401
from app.models.audio_sample import AudioSample  # noqa: F401
from app.models.model_version import ModelVersion  # noqa: F401
from app.models.persona_preset import PersonaPreset  # noqa: F401

# Phase E models
from app.models.pronunciation_entry import PronunciationEntry  # noqa: F401
from app.models.provider import Provider  # noqa: F401
from app.models.synthesis_history import SynthesisHistory  # noqa: F401

# System settings
from app.models.system_setting import SystemSetting  # noqa: F401
from app.models.training_job import TrainingJob  # noqa: F401
from app.models.usage_event import UsageEvent  # noqa: F401
from app.models.voice_favorite import VoiceFavorite  # noqa: F401
from app.models.voice_profile import VoiceProfile  # noqa: F401
from app.models.webhook import Webhook  # noqa: F401
