"""Core exceptions for servicorn."""


class ServicornError(Exception):
    """Base exception for servicorn."""


class InvalidRequestError(ServicornError):
    """Raised when an incoming RPC request cannot be normalized."""


class ConfigurationError(ServicornError):
    """Raised when runtime configuration is invalid."""


class RuntimeUnavailableError(ServicornError):
    """Raised when an optional runtime backend is not available."""
