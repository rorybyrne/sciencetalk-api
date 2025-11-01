"""Authentication routes."""

import logging

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Cookie, HTTPException, Response, status
from fastapi.responses import RedirectResponse
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"], route_class=DishkaRoute)


class InitiateLoginRequest(BaseModel):
    """Initiate login request.

    Two modes:
    1. Server-based (recommended): Omit account, optionally specify server
    2. Handle-based (advanced): Provide specific handle or DID
    """

    account: str | None = None  # Optional: handle/DID for advanced users
    server: str = "https://bsky.social"  # Server URL (default to Bluesky)
    login_hint: str | None = None  # Optional hint for auth server


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

    Two modes supported:

    1. **Server-based (recommended)**: Simple "Sign in with Bluesky" button
       - No handle input required
       - Works for 99% of users
       - Just send empty request body or specify custom server

    2. **Handle-based (advanced)**: For custom PDS or explicit targeting
       - Provide specific handle or DID
       - Useful for non-Bluesky servers

    Args:
        request: Login request with optional account and server
        auth_service: Authentication domain service from DI

    Returns:
        Authorization URL to redirect to

    Raises:
        HTTPException: If initiation fails

    Examples:
        # Simple: Sign in with Bluesky (recommended)
        POST /auth/login
        {}

        # Advanced: Specific handle
        POST /auth/login
        {
            "account": "alice.bsky.social"
        }

        # Advanced: Custom PDS server
        POST /auth/login
        {
            "server": "https://custom-pds.example.com"
        }

        # With login hint
        POST /auth/login
        {
            "server": "https://bsky.social",
            "login_hint": "alice@example.com"
        }

        Response:
        {
            "authorization_url": "https://bsky.social/oauth/authorize?..."
        }
    """
    try:
        if request.account:
            # Handle-based flow (existing/advanced)
            logger.info(f"Initiating handle-based login for: {request.account}")
            auth_url = await auth_service.initiate_login(request.account)
        else:
            # Server-based flow (new/recommended)
            logger.info(f"Initiating server-based login with: {request.server}")
            auth_url = await auth_service.initiate_login_with_server(
                server_url=request.server, login_hint=request.login_hint
            )

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
        login_use_case: Login use case from DI
        settings: Application settings from DI

    Returns:
        HTTP 302 redirect to frontend with Set-Cookie header

    Raises:
        HTTPException: If login fails

    Example:
        GET /auth/callback?code=abc123&state=xyz789&iss=https://bsky.social

        Redirects to: https://talk.amacrin.com/
        Sets cookie: auth_token
          - Production: HttpOnly, Secure, SameSite=None, Domain=.amacrin.com
          - Development: HttpOnly, SameSite=Lax
    """
    logger.info(f"OAuth callback received: state={state}, iss={iss}")

    try:
        # Execute login use case
        logger.info("Executing login use case...")
        login_response = await login_use_case.execute(
            LoginRequest(code=code, state=state, iss=iss)
        )
        logger.info(f"Login successful for user: {login_response.handle}")

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

        # Prepare cookie settings
        cookie_domain = ".amacrin.com" if is_production else None
        cookie_secure = is_production
        cookie_samesite = "none" if is_production else "lax"
        cookie_max_age = settings.auth.jwt_expiry_days * 24 * 60 * 60

        logger.info(
            f"Setting auth cookie with settings: "
            f"environment={settings.environment}, "
            f"is_production={is_production}, "
            f"domain={cookie_domain}, "
            f"secure={cookie_secure}, "
            f"samesite={cookie_samesite}, "
            f"httponly=True, "
            f"path=/, "
            f"max_age={cookie_max_age}"
        )

        # Create redirect response and set cookie on it
        # IMPORTANT: When returning a Response directly (like RedirectResponse),
        # cookies must be set on that response object, not the response parameter
        redirect_url = settings.api.frontend_url
        redirect_response = RedirectResponse(
            url=redirect_url,
            status_code=status.HTTP_302_FOUND,
        )

        redirect_response.set_cookie(
            key="auth_token",
            value=login_response.token,
            httponly=True,
            secure=cookie_secure,
            samesite=cookie_samesite,
            domain=cookie_domain,
            path="/",
            max_age=cookie_max_age,
        )

        logger.info(f"Auth cookie set successfully, redirecting to: {redirect_url}")

        return redirect_response

    except ValueError as e:
        # Invite-only error
        logger.error(f"Invite-only error during OAuth callback: {str(e)}")
        return RedirectResponse(
            url=f"{settings.api.frontend_url}/auth/error?error=no_invite&message={str(e)}",
            status_code=status.HTTP_302_FOUND,
        )
    except BlueskyAuthError as e:
        # OAuth error
        logger.error(f"Bluesky OAuth error during callback: {str(e)}")
        return RedirectResponse(
            url=f"{settings.api.frontend_url}/auth/error?error=auth_failed&message={str(e)}",
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error during OAuth callback: {str(e)}")
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
