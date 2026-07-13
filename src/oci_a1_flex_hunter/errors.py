"""Project-specific errors with explicit retry semantics."""


class HunterError(Exception):
    """Base class for expected application errors."""


class ConfigurationError(HunterError):
    """Local configuration is incomplete or unsafe."""


class AuthenticationError(HunterError):
    """OCI authentication failed."""


class AuthorizationError(HunterError):
    """The OCI principal is not authorized for the operation."""


class MalformedRequestError(HunterError):
    """OCI rejected the request as malformed."""


class CapacityUnavailableError(HunterError):
    """Capacity is unavailable and a bounded retry is permitted."""


class TransientOCIError(HunterError):
    """A throttling or service failure permits a bounded retry."""


class NonRetryableOCIError(HunterError):
    """An OCI failure must stop the workflow."""


class LockUnavailableError(HunterError):
    """Another local process owns the hunter lock."""
