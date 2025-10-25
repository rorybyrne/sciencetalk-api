"""Login use case."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel

from talk.domain.model.user import User
from talk.domain.repository import UserRepository
from talk.domain.service import AuthService, JWTService
from talk.domain.value import UserId
from talk.domain.value.types import BlueskyDID, Handle


class LoginRequest(BaseModel):
    """Login request."""

    code: str  # OAuth authorization code


class LoginResponse(BaseModel):
    """Login response."""

    token: str
    user_id: str
    handle: str


class LoginUseCase:
    """Use case for user login via Bluesky OAuth."""

    def __init__(
        self,
        auth_service: AuthService,
        jwt_service: JWTService,
        user_repository: UserRepository,
    ) -> None:
        """Initialize login use case.

        Args:
            auth_service: Authentication domain service
            jwt_service: JWT token domain service
            user_repository: User repository
        """
        self.auth_service = auth_service
        self.jwt_service = jwt_service
        self.user_repository = user_repository

    async def execute(self, request: LoginRequest) -> LoginResponse:
        """Execute login flow.

        Steps:
        1. Authenticate with OAuth code via auth service
        2. Create or update user in database
        3. Generate JWT token via JWT service

        Args:
            request: Login request with OAuth code

        Returns:
            Login response with JWT token and user info

        Raises:
            BlueskyAuthError: If OAuth fails
        """
        # Authenticate user via OAuth
        user_auth_info = await self.auth_service.authenticate_with_code(request.code)

        # Create or update user
        did = BlueskyDID(value=user_auth_info.did)
        existing_user = await self.user_repository.find_by_bluesky_did(did)

        if existing_user:
            # Update user handle/display name/avatar if changed
            user = User(
                id=existing_user.id,
                bluesky_did=did,
                handle=Handle(value=user_auth_info.handle),
                display_name=user_auth_info.display_name,
                avatar_url=user_auth_info.avatar_url,
                karma=existing_user.karma,
                created_at=existing_user.created_at,
                updated_at=datetime.now(),
            )
            await self.user_repository.save(user)
        else:
            # Create new user
            user = User(
                id=UserId(uuid4()),
                bluesky_did=did,
                handle=Handle(value=user_auth_info.handle),
                display_name=user_auth_info.display_name,
                avatar_url=user_auth_info.avatar_url,
                karma=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            await self.user_repository.save(user)

        # Generate JWT token
        token = self.jwt_service.create_token(
            user_id=str(user.id),
            did=user_auth_info.did,
            handle=user_auth_info.handle,
        )

        return LoginResponse(
            token=token,
            user_id=str(user.id),
            handle=user_auth_info.handle,
        )
