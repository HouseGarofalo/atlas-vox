"""Tests for status enums."""

from app.core.enums import JobStatus, ProfileStatus, ProviderType


def test_profile_status_values():
    assert ProfileStatus.PENDING == "pending"
    assert ProfileStatus.TRAINING == "training"
    assert ProfileStatus.READY == "ready"
    assert ProfileStatus.ERROR == "error"
    assert ProfileStatus.ARCHIVED == "archived"


def test_job_status_values():
    assert JobStatus.QUEUED == "queued"
    assert JobStatus.PREPROCESSING == "preprocessing"
    assert JobStatus.TRAINING == "training"
    assert JobStatus.COMPLETED == "completed"
    assert JobStatus.FAILED == "failed"
    assert JobStatus.CANCELLED == "cancelled"


def test_provider_type_values():
    assert ProviderType.LOCAL == "local"
    assert ProviderType.CLOUD == "cloud"
    assert ProviderType.GPU == "gpu"


def test_enums_are_strings():
    """Enums are StrEnum so they work as plain strings."""
    assert ProfileStatus.READY == "ready"
    assert f"Status is {ProfileStatus.READY}" == "Status is ready"
