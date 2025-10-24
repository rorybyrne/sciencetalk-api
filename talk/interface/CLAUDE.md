# Interface Layer - CLAUDE.md

## Purpose
The interface layer handles **external communication** with users and systems. It translates between external protocols (HTTP, CLI, GraphQL) and your application's use cases. This layer should be thin and focus only on protocol concerns.

## Key Principles
- **Protocol translation** - Convert between external formats and internal models
- **Input validation** - Validate format, types, and required fields
- **Error mapping** - Convert internal errors to appropriate external responses
- **No business logic** - Delegate everything to application layer
- **Framework isolation** - Keep framework-specific code contained here

## Structure
- `api/` - HTTP API implementation (FastAPI, Flask, etc.)
- `cli/` - Command-line interface (if applicable)
- `graphql/` - GraphQL endpoints (if applicable)
- `error.py` - Interface-specific exceptions

## Implementation Guidelines

### API Routes (`api/routes/`)
Handle HTTP requests and responses, delegating business logic to use cases.

```python
from fastapi import APIRouter, Depends, HTTPException, status
from dishka.integrations.fastapi import FromDishka

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=CreateOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: CreateOrderRequest,
    use_case: FromDishka[CreateOrderUseCase]
) -> CreateOrderResponse:
    try:
        # 1. Validate input (format validation)
        request.validate()

        # 2. Convert to use case request
        use_case_request = CreateOrderUseCaseRequest.from_api_request(request)

        # 3. Execute use case
        use_case_response = await use_case.execute(use_case_request)

        # 4. Convert to API response
        return CreateOrderResponse.from_use_case_response(use_case_response)

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except CustomerNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    except InsufficientInventoryError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Insufficient inventory"
        )
    except ApplicationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{order_id}", response_model=GetOrderResponse)
async def get_order(
    order_id: str,
    use_case: FromDishka[GetOrderUseCase]
) -> GetOrderResponse:
    try:
        # Convert path parameter to use case request
        use_case_request = GetOrderUseCaseRequest(order_id=OrderId(order_id))

        # Execute use case
        use_case_response = await use_case.execute(use_case_request)

        # Convert to API response
        return GetOrderResponse.from_use_case_response(use_case_response)

    except OrderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
```

### Request Models (`api/model/request.py`)
Define and validate incoming data structures.

```python
from pydantic import BaseModel, validator
from typing import List, Optional
from decimal import Decimal

class CreateOrderRequest(BaseModel):
    customer_id: str
    items: List[OrderItemRequest]
    shipping_address: Optional[AddressRequest] = None

    @validator('customer_id')
    def validate_customer_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Customer ID is required')
        return v.strip()

    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError('Order must have at least one item')
        return v

    def validate(self) -> None:
        """Additional validation that can't be done with Pydantic validators."""
        total_quantity = sum(item.quantity for item in self.items)
        if total_quantity > 100:
            raise ValidationError("Cannot order more than 100 items total")

class OrderItemRequest(BaseModel):
    product_id: str
    quantity: int
    unit_price: Optional[Decimal] = None

    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v
```

### Response Models (`api/model/response.py`)
Define outgoing data structures and conversions from use case responses.

```python
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

class CreateOrderResponse(BaseModel):
    order_id: str
    customer_id: str
    total_amount: Decimal
    status: str
    created_at: datetime

    @classmethod
    def from_use_case_response(cls, response: CreateOrderUseCaseResponse) -> 'CreateOrderResponse':
        return cls(
            order_id=response.order_id,
            customer_id=response.customer_id,
            total_amount=response.total_amount,
            status=response.status,
            created_at=response.created_at
        )

class GetOrderResponse(BaseModel):
    order_id: str
    customer_id: str
    items: List[OrderItemResponse]
    total_amount: Decimal
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_use_case_response(cls, response: GetOrderUseCaseResponse) -> 'GetOrderResponse':
        return cls(
            order_id=response.order_id,
            customer_id=response.customer_id,
            items=[
                OrderItemResponse.from_use_case_item(item)
                for item in response.items
            ],
            total_amount=response.total_amount,
            status=response.status,
            created_at=response.created_at,
            updated_at=response.updated_at
        )

class OrderItemResponse(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
```

