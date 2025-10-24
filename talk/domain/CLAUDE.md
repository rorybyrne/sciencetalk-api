# Domain Layer - CLAUDE.md

## Purpose
The domain layer contains the **core business logic** and has **NO external dependencies**. This is the heart of your application where business rules, entities, and domain services live.

## Key Principles
- **No external dependencies** - Only Python standard library and domain concepts
- **Rich domain models** - Business logic belongs in entities and value objects
- **Ubiquitous language** - Use terminology from domain experts consistently
- **Aggregate boundaries** - Maintain consistency within aggregate roots
- **Immutable value objects** - Value objects should never change after creation

## Structure
- `model/` - Domain entities and aggregates
- `service/` - Domain services for business logic that doesn't fit in entities
- `value/` - Value objects and strongly-typed identifiers
- `error.py` - Domain-specific exceptions

## Implementation Guidelines

### Entities (`model/`)
- Represent things with **identity** that can change over time
- Contain business logic and enforce invariants
- Should be aggregate roots or belong to an aggregate
- Use rich methods that express business operations

```python
class Order:
    def __init__(self, order_id: OrderId, customer_id: CustomerId):
        self.id = order_id
        self.customer_id = customer_id
        self.items: List[OrderItem] = []
        self.status = OrderStatus.DRAFT

    def add_item(self, product: Product, quantity: int) -> None:
        if self.status != OrderStatus.DRAFT:
            raise OrderCannotBeModifiedError("Cannot modify confirmed order")
        # Business logic here
```

### Value Objects (`value/`)
- Represent concepts with **no identity** - equality based on value
- Should be **immutable** after creation
- Validate themselves in constructors
- Can be shared across aggregates

```python
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: Currency

    def __post_init__(self):
        if self.amount < 0:
            raise NegativeAmountError()
```

### Domain Services (`service/`)
- Contains business logic that doesn't naturally belong to any entity
- Coordinates between multiple domain objects
- Stateless operations
- Should NOT depend on infrastructure

```python
class PricingService:
    def calculate_order_total(self, order: Order, customer: Customer) -> Money:
        # Complex pricing logic that involves multiple entities
        pass
```

### Identifiers (`value/identifiers.py`)
- Use strongly-typed IDs with NewType
- Prevents mixing up different entity IDs
- Makes code more self-documenting

```python
from typing import NewType
OrderId = NewType("OrderId", str)
CustomerId = NewType("CustomerId", str)
```

## What NOT to Put Here
- Database queries or persistence logic → goes in Infrastructure
- HTTP requests or external API calls → goes in Infrastructure
- Framework-specific code → goes in Interface or Infrastructure
- Use case orchestration → goes in Application
- Data transfer objects → goes in Interface

## Common Patterns

### Aggregate Root Pattern
```python
class Order:  # Aggregate root
    def __init__(self):
        self._items: List[OrderItem] = []  # Aggregate members

    def add_item(self, product_id: ProductId, quantity: int) -> None:
        # All modifications go through aggregate root
        item = OrderItem(product_id, quantity)
        self._items.append(item)

    @property
    def items(self) -> List[OrderItem]:
        return self._items.copy()  # Return copy to prevent external modification
```

### Domain Events (Optional)
```python
class Order:
    def __init__(self):
        self._events: List[DomainEvent] = []

    def confirm(self) -> None:
        self.status = OrderStatus.CONFIRMED
        self._events.append(OrderConfirmed(self.id))
```

## Testing Domain Layer
- Focus on business rules and invariants
- Test aggregate boundaries and consistency
- Verify value object validation
- Test domain service calculations
- No mocking needed - pure business logic

## Questions to Ask Yourself
1. **Does this belong to the domain?** - If it's about external systems, it goes elsewhere
2. **Which aggregate does this belong to?** - Keep related concepts together
3. **Is this an entity or value object?** - Identity vs. value-based equality
4. **What business rules must be enforced?** - Implement them here
5. **What does the domain expert call this?** - Use their terminology

## Common Mistakes to Avoid
- **Anemic domain model** - Don't just create data containers, add behavior
- **God aggregates** - Keep aggregates small and focused
- **Infrastructure leakage** - No databases, HTTP, or external service dependencies
- **Wrong boundaries** - Don't mix unrelated business concepts
- **Missing validation** - Value objects and entities should validate themselves

Remember: **The domain layer is the most important part of your application. Get this right and everything else follows naturally.**
