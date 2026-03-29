"""Tests for custom exception hierarchy."""

from app.core.exceptions import AtlasVoxError, NotFoundError, ProviderError, ValidationError


def test_not_found_is_atlas_vox_error():
    assert issubclass(NotFoundError, AtlasVoxError)


def test_validation_is_atlas_vox_error():
    assert issubclass(ValidationError, AtlasVoxError)


def test_provider_is_atlas_vox_error():
    assert issubclass(ProviderError, AtlasVoxError)


def test_not_found_raises_with_message():
    try:
        raise NotFoundError("Profile not found")
    except AtlasVoxError as e:
        assert str(e) == "Profile not found"


def test_all_catchable_by_base():
    """All custom exceptions are catchable by AtlasVoxError."""
    for exc_cls in (NotFoundError, ValidationError, ProviderError):
        try:
            raise exc_cls("test")
        except AtlasVoxError:
            pass  # Should be caught
