# Tests - CLAUDE.md

## Purpose
Comprehensive testing strategy following the **Test Pyramid** principle with focus on fast, reliable tests that provide confidence in your domain-driven design implementation.

## Testing Philosophy
- **Test business logic thoroughly** - Domain layer gets the most coverage
- **Test integration points** - Verify layers work together correctly
- **Fast feedback loops** - Unit tests run in milliseconds
- **Realistic scenarios** - Integration tests use real infrastructure where possible
- **End-to-end confidence** - E2E tests cover critical user journeys

## Test Structure
- `unit/` - Fast, isolated tests for individual components
- `integration/` - Tests that verify component interactions
- `e2e/` - End-to-end tests through the full application
- `conftest.py` - Shared test configuration and fixtures

## Testing Strategy by Layer

### Unit Tests (`unit/`)
Test individual components in isolation with no external dependencies.

#### Domain Layer Testing
**Focus: Business logic, invariants, and domain rules**

```python
# tests/unit/domain/model/test_order.py
import pytest
from decimal import Decimal

from talk.domain.model.order import Order
from talk.domain.value.identifiers import OrderId, CustomerId
from talk.domain.value.money import Money, Currency
from talk.domain.error import InvalidOrderStateError

class TestOrder:
    def test_create_order_with_valid_data(self):
        # Arrange
        order_id = OrderId("123")
        customer_id = CustomerId("456")

        # Act
        order = Order(order_id, customer_id)

        # Assert
        assert order.id == order_id
        assert order.customer_id == customer_id
        assert order.status == OrderStatus.DRAFT
        assert len(order.items) == 0

    def test_add_item_to_draft_order(self):
        # Arrange
        order = Order(OrderId("123"), CustomerId("456"))
        product_id = ProductId("789")
        quantity = 2

        # Act
        order.add_item(product_id, quantity)

        # Assert
        assert len(order.items) == 1
        assert order.items[0].product_id == product_id
        assert order.items[0].quantity == quantity

    def test_cannot_add_item_to_confirmed_order(self):
        # Arrange
        order = Order(OrderId("123"), CustomerId("456"))
        order.confirm()  # Change status to CONFIRMED

        # Act & Assert
        with pytest.raises(InvalidOrderStateError, match="Cannot modify confirmed order"):
            order.add_item(ProductId("789"), 1)

    def test_calculate_total_with_multiple_items(self):
        # Arrange
        order = Order(OrderId("123"), CustomerId("456"))
        order.add_item(ProductId("1"), 2, Money(Decimal("10.00"), Currency.USD))
        order.add_item(ProductId("2"), 1, Money(Decimal("5.00"), Currency.USD))

        # Act
        total = order.calculate_total()

        # Assert
        assert total == Money(Decimal("25.00"), Currency.USD)

# tests/unit/domain/service/test_pricing_service.py
class TestPricingService:
    def test_calculate_order_total_with_no_discount(self):
        # Arrange
        pricing_service = PricingService()
        order = self._create_order_with_items()
        customer = self._create_regular_customer()

        # Act
        total = pricing_service.calculate_order_total(order, customer)

        # Assert
        assert total == Money(Decimal("100.00"), Currency.USD)

    def test_calculate_order_total_with_vip_discount(self):
        # Arrange
        pricing_service = PricingService()
        order = self._create_order_with_items()
        customer = self._create_vip_customer()

        # Act
        total = pricing_service.calculate_order_total(order, customer)

        # Assert
        assert total == Money(Decimal("90.00"), Currency.USD)  # 10% VIP discount
```

#### Application Layer Testing
**Focus: Use case orchestration and error handling**

```python
# tests/unit/application/usecase/test_create_order.py
import pytest
from unittest.mock import Mock, AsyncMock

from talk.application.usecase.create_order import CreateOrderUseCase, CreateOrderRequest
from talk.domain.error import CustomerNotFoundError, InsufficientInventoryError

class TestCreateOrderUseCase:
    def setup_method(self):
        self.order_repo = Mock()
        self.customer_repo = Mock()
        self.pricing_service = Mock()
        self.inventory_service = Mock()

        self.use_case = CreateOrderUseCase(
            self.order_repo,
            self.customer_repo,
            self.pricing_service,
            self.inventory_service
        )

    @pytest.mark.asyncio
    async def test_create_order_success(self):
        # Arrange
        request = CreateOrderRequest(
            customer_id="123",
            items=[OrderItemRequest(product_id="456", quantity=2)]
        )

        customer = Customer(CustomerId("123"), "John Doe")
        self.customer_repo.find_by_id.return_value = customer
        self.inventory_service.is_available.return_value = True
        self.pricing_service.calculate_order_total.return_value = Money(Decimal("50.00"), Currency.USD)
        self.order_repo.save.return_value = Mock(id=OrderId("789"))

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.order_id == "789"
        self.customer_repo.find_by_id.assert_called_once_with(CustomerId("123"))
        self.order_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_order_customer_not_found(self):
        # Arrange
        request = CreateOrderRequest(customer_id="123", items=[])
        self.customer_repo.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(CustomerNotFoundError):
            await self.use_case.execute(request)
```

