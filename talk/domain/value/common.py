"""Base class for value objects."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, RootModel


class ValueObject(BaseModel):
    """Base class for all value objects.

    Value objects are immutable and compared by value, not identity.
    """

    model_config = ConfigDict(
        frozen=True,  # All value objects are immutable
        arbitrary_types_allowed=True,
    )


T = TypeVar("T")


class RootValueObject(RootModel[T], Generic[T]):
    """Base class for value objects that wrap a single primitive value.

    RootValueObject uses Pydantic's RootModel, which means:
    - The model wraps a single value (accessed via .root)
    - model_dump() automatically returns the primitive value, not a dict
    - Perfect for simple wrappers like Handle, DID, Email, etc.
    """

    model_config = ConfigDict(
        frozen=True,  # All value objects are immutable
    )

    def __str__(self) -> str:
        """Return string representation of the root value."""
        return str(self.root)
