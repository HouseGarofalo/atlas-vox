"""Application exception hierarchy.

All services should raise these typed exceptions instead of bare ValueError.
The global exception handler maps them to appropriate HTTP status codes.
"""

from __future__ import annotations


class AtlasVoxError(Exception):
    """Base exception for all Atlas Vox errors."""

    def __init__(self, detail: str = "An error occurred", code: str = "error"):
        self.detail = detail
        self.code = code
        super().__init__(detail)


class NotFoundError(AtlasVoxError):
    """Resource was not found."""

    def __init__(self, resource: str = "Resource", identifier: str | None = None):
        self.resource = resource
        self.identifier = identifier
        msg = f"{resource} not found"
        if identifier:
            msg = f"{resource} '{identifier}' not found"
        super().__init__(detail=msg, code="not_found")


class ValidationError(AtlasVoxError):
    """Input validation failed."""

    def __init__(self, message: str = "Validation failed", field: str | None = None):
        self.field = field
        super().__init__(detail=message, code="validation_error")


class ProviderError(AtlasVoxError):
    """TTS provider error."""

    def __init__(self, provider: str = "provider", operation: str = "operation", internal_error: str | None = None):
        self.provider = provider
        self.operation = operation
        self.internal_error = internal_error
        # Don't expose internal errors in the detail
        detail = f"[{provider}] {operation} failed"
        super().__init__(detail=detail, code="provider_error")


class ServiceError(AtlasVoxError):
    """Service operation error."""

    def __init__(self, service: str = "service", internal_error: str | None = None):
        self.service = service
        self.internal_error = internal_error
        # Don't expose internal errors in the detail
        detail = f"{service} error"
        super().__init__(detail=detail, code="service_error")


class AuthenticationError(AtlasVoxError):
    """Authentication failed."""

    def __init__(self):
        super().__init__(detail="Authentication failed", code="authentication_error")


class AuthorizationError(AtlasVoxError):
    """Insufficient permissions."""

    def __init__(self, required_scope: str | None = None):
        msg = "Insufficient permissions"
        if required_scope:
            msg = f"Required scope: {required_scope}"
        super().__init__(detail=msg, code="authorization_error")


class StorageError(AtlasVoxError):
    """File storage/retrieval error."""

    def __init__(self, message: str = "Storage error"):
        super().__init__(detail=message, code="storage_error")


class TrainingError(AtlasVoxError):
    """Training pipeline error."""

    def __init__(self, message: str, job_id: str | None = None):
        self.job_id = job_id
        super().__init__(detail=message, code="training_error")