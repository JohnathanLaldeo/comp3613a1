"""Domain errors raised by repositories/services.

Both subclass ValueError, so existing HTML routes that catch ValueError keep
working; the JSON API maps them to 404 / 409 status codes.
"""


class NotFoundError(ValueError):
    """The requested record does not exist (or is not available)."""


class ConflictError(ValueError):
    """The request clashes with the current state (duplicate, out of stock)."""
