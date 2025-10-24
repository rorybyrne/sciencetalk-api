# Util Layer - CLAUDE.md

## Purpose
The util layer contains **cross-cutting concerns** and shared utilities that don't belong to any specific architectural layer. This includes dependency injection, configuration, common helpers, and framework integrations.

## Key Principles
- **Layer-agnostic** - Can be used by any layer
- **No business logic** - Pure utility functions and framework glue
- **Framework integration** - Hide framework complexity from other layers
- **Configuration management** - Centralize settings and environment handling
- **Dependency injection** - Wire up the application graph

## Structure
- `di/` - Dependency injection container and providers
- `error.py` - Utility-specific exceptions
- `temporal.py` - Date/time utilities (if needed)
- `model.py` - Common data structures (if needed)

## Implementation Guidelines

### Dependency Injection (`di/`)
Configure and wire up the entire application dependency graph.

#### Container Setup (`di/container.py`)
```python
from dishka import make_container, Container, Scope
from dishka.integrations.fastapi import setup_dishka

from .domain import DomainProvider
from .infrastructure import InfrastructureProvider
from .application import ApplicationProvider

def create_container(settings: Settings) -> Container:
    """Create DI container with all providers."""
    container = make_container(
        DomainProvider(),
        InfrastructureProvider(settings),
        ApplicationProvider(),
        scope=Scope.APP
    )
    return container

def create_test_container() -> Container:
    """Create DI container for testing with mocks."""
    settings = Settings(environment="test")
    container = make_container(
        DomainProvider(),
        TestInfrastructureProvider(settings),
        ApplicationProvider(),
        scope=Scope.APP
    )
    return container

def setup_di(app: FastAPI, container: Container) -> None:
    """Setup dependency injection for FastAPI."""
    setup_dishka(container, app)
```

#### Domain Provider (`di/domain.py`)
```python
from dishka import Provider, Scope, provide

from ...domain.service.order import OrderService
from ...domain.service.customer import CustomerService
from ...domain.service.pricing import PricingService

class DomainProvider(Provider):
    """Provides domain services."""

    scope = Scope.APP

    @provide
    def get_order_service(self) -> OrderService:
        return OrderService()

    @provide
    def get_customer_service(self) -> CustomerService:
        return CustomerService()

    @provide
    def get_pricing_service(self) -> PricingService:
        return PricingService()
```

#### Infrastructure Provider (`di/infrastructure.py`)
```python
from dishka import Provider, Scope, provide

from ...config import Settings
from ...infrastructure.persistence.repository.order.base import OrderRepository
from ...infrastructure.persistence.repository.order.database import DatabaseOrderRepository
from ...infrastructure.persistence.repository.order.inmemory import InMemoryOrderRepository
from ...infrastructure.payment.base import PaymentService
from ...infrastructure.payment.stripe import StripePaymentService
from ...infrastructure.payment.mock import MockPaymentService

class InfrastructureProvider(Provider):
    """Provides infrastructure implementations."""

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings

    scope = Scope.APP

    @provide
    def get_order_repository(self) -> OrderRepository:
        if self.settings.environment == "test":
            return InMemoryOrderRepository()
        else:
            db_client = self._create_db_client()
            return DatabaseOrderRepository(db_client)

    @provide
    def get_payment_service(self) -> PaymentService:
        if self.settings.environment == "test":
            return MockPaymentService()
        else:
            return StripePaymentService(
                api_key=self.settings.stripe_api_key,
                webhook_secret=self.settings.stripe_webhook_secret
            )

    def _create_db_client(self):
        # Database client creation logic
        pass

class TestInfrastructureProvider(Provider):
    """Provides test implementations for all infrastructure."""

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings

    scope = Scope.APP

    @provide
    def get_order_repository(self) -> OrderRepository:
        return InMemoryOrderRepository()

    @provide
    def get_payment_service(self) -> PaymentService:
        return MockPaymentService()
```

#### Application Provider (`di/application.py`)
```python
from dishka import Provider, Scope, provide

from ...application.usecase.create_order import CreateOrderUseCase
from ...application.usecase.get_order import GetOrderUseCase
from ...domain.service.order import OrderService
from ...domain.service.customer import CustomerService
from ...domain.service.pricing import PricingService
from ...infrastructure.persistence.repository.order.base import OrderRepository
from ...infrastructure.payment.base import PaymentService

class ApplicationProvider(Provider):
    """Provides application use cases."""

    scope = Scope.APP

    @provide
    def get_create_order_use_case(
        self,
        order_repository: OrderRepository,
        customer_service: CustomerService,
        pricing_service: PricingService,
        payment_service: PaymentService
    ) -> CreateOrderUseCase:
        return CreateOrderUseCase(
            order_repository=order_repository,
            customer_service=customer_service,
            pricing_service=pricing_service,
            payment_service=payment_service
        )

    @provide
    def get_get_order_use_case(
        self,
        order_repository: OrderRepository
    ) -> GetOrderUseCase:
        return GetOrderUseCase(order_repository=order_repository)
```