### Integration Tests (`integration/`)
Test component interactions with real infrastructure where possible.

#### Repository Integration Tests
**Focus: Data persistence and retrieval with real database**

```python
# tests/integration/infrastructure/persistence/test_order_repository.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from talk.infrastructure.persistence.repository.order.database import DatabaseOrderRepository
from talk.domain.model.order import Order
from talk.domain.value.identifiers import OrderId, CustomerId

@pytest.fixture
def db_session():
    # Create test database
    engine = create_engine("sqlite:///:memory:")
    # Run migrations
    setup_test_schema(engine)

    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def order_repository(db_session):
    return DatabaseOrderRepository(db_session)

class TestDatabaseOrderRepository:
    @pytest.mark.asyncio
    async def test_save_and_retrieve_order(self, order_repository):
        # Arrange
        order = Order(OrderId("123"), CustomerId("456"))
        order.add_item(ProductId("789"), 2)

        # Act
        saved_order = await order_repository.save(order)
        retrieved_order = await order_repository.find_by_id(saved_order.id)

        # Assert
        assert retrieved_order is not None
        assert retrieved_order.id == saved_order.id
        assert retrieved_order.customer_id == saved_order.customer_id
        assert len(retrieved_order.items) == 1
        assert retrieved_order.items[0].quantity == 2

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, order_repository):
        # Act
        result = await order_repository.find_by_id(OrderId("nonexistent"))

        # Assert
        assert result is None
```

#### Use Case Integration Tests
**Focus: Full use case execution with real DI container**

```python
# tests/integration/application/usecase/test_create_order_integration.py
import pytest
from dishka import make_container

from talk.util.di.container import create_test_container
from talk.application.usecase.create_order import CreateOrderUseCase, CreateOrderRequest

@pytest.fixture
async def container():
    container = create_test_container()
    await container.start()
    yield container
    await container.close()

class TestCreateOrderIntegration:
    @pytest.mark.asyncio
    async def test_create_order_end_to_end(self, container):
        # Arrange
        use_case = await container.get(CreateOrderUseCase)

        # Setup test data
        customer_repo = await container.get(CustomerRepository)
        customer = Customer(CustomerId("123"), "John Doe")
        await customer_repo.save(customer)

        request = CreateOrderRequest(
            customer_id="123",
            items=[OrderItemRequest(product_id="456", quantity=2)]
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.order_id is not None

        # Verify order was saved
        order_repo = await container.get(OrderRepository)
        saved_order = await order_repo.find_by_id(OrderId(response.order_id))
        assert saved_order is not None
        assert len(saved_order.items) == 1
```

### End-to-End Tests (`e2e/`)
Test complete user journeys through the HTTP API.

```python
# tests/e2e/test_order_workflow.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from talk.interface.api.app import create_app
from talk.util.di.container import create_test_container

@pytest.fixture
def test_app():
    # Create app with test configuration
    container = create_test_container()
    app = create_app()
    setup_dishka(container, app)
    return app

@pytest.fixture
def client(test_app):
    return TestClient(test_app)

class TestOrderWorkflow:
    def test_complete_order_workflow(self, client):
        # 1. Create customer
        customer_data = {
            "name": "John Doe",
            "email": "john@example.com"
        }
        customer_response = client.post("/customers/", json=customer_data)
        assert customer_response.status_code == 201
        customer_id = customer_response.json()["customer_id"]

        # 2. Create order
        order_data = {
            "customer_id": customer_id,
            "items": [
                {"product_id": "123", "quantity": 2},
                {"product_id": "456", "quantity": 1}
            ]
        }
        order_response = client.post("/orders/", json=order_data)
        assert order_response.status_code == 201
        order_id = order_response.json()["order_id"]

        # 3. Get order
        get_response = client.get(f"/orders/{order_id}")
        assert get_response.status_code == 200
        order_details = get_response.json()
        assert order_details["customer_id"] == customer_id
        assert len(order_details["items"]) == 2

        # 4. Confirm order
        confirm_response = client.post(f"/orders/{order_id}/confirm")
        assert confirm_response.status_code == 200
        assert confirm_response.json()["status"] == "confirmed"

    def test_create_order_with_invalid_customer(self, client):
        # Arrange
        order_data = {
            "customer_id": "nonexistent",
            "items": [{"product_id": "123", "quantity": 1}]
        }

        # Act
        response = client.post("/orders/", json=order_data)

        # Assert
        assert response.status_code == 404
        assert "Customer not found" in response.json()["message"]
```

