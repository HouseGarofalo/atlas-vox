"""Custom exception hierarchy for Atlas Vox."""


class AtlasVoxError(Exception):
    """Base exception."""


class NotFoundError(AtlasVoxError):
    """Resource not found."""


class ValidationError(AtlasVoxError):
    """Validation failed."""


class ProviderError(AtlasVoxError):
    """Provider operation failed."""
