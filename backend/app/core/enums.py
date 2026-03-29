"""Status enums for Atlas Vox models."""

from enum import StrEnum


class ProfileStatus(StrEnum):
    PENDING = "pending"
    TRAINING = "training"
    READY = "ready"
    ERROR = "error"
    ARCHIVED = "archived"


class JobStatus(StrEnum):
    QUEUED = "queued"
    PREPROCESSING = "preprocessing"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProviderType(StrEnum):
    LOCAL = "local"
    CLOUD = "cloud"
    GPU = "gpu"
