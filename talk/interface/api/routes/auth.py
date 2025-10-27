"""Authentication routes."""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Cookie, HTTPException, Response, status
from pydantic import BaseModel

from talk.adapter.bluesky.auth import BlueskyAuthError
from talk.application.usecase.auth import GetCurrentUserUseCase, LoginUseCase
from talk.application.usecase.auth.get_current_user import (
    GetCurrentUserRequest,
    GetCurrentUserResponse,
)
from talk.application.usecase.auth.login import LoginRequest
from talk.config import Settings
from talk.domain.service import AuthService
from talk.util.jwt import JWTError

router = APIRouter(prefix="/auth", tags=["authentication"], route_class=DishkaRoute)


class InitiateLoginRequest(BaseModel):
    """Initiate login request."""

    account: str


class InitiateLoginResponse(BaseModel):
    """Initiate login response."""

    authorization_url: str


class LogoutResponse(BaseModel):
    """Logout response."""

    success: bool
    message: str


@router.post("/login", response_model=InitiateLoginResponse)
async def initiate_login(
    request: InitiateLoginRequest,
    auth_service: FromDishka[AuthService],
) -> InitiateLoginResponse:
    """Initiate OAuth login flow.

    Accepts a Bluesky handle or DID and returns the authorization URL
    to redirect the user to for authentication.

    Args:
        request: Login request with account (handle or DID)
        auth_service: Authentication domain service from DI

    Returns:
        Authorization URL to redirect to

    Raises:
        HTTPException: If initiation fails

    Example:
        POST /auth/login
        {
            "account": "alice.bsky.social"
        }

        Response:
        {
            "authorization_url": "https://bsky.social/oauth/authorize?..."
        }
    """
    try:
        auth_url = await auth_service.initiate_login(request.account)
        return InitiateLoginResponse(authorization_url=auth_url)
    except BlueskyAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate login: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )


@router.get("/callback")
async def login_callback(
    code: str,
    state: str,
    iss: str,
    response: Response,
    login_use_case: FromDishka[LoginUseCase],
    settings: FromDishka[Settings],
):
    """Handle OAuth callback and complete login.

    This endpoint receives the redirect from the OAuth provider after
    the user authenticates. It completes the OAuth flow, creates/updates
    the user, issues a JWT cookie, and redirects to the frontend.

    Args:
        code: Authorization code from OAuth provider
        state: State parameter for session verification
        iss: Issuer URL for verification
        response: FastAPI response object
        login_use_case: Login use case from DI
        settings: Application settings from DI

    Returns:
        HTTP 302 redirect to frontend

    Raises:
        HTTPException: If login fails

    Example:
        GET /auth/callback?code=abc123&state=xyz789&iss=https://bsky.social

        Redirects to: https://frontend.example.com/
        Sets cookie: auth_token (HTTP-only, Secure, SameSite=Lax)
    """
    try:
        # Execute login use case
        login_response = await login_use_case.execute(
            LoginRequest(code=code, state=state, iss=iss)
        )

        # Set HTTP-only cookie with JWT token
        # Production (cross-subdomain): talk.amacrin.com → api.talk.amacrin.com
        #   - samesite="none" required for cross-site requests
        #   - secure=True required when samesite="none"
        #   - domain=".amacrin.com" to share across subdomains
        # Development (same-origin): localhost:3000 → localhost:8000
        #   - samesite="lax" for same-origin requests
        #   - secure=False to allow HTTP
        #   - domain=None (default to current host)
        is_production = settings.environment == "production"
        response.set_cookie(
            key="auth_token",
            value=login_response.token,
            httponly=True,
            secure=is_production,  # HTTPS required in production
            samesite="none"
            if is_production
            else "lax",  # "none" for cross-subdomain, "lax" for localhost
            domain=".amacrin.com"
            if is_production
            else None,  # Share across subdomains in production only
            path="/",
            max_age=settings.auth.jwt_expiry_days * 24 * 60 * 60,  # seconds
        )

        # Redirect to frontend
        from fastapi.responses import RedirectResponse

        return RedirectResponse(
            url=settings.api.frontend_url,
            status_code=status.HTTP_302_FOUND,
        )

    except ValueError as e:
        # Invite-only error
        from fastapi.responses import RedirectResponse

        return RedirectResponse(
            url=f"{settings.api.frontend_url}/auth/error?error=no_invite&message={str(e)}",
            status_code=status.HTTP_302_FOUND,
        )
    except BlueskyAuthError as e:
        # OAuth error
        from fastapi.responses import RedirectResponse

        return RedirectResponse(
            url=f"{settings.api.frontend_url}/auth/error?error=auth_failed&message={str(e)}",
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as e:
        # Unexpected error
        from fastapi.responses import RedirectResponse

        return RedirectResponse(
            url=f"{settings.api.frontend_url}/auth/error?error=unexpected&message={str(e)}",
            status_code=status.HTTP_302_FOUND,
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    settings: FromDishka[Settings],
) -> LogoutResponse:
    """Logout user by clearing authentication cookie.

    Args:
        response: FastAPI response object
        settings: Application settings from DI

    Returns:
        Logout success message
    """
    # Delete cookie with same domain/path as when it was created
    is_production = settings.environment == "production"
    response.delete_cookie(
        key="auth_token",
        domain=".amacrin.com" if is_production else None,
        path="/",
    )
    return LogoutResponse(success=True, message="Successfully logged out")


@router.get("/me", response_model=GetCurrentUserResponse)
async def get_current_user(
    get_current_user_use_case: FromDishka[GetCurrentUserUseCase],
    auth_token: str | None = Cookie(default=None),
) -> GetCurrentUserResponse:
    """Get currently authenticated user.

    Args:
        get_current_user_use_case: Get current user use case from DI
        auth_token: JWT token from cookie

    Returns:
        Current user information

    Raises:
        HTTPException: If not authenticated or token invalid
    """
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        user = await get_current_user_use_case.execute(
            GetCurrentUserRequest(token=auth_token)
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        return user

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
