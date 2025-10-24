# Application Layer - CLAUDE.md

## Purpose
The application layer **orchestrates domain services** to fulfill specific use cases. It contains **NO business logic** - only coordination logic that defines how domain services work together.

## Key Principles
- **Orchestration only** - Coordinate domain services, don't implement business logic
- **Transaction boundaries** - Each use case represents a transaction boundary
- **Stateless** - Use cases should not maintain state between calls
- **Single responsibility** - One use case per business operation
- **Dependency on domain abstractions** - Depend on interfaces, not implementations

## Structure
- `usecase/` - Use case implementations that orchestrate domain services
- `base.py` - Base classes and common patterns

## Implementation Guidelines

### Use Cases (`usecase/`)
- Represent complete business operations from user perspective
- Orchestrate multiple domain services
- Handle cross-cutting concerns (logging, validation, transactions)
- Convert between interface models and domain models

```python
class CreateOrderUseCase(BaseUseCase):
    def __init__(
        self,
        order_repository: OrderRepository,
        customer_repository: CustomerRepository,
        pricing_service: PricingService,
        inventory_service: InventoryService,
    ):
        self._order_repo = order_repository
        self._customer_repo = customer_repository
        self._pricing_service = pricing_service
        self._inventory_service = inventory_service

    async def execute(self, request: CreateOrderRequest) -> CreateOrderResponse:
        # 1. Validate inputs (basic validation, not business rules)
        if not request.customer_id:
            raise ValidationError("Customer ID required")

        # 2. Load domain objects
        customer = await self._customer_repo.find_by_id(request.customer_id)
        if not customer:
            raise CustomerNotFoundError()

        # 3. Orchestrate domain operations
        order = Order.create(customer.id)

        for item_request in request.items:
            # Check inventory (domain service)
            if not await self._inventory_service.is_available(
                item_request.product_id,
                item_request.quantity
            ):
                raise InsufficientInventoryError()

            # Add item (domain logic)
            order.add_item(item_request.product_id, item_request.quantity)

        # Calculate pricing (domain service)
        total = self._pricing_service.calculate_order_total(order, customer)
        order.set_total(total)

        # 4. Persist changes
        saved_order = await self._order_repo.save(order)

        # 5. Return response
        return CreateOrderResponse.from_domain(saved_order)
```

### Request/Response Models
- Define the interface contract for use cases
- Should be simple data structures (often dataclasses)
- Include basic validation
- Convert to/from domain objects

```python
@dataclass
class CreateOrderRequest:
    customer_id: str
    items: List[OrderItemRequest]

    def validate(self) -> None:
        if not self.customer_id:
            raise ValidationError("Customer ID required")
        if not self.items:
            raise ValidationError("Order must have items")

@dataclass
class CreateOrderResponse:
    order_id: str
    total_amount: Decimal
    status: str

    @classmethod
    def from_domain(cls, order: Order) -> 'CreateOrderResponse':
        return cls(
            order_id=str(order.id),
            total_amount=order.total.amount,
            status=order.status.value
        )
```

### Error Handling
- Catch domain exceptions and decide how to handle them
- Create application-specific exceptions when needed
- Don't let infrastructure errors bubble up unchanged

```python
class CreateOrderUseCase:
    async def execute(self, request: CreateOrderRequest) -> CreateOrderResponse:
        try:
            # ... orchestration logic
            pass
        except CustomerNotFoundError:
            raise ApplicationError("Invalid customer")
        except InsufficientInventoryError as e:
            raise ApplicationError(f"Product {e.product_id} not available")
        except RepositoryError:
            raise ApplicationError("Unable to save order")
```

## What Belongs Here
- **Use case orchestration** - Coordinating multiple domain services
- **Transaction management** - Ensuring consistency across operations
- **Basic input validation** - Format and required field validation
- **Data transformation** - Converting between layers
- **Cross-cutting concerns** - Logging, metrics, caching

## What NOT to Put Here
- **Business logic** → belongs in Domain layer
- **Database queries** → belongs in Infrastructure layer
- **HTTP handling** → belongs in Interface layer
- **External API calls** → belongs in Infrastructure layer
- **Complex validation** → business rules belong in Domain layer

## Common Patterns

### Base Use Case
```python
class BaseUseCase(ABC):
    @abstractmethod
    async def execute(self, request: Any) -> Any:
        pass

class TransactionalUseCase(BaseUseCase):
    async def execute(self, request: Any) -> Any:
        async with self._transaction_manager.begin():
            return await self._execute_impl(request)

    @abstractmethod
    async def _execute_impl(self, request: Any) -> Any:
        pass
```

### Query vs Command Separation
```python
# Commands - modify state
class CreateOrderUseCase(BaseUseCase):
    async def execute(self, request: CreateOrderRequest) -> CreateOrderResponse:
        # Modify domain state
        pass

# Queries - read state
class GetOrderUseCase(BaseUseCase):
    async def execute(self, request: GetOrderRequest) -> GetOrderResponse:
        # Read-only operation
        pass
```

### Saga Pattern (for complex workflows)
```python
class ComplexOrderProcessUseCase(BaseUseCase):
    async def execute(self, request: ComplexOrderRequest) -> ComplexOrderResponse:
        # Step 1: Create order
        order = await self._create_order_step(request)

        try:
            # Step 2: Reserve inventory
            await self._reserve_inventory_step(order)

            # Step 3: Process payment
            await self._process_payment_step(order)

            # Step 4: Confirm order
            await self._confirm_order_step(order)

        except Exception:
            # Compensate previous steps
            await self._compensate(order)
            raise
```

## Testing Application Layer
- **Integration tests** - Test with real domain services and mocked repositories
- **Mock infrastructure** - Use in-memory repositories and mock external services
- **Focus on orchestration** - Verify the right services are called in the right order
- **Error scenarios** - Test compensation and error handling logic

```python
async def test_create_order_success():
    # Arrange
    customer_repo = InMemoryCustomerRepository()
    order_repo = InMemoryOrderRepository()
    pricing_service = MockPricingService()
    use_case = CreateOrderUseCase(order_repo, customer_repo, pricing_service)

    # Act
    response = await use_case.execute(CreateOrderRequest(...))

    # Assert
    assert response.order_id is not None
    saved_order = await order_repo.find_by_id(response.order_id)
    assert saved_order.status == OrderStatus.CREATED
```

## Questions to Ask Yourself
1. **What's the complete business operation?** - Use cases should represent full user workflows
2. **Which domain services need to coordinate?** - Identify dependencies
3. **What's the transaction boundary?** - What needs to succeed or fail together
4. **How do I handle failures?** - Plan compensation strategies
5. **What data transformation is needed?** - Between interface and domain models

## Common Mistakes to Avoid
- **Fat use cases** - Keep them focused on orchestration, not business logic
- **God use cases** - Split complex operations into smaller, focused use cases
- **Business logic leakage** - Don't implement domain rules here
- **Infrastructure coupling** - Depend on abstractions, not concrete implementations
- **Missing error handling** - Always plan for domain and infrastructure failures

Remember: **Use cases are the entry points to your domain. They should clearly express what your application can do, not how it does it.**