## Test Configuration (`conftest.py`)

```python
import pytest
import asyncio
from typing import AsyncGenerator
from dishka import make_container

from talk.util.di.container import create_test_container
from talk.config import Settings

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_settings():
    """Test settings with overrides."""
    return Settings(
        environment="test",
        database_url="sqlite:///:memory:",
        debug=True
    )

@pytest.fixture
async def container(test_settings):
    """DI container for testing."""
    container = create_test_container(test_settings)
    await container.start()
    yield container
    await container.close()

@pytest.fixture
def mock_payment_service():
    """Mock payment service for testing."""
    from talk.infrastructure.payment.mock import MockPaymentService
    return MockPaymentService(should_succeed=True)
```

## Testing Best Practices

### Arrange-Act-Assert Pattern
```python
def test_something():
    # Arrange - Set up test data and dependencies
    order = Order(OrderId("123"), CustomerId("456"))

    # Act - Execute the behavior being tested
    order.add_item(ProductId("789"), 2)

    # Assert - Verify the expected outcome
    assert len(order.items) == 1
    assert order.items[0].quantity == 2
```

### Test Data Builders
```python
class OrderBuilder:
    def __init__(self):
        self.order_id = OrderId("default-id")
        self.customer_id = CustomerId("default-customer")
        self.items = []

    def with_id(self, order_id: OrderId) -> 'OrderBuilder':
        self.order_id = order_id
        return self

    def with_customer(self, customer_id: CustomerId) -> 'OrderBuilder':
        self.customer_id = customer_id
        return self

    def with_item(self, product_id: ProductId, quantity: int) -> 'OrderBuilder':
        self.items.append((product_id, quantity))
        return self

    def build(self) -> Order:
        order = Order(self.order_id, self.customer_id)
        for product_id, quantity in self.items:
            order.add_item(product_id, quantity)
        return order

# Usage
def test_order_with_multiple_items():
    order = (OrderBuilder()
             .with_id(OrderId("123"))
             .with_customer(CustomerId("456"))
             .with_item(ProductId("1"), 2)
             .with_item(ProductId("2"), 1)
             .build())

    assert len(order.items) == 2
```

## Performance Testing
```python
import time
import pytest

@pytest.mark.performance
def test_order_creation_performance():
    start_time = time.time()

    # Create 1000 orders
    for i in range(1000):
        order = Order(OrderId(f"order-{i}"), CustomerId(f"customer-{i}"))
        order.add_item(ProductId("product-1"), 1)

    end_time = time.time()
    execution_time = end_time - start_time

    # Should create 1000 orders in less than 1 second
    assert execution_time < 1.0
```

## Common Testing Patterns

### Parameterized Tests
```python
@pytest.mark.parametrize("quantity,expected_total", [
    (1, Decimal("10.00")),
    (2, Decimal("20.00")),
    (5, Decimal("50.00")),
])
def test_order_total_calculation(quantity, expected_total):
    order = Order(OrderId("123"), CustomerId("456"))
    order.add_item(ProductId("1"), quantity, Money(Decimal("10.00"), Currency.USD))

    total = order.calculate_total()
    assert total.amount == expected_total
```

### Property-Based Testing
```python
from hypothesis import given, strategies as st

@given(
    quantity=st.integers(min_value=1, max_value=100),
    unit_price=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000.00"))
)
def test_order_total_is_quantity_times_price(quantity, unit_price):
    order = Order(OrderId("123"), CustomerId("456"))
    order.add_item(ProductId("1"), quantity, Money(unit_price, Currency.USD))

    total = order.calculate_total()
    expected = quantity * unit_price

    assert total.amount == expected
```

## Questions to Ask Yourself
1. **What behavior am I testing?** - Focus on behavior, not implementation
2. **Is this test isolated?** - Unit tests should have no external dependencies
3. **Is this test fast?** - Unit tests should run in milliseconds
4. **Is this test deterministic?** - Should pass/fail consistently
5. **Does this test add value?** - Test important behaviors, not trivial getters/setters

## Common Testing Mistakes to Avoid
- **Testing implementation details** - Test behavior, not internal structure
- **Slow unit tests** - Keep external dependencies out of unit tests
- **Brittle tests** - Don't over-specify test data and assertions
- **Missing edge cases** - Test boundary conditions and error scenarios
- **Poor test data** - Use realistic, meaningful test data
- **No integration tests** - Unit tests alone aren't enough

Remember: **Good tests give you confidence to refactor and extend your code. They should be fast, reliable, and easy to understand.**
