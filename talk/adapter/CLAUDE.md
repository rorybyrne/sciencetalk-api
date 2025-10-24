# Adapter Layer - CLAUDE.md

## Purpose
The infrastructure layer provides **concrete implementations** of domain abstractions and handles all **external system integration**. This layer depends on the domain layer but should be invisible to it.

## Key Principles
- **Implement domain interfaces** - Don't create new abstractions here
- **Handle external complexity** - Hide implementation details from domain
- **Dependency inversion** - Implement abstractions defined in domain layer
- **Configuration injection** - Accept settings through constructor injection
- **Error translation** - Convert external errors to domain errors when appropriate

## Structure
- `provider1/`, `provider2/` - External service integrations
- `error.py` - Infrastructure-specific exceptions

## Implementation Guidelines
### External Service Providers
Implement external service integrations with both real and mock implementations.

#### Service Provider Base Class
```python
class Adapter(ABC):
    def __init__(self, client: Any):
        self._client = client

    @abstractmethod
    async def process(self, data: Any) -> Any:
        pass
```

#### Real Implementation
```python
class StripePaymentAdapter(PaymentService):
    def __init__(self, stripe_client: StripeClient, api_key: str):
        super().__init__(stripe_client)
        self._api_key = api_key

    async def process_payment(self, payment_request: PaymentRequest) -> PaymentResult:
        try:
            # Convert domain object to external API format
            stripe_request = self._to_stripe_format(payment_request)

            # Call external service
            stripe_response = await self._client.charges.create(
                amount=stripe_request.amount_cents,
                currency=stripe_request.currency,
                source=stripe_request.token,
                description=stripe_request.description
            )

            # Convert response back to domain format
            return self._to_domain_format(stripe_response)

        except StripeError as e:
            # Translate external error to domain error
            if e.code == 'card_declined':
                raise PaymentDeclinedError(str(e))
            else:
                raise PaymentServiceError(f"Payment failed: {e}")

    def _to_stripe_format(self, request: PaymentRequest) -> StripeChargeRequest:
        return StripeChargeRequest(
            amount_cents=int(request.amount.amount * 100),
            currency=request.amount.currency.code.lower(),
            token=request.payment_token,
            description=f"Order {request.order_id}"
        )

    def _to_domain_format(self, response: StripeCharge) -> PaymentResult:
        return PaymentResult(
            transaction_id=TransactionId(response.id),
            status=PaymentStatus.COMPLETED if response.paid else PaymentStatus.FAILED,
            amount=Money(Decimal(response.amount) / 100, Currency.USD)
        )
```

#### Mock Implementation (for testing)
```python
class MockPaymentAdapter(PaymentAdapter):
    def __init__(self, should_succeed: bool = True):
        super().__init__(client=None)
        self._should_succeed = should_succeed
        self._processed_payments: List[PaymentRequest] = []

    async def process_payment(self, payment_request: PaymentRequest) -> PaymentResult:
        self._processed_payments.append(payment_request)

        if not self._should_succeed:
            raise PaymentDeclinedError("Mock payment declined")

        return PaymentResult(
            transaction_id=TransactionId(f"mock_{uuid4()}"),
            status=PaymentStatus.COMPLETED,
            amount=payment_request.amount
        )

    def get_processed_payments(self) -> List[PaymentRequest]:
        return self._processed_payments.copy()
```

### Configuration and Clients
Handle external service configuration and client setup.

```python
@dataclass
class StripeConfig:
    api_key: str
    webhook_secret: str
    api_version: str = "2023-10-16"

class StripeClientFactory:
    @staticmethod
    def create(config: StripeConfig) -> StripeClient:
        stripe.api_key = config.api_key
        stripe.api_version = config.api_version
        return stripe  # or wrapped client
```

### Error Handling
Convert external errors to appropriate domain or infrastructure errors.

## What Belongs Here
- **External API calls** - HTTP clients, message queue publishers
- **File system operations** - Reading/writing files, blob storage
- **Message queues** - Publishing/consuming messages
- **Email services** - Sending emails, SMS
- **Authentication providers** - OAuth, JWT validation

## What NOT to Put Here
- **Business logic** → belongs in Domain layer
- **Use case orchestration** → belongs in Application layer
- **HTTP routing** → belongs in Interface layer
- **Request/response models** → belongs in Interface layer

## Common Patterns

### Circuit Breaker Pattern
```python
class CircuitBreakerPaymentService(PaymentService):
    def __init__(self, wrapped_service: PaymentService):
        self._service = wrapped_service
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=30
        )

    async def process_payment(self, request: PaymentRequest) -> PaymentResult:
        return await self._circuit_breaker.call(
            self._service.process_payment,
            request
        )
```

### Retry Pattern
```python
class RetryableOrderRepository(OrderRepository):
    def __init__(self, wrapped_repo: OrderRepository):
        self._repo = wrapped_repo

    @retry(stop=stop_after_attempt(3), wait=wait_exponential())
    async def save(self, order: Order) -> Order:
        return await self._repo.save(order)
```

## Testing Infrastructure Layer
- **Integration tests** - Test with real external services (databases, APIs)
- **Contract tests** - Verify external service integration
- **Mock external services** - Use test databases, mock HTTP endpoints
- **Error scenario testing** - Test network failures, timeouts, etc.

## Configuration Management
- Use environment variables and configuration objects
- Separate configuration by environment (dev, staging, prod)
- Handle secrets securely

## Questions to Ask Yourself
1. **What external system am I integrating with?** - Database, API, file system, etc.
2. **What domain interface am I implementing?** - Don't create new abstractions
3. **How do I handle failures?** - Network issues, timeouts, service unavailable
4. **What configuration is needed?** - Connection strings, API keys, settings
5. **How do I test this?** - Mock services, test databases, integration tests

## Common Mistakes to Avoid
- **Leaky abstractions** - Don't expose implementation details to domain layer
- **Missing error handling** - Always handle external service failures
- **No testing strategy** - Must be able to test without real external services
- **Tight coupling** - Don't make domain dependent on infrastructure details
- **Missing configuration** - Hardcoded connection strings and API keys
- **Synchronous calls** - Use async/await for I/O operations

Remember: **The adapter layer should be swappable. Your domain should work the same whether you use Stripe or PayPal.**
