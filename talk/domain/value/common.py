"""Base class for value objects."""

from pydantic import BaseModel, ConfigDict


class ValueObject(BaseModel):
    """Base class for all value objects.

    Value objects are immutable and compared by value, not identity.
    """

    model_config = ConfigDict(
        frozen=True,  # All value objects are immutable
        arbitrary_types_allowed=True,
    )
