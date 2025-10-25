"""Health check routes."""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: datetime
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint.

    Returns:
        Health status indicating the service is running
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="0.1.0",
    )
