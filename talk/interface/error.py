"""Interface layer errors."""


class InterfaceError(Exception):
    """Base interface error."""

    pass


class ValidationError(InterfaceError):
    """Request validation error."""

    pass


class NotFoundError(InterfaceError):
    """Resource not found error."""

    pass
