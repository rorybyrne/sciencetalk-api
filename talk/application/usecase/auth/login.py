"""Login use case."""

import logging
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel

from talk.config import Settings
from talk.domain.model.user import User
from talk.domain.repository import UserRepository
from talk.domain.service import AuthService, InviteService, JWTService
from talk.domain.value import UserId
from talk.domain.value.types import BlueskyDID, Handle

logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    """Login request from OAuth callback.

    These parameters come from the OAuth provider in the callback URL.
    """

    code: str  # OAuth authorization code
    state: str  # State parameter for session verification
    iss: str  # Issuer URL for verification


class LoginResponse(BaseModel):
    """Login response."""

    token: str
    user_id: str
    handle: Handle


class LoginUseCase:
    """Use case for user login via Bluesky OAuth."""

    def __init__(
        self,
        auth_service: AuthService,
        jwt_service: JWTService,
        user_repository: UserRepository,
        invite_service: InviteService,
        settings: Settings,
    ) -> None:
        """Initialize login use case.

        Args:
            auth_service: Authentication domain service
            jwt_service: JWT token domain service
            user_repository: User repository
            invite_service: Invite domain service
            settings: Application settings
        """
        self.auth_service = auth_service
        self.jwt_service = jwt_service
        self.user_repository = user_repository
        self.invite_service = invite_service
        self.settings = settings

    async def execute(self, request: LoginRequest) -> LoginResponse:
        """Execute login flow.

        Steps:
        1. Complete OAuth flow and get user info via auth service
        2. Create or update user in database
        3. Generate JWT token via JWT service

        Args:
            request: Login request with OAuth callback parameters

        Returns:
            Login response with JWT token and user info

        Raises:
            BlueskyAuthError: If OAuth completion fails
        """
        # Complete OAuth flow and get user info
        user_auth_info = await self.auth_service.complete_login(
            code=request.code,
            state=request.state,
            iss=request.iss,
        )

        # Create or update user
        did = BlueskyDID(root=user_auth_info.did)
        handle = Handle(root=user_auth_info.handle)
        existing_user = await self.user_repository.find_by_bluesky_did(did)

        if existing_user:
            logger.info(f"Existing user login: {handle} (user_id={existing_user.id})")
            # Update user handle/display name/avatar if changed
            user = User(
                id=existing_user.id,
                bluesky_did=did,
                handle=handle,
                display_name=user_auth_info.display_name,
                avatar_url=user_auth_info.avatar_url,
                karma=existing_user.karma,
                invite_quota=existing_user.invite_quota,
                created_at=existing_user.created_at,
                updated_at=datetime.now(),
            )
            await self.user_repository.save(user)
        else:
            # Check if user is a seed user (unlimited inviter)
            is_seed_user = handle in self.settings.invitations.unlimited_inviters

            if not is_seed_user:
                # Check if user has invite (required for new non-seed users)
                has_invite = await self.invite_service.check_invite_exists(handle)
                if not has_invite:
                    logger.warning(
                        f"Login rejected - no invite found for new user: {handle}"
                    )
                    raise ValueError(
                        "No invite found. This platform is currently invite-only."
                    )

            # Create new user
            user_id = UserId(uuid4())
            logger.info(
                f"Creating new user: {handle} (seed_user={is_seed_user}, user_id={user_id})"
            )
            user = User(
                id=user_id,
                bluesky_did=did,
                handle=handle,
                display_name=user_auth_info.display_name,
                avatar_url=user_auth_info.avatar_url,
                karma=0,
                invite_quota=5,  # Default quota for new users
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            await self.user_repository.save(user)

            # Mark invite as accepted (only if not a seed user)
            if not is_seed_user:
                await self.invite_service.accept_invite(handle, user_id)

        # Generate JWT token
        token = self.jwt_service.create_token(
            user_id=str(user.id),
            did=user_auth_info.did,
            handle=user_auth_info.handle,
        )

        return LoginResponse(
            token=token,
            user_id=str(user.id),
            handle=user.handle,
        )
