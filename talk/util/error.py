"""Utility layer errors."""


class UtilError(Exception):
    """Base utility error."""

    pass


class ConfigurationError(UtilError):
    """Configuration error."""

    pass


class DependencyInjectionError(UtilError):
    """Dependency injection error."""

    pass
