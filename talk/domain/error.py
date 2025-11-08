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


class NotAuthorizedError(DomainError):
    """Raised when a user attempts to edit content they don't own."""

    def __init__(self, resource: str, resource_id: str, user_id: str):
        super().__init__(
            f"User {user_id} is not authorized to edit {resource} {resource_id}"
        )


class ContentDeletedException(DomainError):
    """Raised when attempting to edit deleted content."""

    def __init__(self, resource: str, resource_id: str):
        super().__init__(f"Cannot edit deleted {resource} {resource_id}")


class InvalidEditOperationError(DomainError):
    """Raised when an edit operation violates business rules."""

    def __init__(self, message: str):
        super().__init__(message)


class NotFoundError(DomainError):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, identifier: str):
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} not found: {identifier}")
