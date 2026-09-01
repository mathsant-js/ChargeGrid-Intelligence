class DomainError(Exception):
    """Base exception for expected business-rule failures."""


class DomainConflictError(DomainError):
    """Raised when the requested operation conflicts with domain state."""


class DomainResourceNotFoundError(DomainError):
    """Raised when a resource must not be visible to the current user."""