### Error Handling
Map internal errors to appropriate HTTP status codes and messages.

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Handle domain layer errors."""
    error_mappings = {
        CustomerNotFoundError: (404, "Customer not found"),
        OrderNotFoundError: (404, "Order not found"),
        InsufficientInventoryError: (409, "Insufficient inventory"),
        InvalidOrderStateError: (400, "Invalid order state"),
        PaymentDeclinedError: (402, "Payment declined"),
    }

    status_code, message = error_mappings.get(
        type(exc),
        (500, "Internal server error")
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": type(exc).__name__,
            "message": message,
            "detail": str(exc) if status_code != 500 else None
        }
    )

async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "message": "Invalid input data",
            "details": exc.errors()
        }
    )
```

### Application Setup (`api/app.py`)
Configure the FastAPI application with routes, middleware, and error handlers.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dishka import make_container
from dishka.integrations.fastapi import setup_dishka

from .routes import health, orders, customers
from .error import domain_error_handler, validation_error_handler
from ...util.di.container import create_container

def create_app() -> FastAPI:
    app = FastAPI(
        title="Order Management API",
        description="API for managing orders and customers",
        version="1.0.0"
    )

    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup dependency injection
    container = create_container()
    setup_dishka(container, app)

    # Register routes
    app.include_router(health.router)
    app.include_router(orders.router)
    app.include_router(customers.router)

    # Register error handlers
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    return app

app = create_app()
```

### Health Checks
Provide endpoints for monitoring and health checking.

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from dishka.integrations.fastapi import FromDishka

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    dependencies: dict

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        dependencies={}
    )

@router.get("/health/detailed", response_model=HealthResponse)
async def detailed_health_check(
    order_repo: FromDishka[OrderRepository],
    payment_service: FromDishka[PaymentService]
) -> HealthResponse:
    """Detailed health check with dependency verification."""
    dependencies = {}

    # Check database
    try:
        await order_repo.health_check()
        dependencies["database"] = "healthy"
    except Exception as e:
        dependencies["database"] = f"unhealthy: {e}"

    # Check payment service
    try:
        await payment_service.health_check()
        dependencies["payment_service"] = "healthy"
    except Exception as e:
        dependencies["payment_service"] = f"unhealthy: {e}"

    overall_status = "healthy" if all(
        status == "healthy" for status in dependencies.values()
    ) else "unhealthy"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        dependencies=dependencies
    )
```

## What Belongs Here
- **HTTP request/response handling** - Routes, middleware, status codes
- **Input validation** - Format validation, required fields, data types
- **Output formatting** - JSON serialization, response models
- **Authentication/authorization** - JWT validation, API keys, permissions
- **Rate limiting** - Request throttling, quota management
- **CORS configuration** - Cross-origin request handling
- **API documentation** - OpenAPI/Swagger configuration

## What NOT to Put Here
- **Business logic** → belongs in Domain layer
- **Use case orchestration** → belongs in Application layer
- **Database operations** → belongs in Infrastructure layer
- **External service calls** → belongs in Infrastructure layer

## Common Patterns

### Pagination
```python
from fastapi import Query
from typing import Optional

class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(20, ge=1, le=100, description="Page size")
    ):
        self.page = page
        self.size = size
        self.offset = (page - 1) * size

@router.get("/orders", response_model=PaginatedOrderResponse)
async def list_orders(
    pagination: PaginationParams = Depends(),
    use_case: FromDishka[ListOrdersUseCase]
) -> PaginatedOrderResponse:
    request = ListOrdersUseCaseRequest(
        offset=pagination.offset,
        limit=pagination.size
    )
    response = await use_case.execute(request)
    return PaginatedOrderResponse.from_use_case_response(response)
```

### Filtering and Sorting
```python
from enum import Enum
from typing import Optional

class OrderSortBy(str, Enum):
    CREATED_AT = "created_at"
    TOTAL_AMOUNT = "total_amount"
    STATUS = "status"

class OrderStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"

@router.get("/orders", response_model=PaginatedOrderResponse)
async def list_orders(
    status: Optional[OrderStatus] = Query(None),
    sort_by: OrderSortBy = Query(OrderSortBy.CREATED_AT),
    sort_desc: bool = Query(False),
    pagination: PaginationParams = Depends(),
    use_case: FromDishka[ListOrdersUseCase]
) -> PaginatedOrderResponse:
    # Convert API parameters to use case request
    pass
```

### File Upload
```python
from fastapi import UploadFile, File

@router.post("/orders/{order_id}/attachments")
async def upload_attachment(
    order_id: str,
    file: UploadFile = File(...),
    use_case: FromDishka[AddOrderAttachmentUseCase]
) -> AttachmentResponse:
    # Validate file type and size
    if file.content_type not in ["image/jpeg", "image/png", "application/pdf"]:
        raise HTTPException(400, "Invalid file type")

    if file.size > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(400, "File too large")

    # Read file content
    content = await file.read()

    # Execute use case
    request = AddOrderAttachmentUseCaseRequest(
        order_id=OrderId(order_id),
        filename=file.filename,
        content_type=file.content_type,
        content=content
    )
    response = await use_case.execute(request)
    return AttachmentResponse.from_use_case_response(response)
```

## Testing Interface Layer
- **API tests** - Test HTTP endpoints with test client
- **Contract tests** - Verify API contracts and OpenAPI specification
- **Integration tests** - Test full request/response cycle
- **Mock use cases** - Test interface logic without business logic

```python
from fastapi.testclient import TestClient
import pytest

def test_create_order_success(test_client: TestClient, mock_create_order_use_case):
    # Arrange
    request_data = {
        "customer_id": "123",
        "items": [
            {"product_id": "456", "quantity": 2}
        ]
    }

    # Act
    response = test_client.post("/orders/", json=request_data)

    # Assert
    assert response.status_code == 201
    response_data = response.json()
    assert "order_id" in response_data
    assert response_data["customer_id"] == "123"

def test_create_order_validation_error(test_client: TestClient):
    # Missing required field
    request_data = {
        "items": [
            {"product_id": "456", "quantity": 2}
        ]
    }

    response = test_client.post("/orders/", json=request_data)
    assert response.status_code == 422
```

## Security Considerations
- **Input validation** - Validate all inputs, sanitize data
- **Authentication** - Verify user identity
- **Authorization** - Check user permissions
- **Rate limiting** - Prevent abuse
- **HTTPS only** - Encrypt data in transit
- **CORS configuration** - Control cross-origin requests

## Questions to Ask Yourself
1. **What protocol am I supporting?** - HTTP REST, GraphQL, WebSocket, CLI
2. **What authentication is needed?** - JWT, API keys, OAuth, none
3. **How do I validate input?** - Required fields, formats, business rules
4. **What error responses are appropriate?** - Status codes, error messages
5. **How do I document the API?** - OpenAPI, examples, descriptions

## Common Mistakes to Avoid
- **Business logic in controllers** - Keep routes thin, delegate to use cases
- **Exposing internal errors** - Don't leak stack traces or internal details
- **Missing input validation** - Always validate before passing to use cases
- **Inconsistent error responses** - Use standard error formats
- **Poor API design** - Follow REST principles and HTTP standards
- **No versioning strategy** - Plan for API evolution

Remember: **The interface layer is your application's public face. Make it clean, consistent, and well-documented.**
