"""Domain layer errors."""


class DomainError(Exception):
    """Base domain error."""

    pass


class ValidationError(DomainError):
    """Domain validation error."""

    pass


class BusinessRuleViolationError(DomainError):
    """Business rule violation error."""

    pass
