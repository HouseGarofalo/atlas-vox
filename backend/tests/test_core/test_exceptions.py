"""Tests for custom exception hierarchy."""

from app.core.exceptions import AtlasVoxError, NotFoundError, ProviderError, ServiceError, ValidationError


def test_not_found_is_atlas_vox_error():
    assert issubclass(NotFoundError, AtlasVoxError)


def test_validation_is_atlas_vox_error():
    assert issubclass(ValidationError, AtlasVoxError)


def test_provider_is_atlas_vox_error():
    assert issubclass(ProviderError, AtlasVoxError)


def test_service_error_is_atlas_vox_error():
    assert issubclass(ServiceError, AtlasVoxError)


def test_not_found_raises_with_message():
    try:
        raise NotFoundError("Profile", "abc-123")
    except AtlasVoxError as e:
        assert "Profile 'abc-123' not found" in str(e)
        assert e.code == "not_found"


def test_not_found_default():
    e = NotFoundError()
    assert "Resource not found" in e.detail


def test_validation_error():
    e = ValidationError("Name is required")
    assert e.detail == "Name is required"
    assert e.code == "validation_error"


def test_provider_error_sanitizes():
    e = ProviderError("elevenlabs", "synthesis", internal_error="API key invalid: sk-1234")
    assert "elevenlabs" in e.detail
    assert "synthesis" in e.detail
    assert "sk-1234" not in e.detail  # Internal details NOT in detail
    assert e.code == "provider_error"


def test_service_error():
    e = ServiceError("transcription", internal_error="FileNotFoundError: /tmp/x.wav")
    assert "transcription" in e.detail
    assert "/tmp/x.wav" not in e.detail
    assert e.code == "service_error"


def test_all_catchable_by_base():
    """All custom exceptions are catchable by AtlasVoxError."""
    for exc_cls in (NotFoundError, ValidationError, ProviderError, ServiceError):
        try:
            raise exc_cls()
        except AtlasVoxError:
            pass  # Should be caught
