"""Custom exception hierarchy for Atlas Vox.

These exceptions provide a consistent error contract:
  - ``AtlasVoxError`` and its children carry a human-readable ``detail``
    and a machine-readable ``code``.
  - Endpoint code catches them and returns {"detail": "...", "code": "..."}.
  - The ``internal_detail`` field is logged server-side but NEVER sent to
    clients, preventing information leakage.
"""


class AtlasVoxError(Exception):
    """Base exception for all Atlas Vox errors."""

    def __init__(self, detail: str = "An error occurred", *, code: str = "error", internal_detail: str = "") -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code
        self.internal_detail = internal_detail


class NotFoundError(AtlasVoxError):
    """Resource not found."""

    def __init__(self, resource: str = "Resource", resource_id: str = "") -> None:
        detail = f"{resource} not found" + (f": {resource_id}" if resource_id else "")
        super().__init__(detail, code="not_found")


class ValidationError(AtlasVoxError):
    """Client-side validation failed."""

    def __init__(self, detail: str = "Validation failed") -> None:
        super().__init__(detail, code="validation_error")


class ProviderError(AtlasVoxError):
    """TTS provider operation failed. Internal error logged, not returned to client."""

    def __init__(self, provider: str = "", operation: str = "", internal_error: str = "") -> None:
        detail = f"Provider '{provider}' failed during {operation}. Check server logs." if provider else "Provider error"
        super().__init__(detail, code="provider_error", internal_detail=internal_error)


class ServiceError(AtlasVoxError):
    """Internal service failure. Internal error logged, not returned to client."""

    def __init__(self, operation: str = "", internal_error: str = "") -> None:
        detail = f"{operation} failed. Check server logs." if operation else "Service error"
        super().__init__(detail, code="service_error", internal_detail=internal_error)
