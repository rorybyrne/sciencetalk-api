"""Login use case."""

from datetime import datetime, timezone
from uuid import uuid4

import logfire
from pydantic import BaseModel

from talk.config import Settings
from talk.domain.error import NotFoundError
from talk.domain.model.user import User
from talk.domain.model.user_identity import UserIdentity
from talk.domain.service import (
    AuthService,
    InviteService,
    JWTService,
    UserIdentityService,
    UserService,
)
from talk.domain.value import AuthProvider, InviteToken, UserId, UserIdentityId
from talk.domain.value.types import Handle, OAuthProviderInfo


class LoginRequest(BaseModel):
    """Login request from OAuth callback.

    These parameters come from the OAuth provider in the callback URL.
    """

    provider: AuthProvider  # Which provider is handling this login
    code: str  # OAuth authorization code
    state: str  # State parameter for session verification
    iss: str | None = None  # Issuer URL (Bluesky only)
    invite_token: str | None = None  # Optional invite token from URL state


class LoginResponse(BaseModel):
    """Login response."""

    token: str
    user_id: str
    handle: Handle


class LoginUseCase:
    """Use case for multi-provider user login via OAuth."""

    def __init__(
        self,
        auth_service: AuthService,
        jwt_service: JWTService,
        user_service: UserService,
        user_identity_service: UserIdentityService,
        invite_service: InviteService,
        settings: Settings,
    ) -> None:
        """Initialize login use case.

        Args:
            auth_service: Authentication domain service (handles all providers)
            jwt_service: JWT token domain service
            user_service: User domain service
            user_identity_service: User identity domain service
            invite_service: Invite domain service
            settings: Application settings
        """
        self.auth_service = auth_service
        self.jwt_service = jwt_service
        self.user_service = user_service
        self.user_identity_service = user_identity_service
        self.invite_service = invite_service
        self.settings = settings

    async def execute(self, request: LoginRequest) -> LoginResponse:
        """Execute multi-provider login flow.

        Steps:
        1. Complete OAuth flow with provider and get user info
        2. Check if user identity exists (existing user)
        3. If existing: update last_login_at and return
        4. If new: validate invite, create user + identity, accept invite
        5. Generate JWT token

        Args:
            request: Login request with OAuth callback parameters

        Returns:
            Login response with JWT token and user info

        Raises:
            ValueError: If OAuth completion fails or invite validation fails
        """
        # Step 1: Complete OAuth with provider-specific client
        provider_info = await self._complete_oauth(request)

        logfire.info(
            "OAuth completed",
            provider=provider_info.provider.value,
            provider_user_id=provider_info.provider_user_id,
            handle=provider_info.handle,
        )

        # Step 2: Check if identity exists
        existing_identity = await self.user_identity_service.get_identity_by_provider(
            provider_info.provider, provider_info.provider_user_id
        )

        with logfire.span(
            "login_user",
            handle=provider_info.handle,
            provider=provider_info.provider.value,
            is_new_user=not bool(existing_identity),
        ):
            if existing_identity:
                # Existing user - update last login
                try:
                    user = await self.user_service.get_by_id(existing_identity.user_id)
                except NotFoundError:
                    # Identity exists but user doesn't - data inconsistency, treat as new user
                    user = None
                if not user:
                    raise ValueError("User not found for existing identity")

                # Update last_login_at
                updated_identity = existing_identity.model_copy(
                    update={"last_login_at": datetime.now(timezone.utc)}
                )
                await self.user_identity_service.save(updated_identity)

                logfire.info(
                    "Existing user logged in",
                    user_id=str(user.id),
                    provider=provider_info.provider.value,
                )

                # Generate JWT token
                token = self.jwt_service.create_token(
                    user_id=str(user.id),
                    did=provider_info.provider_user_id,  # Use provider ID as "did"
                    handle=provider_info.handle,
                )

                return LoginResponse(
                    token=token,
                    user_id=str(user.id),
                    handle=user.handle,
                )

            # Step 3: New user - validate invite
            invite = await self._validate_invite(request, provider_info)

            # Step 4: Create user and identity
            user_id = UserId(uuid4())

            # Create user with handle as username
            user = User(
                id=user_id,
                handle=Handle(provider_info.handle),  # Use provider handle as username
                avatar_url=provider_info.avatar_url,
                email=provider_info.email,
                bio=None,
                karma=0,
                invite_quota=5,  # Default quota for new users
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            saved_user = await self.user_service.save(user)

            # Create identity
            identity = UserIdentity(
                id=UserIdentityId(uuid4()),
                user_id=user_id,
                provider=provider_info.provider,
                provider_user_id=provider_info.provider_user_id,
                provider_handle=provider_info.handle,
                provider_email=provider_info.email,
                is_primary=True,  # First identity is primary
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_login_at=datetime.now(timezone.utc),
            )
            await self.user_identity_service.save(identity)

            logfire.info(
                "New user created",
                user_id=str(user_id),
                provider=provider_info.provider.value,
                provider_user_id=provider_info.provider_user_id,
            )

            # Step 5: Accept invite (if one exists - seed users don't have invites)
            if invite:
                await self.invite_service.accept_invite(invite.id, user_id)

            # Generate JWT token
            token = self.jwt_service.create_token(
                user_id=str(user_id),
                did=provider_info.provider_user_id,
                handle=provider_info.handle,
            )

            return LoginResponse(
                token=token,
                user_id=str(user_id),
                handle=saved_user.handle,
            )

    async def _complete_oauth(self, request: LoginRequest) -> OAuthProviderInfo:
        """Complete OAuth via auth service.

        Args:
            request: Login request with provider and OAuth params

        Returns:
            Provider user information

        Raises:
            ValueError: If provider not supported or OAuth fails
        """
        # All providers now go through auth service
        # Bluesky adapter will handle iss parameter internally
        return await self.auth_service.complete_login(
            request.provider, request.code, request.state, request.iss
        )

    def _is_seed_user(self, provider_info: OAuthProviderInfo) -> bool:
        """Check if user is a seed user.

        Seed users can create accounts without invites and have unlimited invites.

        Args:
            provider_info: Provider user information

        Returns:
            True if user is a seed user
        """
        seed_users = self.settings.invitations.seed_users

        # Check if handle matches any seed user
        # Handles can be in various formats: "alice.bsky.social", "@alice.bsky.social", "alice@example.com"
        # Normalize by removing @ prefix if present
        handle = provider_info.handle.lstrip("@")

        return handle in [s.lstrip("@") for s in seed_users]

    async def _validate_invite(
        self, request: LoginRequest, provider_info: OAuthProviderInfo
    ):
        """Validate invite for new user.

        Seed users bypass invite requirement entirely.

        Args:
            request: Login request with optional invite token
            provider_info: Provider user information

        Returns:
            Valid invite or None for seed users

        Raises:
            ValueError: If invite validation fails
        """
        # Check if this is a seed user - they bypass invite requirement
        if self._is_seed_user(provider_info):
            logfire.info(
                "Seed user login - bypassing invite requirement",
                handle=provider_info.handle,
                provider=provider_info.provider.value,
            )
            return None  # Seed users don't need invites

        if request.invite_token:
            # Login via invite link - validate token and match identity
            invite = await self.invite_service.get_invite_by_token(
                InviteToken(root=request.invite_token)
            )

            if not invite:
                raise ValueError("Invalid invite token")

            if invite.status != "pending":
                raise ValueError("Invite already accepted")

            # Validate provider and identity match
            if invite.provider != provider_info.provider:
                raise ValueError(
                    f"Invite is for {invite.provider}, "
                    f"but you logged in with {provider_info.provider}"
                )

            if invite.invitee_provider_id != provider_info.provider_user_id:
                raise ValueError(
                    f"Invite is for {invite.invitee_handle}, "
                    f"but you logged in as {provider_info.handle}"
                )

            return invite

        else:
            # Login without invite token - check if any pending invite exists
            has_invite = await self.invite_service.check_invite_exists(
                provider_info.provider, provider_info.provider_user_id
            )

            if not has_invite:
                logfire.warn(
                    "Login rejected - no invite",
                    handle=provider_info.handle,
                    provider=provider_info.provider.value,
                    provider_user_id=provider_info.provider_user_id,
                )
                raise ValueError(
                    f"No invitation found for {provider_info.provider.value}:{provider_info.handle}. "
                    "Science Talk is currently invite-only."
                )

            # Get the invite to accept it later
            invite = await self.invite_service.find_pending_by_provider_identity(
                provider_info.provider, provider_info.provider_user_id
            )

            if not invite:
                raise ValueError("Invite not found")

            return invite
