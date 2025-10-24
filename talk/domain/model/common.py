"""Base model for all domain entities."""

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """Base class for all domain models.

    Provides common configuration for immutability and custom types.
    """

    model_config = ConfigDict(
        frozen=True,  # All domain models are immutable
        arbitrary_types_allowed=True,  # Allow custom value objects
    )
