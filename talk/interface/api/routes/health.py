"""Health check routes."""

from datetime import datetime

from dishka.integrations.fastapi import FromDishka
from fastapi import APIRouter, Request
from pydantic import BaseModel

from talk.config import Settings


router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: datetime
    version: str
    git_sha: str


class CORSDebugResponse(BaseModel):
    """CORS debugging information."""

    origin: str | None
    allowed_origins: list[str]
    cors_enabled: bool
    headers: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: FromDishka[Settings]) -> HealthResponse:
    """Basic health check endpoint.

    Returns:
        Health status indicating the service is running
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="0.1.0",
        git_sha=settings.git_sha,
    )


@router.get("/health/cors", response_model=CORSDebugResponse)
async def cors_debug(request: Request) -> CORSDebugResponse:
    """Debug CORS configuration.

    Useful for troubleshooting CORS issues, especially in Safari.

    Returns:
        CORS configuration details and request headers
    """
    from talk.config import Settings

    settings = Settings()

    return CORSDebugResponse(
        origin=request.headers.get("origin"),
        allowed_origins=[
            settings.api.frontend_url,
            "http://localhost:3000",
            "http://localhost:5173",
        ],
        cors_enabled=True,
        headers=dict(request.headers),
    )
