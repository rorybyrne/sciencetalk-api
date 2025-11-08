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
from talk.domain.error import NotFoundError
from talk.domain.service import AuthService
from talk.domain.value import AuthProvider
from talk.util.jwt import JWTError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"], route_class=DishkaRoute)


class InitiateLoginRequest(BaseModel):
    """Initiate login request for multi-provider authentication.

    Supports both Twitter and Bluesky OAuth flows.
    """

    provider: AuthProvider  # Which OAuth provider to use
    # Bluesky-specific fields (optional)
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


class AuthStatusResponse(BaseModel):
    """Response for checking authentication status.

    Used by /auth/me to return current user if authenticated,
    or indicate unauthenticated state without raising an error.
    """

    authenticated: bool
    user: GetCurrentUserResponse | None = None


@router.post("/login", response_model=InitiateLoginResponse)
async def initiate_login(
    request: InitiateLoginRequest,
    auth_service: FromDishka[AuthService],
) -> InitiateLoginResponse:
    """Initiate multi-provider OAuth login flow.

    Supports Twitter and Bluesky authentication. For Bluesky, you can optionally
    specify a server URL or handle. For Twitter, the provider handles everything.

    Args:
        request: Login request with provider and optional Bluesky parameters
        auth_service: Authentication domain service from DI

    Returns:
        Authorization URL to redirect to

    Raises:
        HTTPException: If initiation fails

    Examples:
        # Twitter login (simple)
        POST /auth/login
        {
            "provider": "twitter"
        }

        # Bluesky login with server (recommended)
        POST /auth/login
        {
            "provider": "bluesky",
            "server": "https://bsky.social"
        }

        # Bluesky login with specific handle (advanced)
        POST /auth/login
        {
            "provider": "bluesky",
            "account": "alice.bsky.social"
        }

        Response:
        {
            "authorization_url": "https://twitter.com/i/oauth2/authorize?..." or
            "authorization_url": "https://bsky.social/oauth/authorize?..."
        }
    """
    try:
        logger.info(f"Initiating {request.provider.value} login")

        # Generate state for CSRF protection (in production, this should be stored securely)
        import secrets

        state = secrets.token_urlsafe(32)

        # All providers now use the same initiate_login method
        auth_url = await auth_service.initiate_login(request.provider, state)

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


@router.get("/callback/bluesky")
async def bluesky_callback(
    code: str,
    state: str,
    iss: str,
    login_use_case: FromDishka[LoginUseCase],
    settings: FromDishka[Settings],
    invite_token: str | None = None,  # Optional - for invite links
):
    """Handle Bluesky OAuth callback and complete login.

    This endpoint receives the redirect from Bluesky after the user authenticates.
    It completes the OAuth flow, creates/updates the user, issues a JWT cookie,
    and redirects to the frontend.

    Args:
        code: Authorization code from Bluesky
        state: State parameter for session verification
        iss: Issuer URL (AT Protocol requirement)
        login_use_case: Login use case from DI
        settings: Application settings from DI
        invite_token: Optional invite token from URL state

    Returns:
        HTTP 302 redirect to frontend with Set-Cookie header

    Raises:
        HTTPException: If login fails

    Example:
        GET /auth/callback/bluesky?code=abc123&state=xyz789&iss=https://bsky.social

        Redirects to: https://talk.amacrin.com/
        Sets cookie: auth_token
    """
    return await _handle_oauth_callback(
        provider=AuthProvider.BLUESKY,
        code=code,
        state=state,
        iss=iss,
        invite_token=invite_token,
        login_use_case=login_use_case,
        settings=settings,
    )


@router.get("/callback/twitter")
async def twitter_callback(
    code: str,
    state: str,
    login_use_case: FromDishka[LoginUseCase],
    settings: FromDishka[Settings],
    invite_token: str | None = None,  # Optional - for invite links
):
    """Handle Twitter OAuth callback and complete login.

    This endpoint receives the redirect from Twitter after the user authenticates.
    It completes the OAuth flow, creates/updates the user, issues a JWT cookie,
    and redirects to the frontend.

    Args:
        code: Authorization code from Twitter
        state: State parameter for session verification
        login_use_case: Login use case from DI
        settings: Application settings from DI
        invite_token: Optional invite token from URL state

    Returns:
        HTTP 302 redirect to frontend with Set-Cookie header

    Raises:
        HTTPException: If login fails

    Example:
        GET /auth/callback/twitter?code=abc123&state=xyz789

        Redirects to: https://talk.amacrin.com/
        Sets cookie: auth_token
    """
    return await _handle_oauth_callback(
        provider=AuthProvider.TWITTER,
        code=code,
        state=state,
        iss=None,
        invite_token=invite_token,
        login_use_case=login_use_case,
        settings=settings,
    )


async def _handle_oauth_callback(
    provider: AuthProvider,
    code: str,
    state: str,
    iss: str | None,
    invite_token: str | None,
    login_use_case: LoginUseCase,
    settings: Settings,
):
    """Shared OAuth callback handler for all providers.

    This internal function handles the common OAuth callback logic
    after provider-specific parameters have been extracted.
    """
    logger.info(
        f"OAuth callback received: provider={provider.value}, state={state}, iss={iss}"
    )

    try:
        # Execute login use case
        logger.info("Executing login use case...")
        login_response = await login_use_case.execute(
            LoginRequest(
                provider=provider,
                code=code,
                state=state,
                iss=iss,
                invite_token=invite_token,
            )
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


@router.get("/me", response_model=AuthStatusResponse)
async def get_current_user(
    get_current_user_use_case: FromDishka[GetCurrentUserUseCase],
    auth_token: str | None = Cookie(default=None),
) -> AuthStatusResponse:
    """Get current user if authenticated, or return unauthenticated status.

    This endpoint is safe to call without authentication - it will return
    authenticated=false instead of raising an error. This allows the frontend
    to check authentication state without generating errors in logs.

    Args:
        get_current_user_use_case: Get current user use case from DI
        auth_token: JWT token from cookie (optional)

    Returns:
        Authentication status with user information if authenticated

    Examples:
        Authenticated:
        {
            "authenticated": true,
            "user": {
                "user_id": "...",
                "handle": "alice.bsky.social",
                ...
            }
        }

        Unauthenticated:
        {
            "authenticated": false,
            "user": null
        }
    """
    if not auth_token:
        return AuthStatusResponse(authenticated=False)

    try:
        user = await get_current_user_use_case.execute(
            GetCurrentUserRequest(token=auth_token)
        )
        return AuthStatusResponse(authenticated=True, user=user)

    except JWTError:
        # Invalid or expired token - this is expected behavior, not an error
        return AuthStatusResponse(authenticated=False)
    except NotFoundError:
        # JWT valid but user not found in database (orphaned token)
        return AuthStatusResponse(authenticated=False)
