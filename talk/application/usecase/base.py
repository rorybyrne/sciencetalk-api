"""Base use case."""

from abc import ABC, abstractmethod
from typing import Any


class BaseUseCase(ABC):
    """Base use case for orchestrating domain services."""

    @abstractmethod
    async def execute(self, request: Any) -> Any:
        pass