### Configuration Management
Centralize all application settings and environment handling.

```python
# Already covered in config.py, but additional utilities:

class ConfigError(Exception):
    """Configuration-related error."""
    pass

def validate_settings(settings: Settings) -> None:
    """Validate settings and raise ConfigError if invalid."""
    if settings.environment == "production":
        if not settings.database_url:
            raise ConfigError("DATABASE_URL required in production")
        if not settings.stripe_api_key:
            raise ConfigError("STRIPE_API_KEY required in production")

def get_log_level(settings: Settings) -> str:
    """Get appropriate log level for environment."""
    if settings.environment == "production":
        return "INFO"
    elif settings.environment == "test":
        return "WARNING"
    else:
        return "DEBUG"
```

### Common Utilities
Shared helper functions that don't belong to any specific layer.

```python
# util/helpers.py
from typing import TypeVar, Optional, List
import uuid
from datetime import datetime, timezone

T = TypeVar('T')

def generate_id() -> str:
    """Generate a unique identifier."""
    return str(uuid.uuid4())

def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)

def chunk_list(items: List[T], chunk_size: int) -> List[List[T]]:
    """Split a list into chunks of specified size."""
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]

def safe_get(dictionary: dict, key: str, default: Optional[T] = None) -> Optional[T]:
    """Safely get value from dictionary with default."""
    return dictionary.get(key, default)
```

### Framework Integration
Hide framework-specific details from other layers.

```python
# util/logging.py
import logging
import sys
from typing import Optional

def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None
) -> None:
    """Setup application logging."""
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        stream=sys.stdout
    )

def get_logger(name: str) -> logging.Logger:
    """Get logger for module."""
    return logging.getLogger(name)
```

## What Belongs Here
- **Dependency injection configuration** - Wiring up the application
- **Settings and configuration** - Environment variables, secrets
- **Framework integration** - FastAPI setup, logging configuration
- **Common utilities** - ID generation, date/time helpers
- **Cross-cutting concerns** - Logging, monitoring, caching setup

## What NOT to Put Here
- **Business logic** → belongs in Domain layer
- **Use case orchestration** → belongs in Application layer
- **External service integration** → belongs in Infrastructure layer
- **HTTP handling** → belongs in Interface layer

## Testing Utilities
Provide helpers for testing across all layers.

```python
# util/testing.py
from typing import Any, Dict
import pytest
from unittest.mock import Mock

def create_mock_with_return(return_value: Any) -> Mock:
    """Create a mock that returns specified value."""
    mock = Mock()
    mock.return_value = return_value
    return mock

async def create_async_mock_with_return(return_value: Any) -> Mock:
    """Create an async mock that returns specified value."""
    mock = Mock()
    mock.return_value = return_value
    return mock

def create_test_settings(**overrides) -> Settings:
    """Create settings for testing with optional overrides."""
    defaults = {
        "environment": "test",
        "debug": True,
        "database_url": "sqlite:///:memory:",
        "api_host": "localhost",
        "api_port": 8000
    }
    defaults.update(overrides)
    return Settings(**defaults)
```

## Environment Management
Handle different deployment environments.

```python
# util/environment.py
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"

def is_production(settings: Settings) -> bool:
    """Check if running in production."""
    return settings.environment == Environment.PRODUCTION

def is_test(settings: Settings) -> bool:
    """Check if running in test."""
    return settings.environment == Environment.TEST

def get_database_pool_size(settings: Settings) -> int:
    """Get appropriate database pool size for environment."""
    if is_production(settings):
        return 20
    elif settings.environment == Environment.STAGING:
        return 10
    else:
        return 5
```

## Questions to Ask Yourself
1. **Is this truly cross-cutting?** - Can it be used by multiple layers?
2. **Does this belong to a specific layer?** - Maybe it should go elsewhere
3. **Is this framework-specific?** - Consider abstracting it
4. **Is this configuration or business logic?** - Keep them separate
5. **Will this be needed in tests?** - Provide test utilities

## Common Mistakes to Avoid
- **God utilities** - Don't put everything in util just because it's shared
- **Business logic creep** - Keep business rules in domain layer
- **Framework coupling** - Abstract framework details appropriately
- **Missing test utilities** - Provide helpers for testing
- **Poor configuration management** - Don't hardcode settings

Remember: **The util layer should make other layers easier to work with, not more complex. Keep it simple and focused.**
