"""Import all models so SQLAlchemy Base.metadata registers them."""

from app.models.api_key import ApiKey  # noqa: F401
from app.models.audio_sample import AudioSample  # noqa: F401
from app.models.model_version import ModelVersion  # noqa: F401
from app.models.persona_preset import PersonaPreset  # noqa: F401
from app.models.provider import Provider  # noqa: F401
from app.models.synthesis_history import SynthesisHistory  # noqa: F401
from app.models.training_job import TrainingJob  # noqa: F401
from app.models.voice_profile import VoiceProfile  # noqa: F401
from app.models.webhook import Webhook  # noqa: F401

# Self-healing models
from app.healing.models import Incident  # noqa: F401
