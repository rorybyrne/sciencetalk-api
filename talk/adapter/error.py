"""Infrastructure layer errors."""


class AdapterError(Exception):
    """Base infrastructure error."""

    pass


class ProviderError(AdapterError):
    """External provider error."""

    pass
