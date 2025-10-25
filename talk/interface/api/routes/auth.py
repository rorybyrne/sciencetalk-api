"""Authentication routes."""

from dishka.integrations.fastapi import FromDishka
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

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginCallbackResponse(BaseModel):
    """Login callback response."""

    success: bool
    message: str


@router.get("/login")
async def initiate_login(
    auth_service: FromDishka[AuthService],
) -> dict:
    """Initiate OAuth login flow.

    Redirects user to Bluesky OAuth authorization page.

    Args:
        auth_service: Authentication domain service from DI

    Returns:
        Authorization URL to redirect to
    """
    auth_url = auth_service.get_oauth_url()
    return {"authorization_url": auth_url}


@router.get("/callback", response_model=LoginCallbackResponse)
async def login_callback(
    code: str,
    response: Response,
    login_use_case: FromDishka[LoginUseCase],
    settings: FromDishka[Settings],
) -> LoginCallbackResponse:
    """Handle OAuth callback and complete login.

    Exchanges authorization code for user info, creates/updates user,
    and sets authentication cookie.

    Args:
        code: Authorization code from OAuth provider
        response: FastAPI response object
        login_use_case: Login use case from DI
        settings: Application settings from DI

    Returns:
        Login success response

    Raises:
        HTTPException: If login fails
    """
    try:
        # Execute login use case
        login_response = await login_use_case.execute(LoginRequest(code=code))

        # Set HTTP-only cookie with JWT token
        response.set_cookie(
            key="auth_token",
            value=login_response.token,
            httponly=True,
            secure=settings.environment == "production",  # HTTPS only in production
            samesite="lax",
            max_age=settings.auth.jwt_expiry_days * 24 * 60 * 60,  # seconds
        )

        return LoginCallbackResponse(
            success=True,
            message=f"Successfully logged in as {login_response.handle}",
        )

    except BlueskyAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )


@router.post("/logout")
async def logout(response: Response) -> dict:
    """Logout user by clearing authentication cookie.

    Args:
        response: FastAPI response object

    Returns:
        Logout success message
    """
    response.delete_cookie(key="auth_token")
    return {"success": True, "message": "Successfully logged out"}


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
