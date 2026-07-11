"""Exceptions for CNE Combustibles Chile."""


class CNEError(Exception):
    """Base exception for CNE API errors."""


class CNEAuthenticationError(CNEError):
    """Raised when authentication fails."""


class CNEConnectionError(CNEError):
    """Raised when communication with the API fails."""


class CNEInvalidResponseError(CNEError):
    """Raised when the API returns an unexpected response."""
