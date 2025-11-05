"""Create invites use case."""

import secrets
from datetime import datetime

import logfire
from pydantic import BaseModel, Field

from talk.adapter.bluesky.identity import (
    IdentityResolutionError,
    resolve_handle_to_did,
)
from talk.application.usecase.base import BaseUseCase
from talk.config import Settings
from talk.domain.model.invite import Invite
from talk.domain.service import InviteService, UserIdentityService, UserService
from talk.domain.value import AuthProvider, InviteStatus, InviteToken, UserId
from talk.domain.value.types import Handle


class InviteeInfo(BaseModel):
    """Info for a single invitee."""

    provider: AuthProvider
    handle: str
    name: str | None = None


class CreateInvitesRequest(BaseModel):
    """Request to create invites."""

    inviter_id: str
    invitees: list[InviteeInfo] = Field(max_length=10)  # Max 10 at once


class InviteItem(BaseModel):
    """Invite item in response."""

    invite_id: str
    invite_url: str  # Full invite URL with token
    invite_token: str  # Just the token
    provider: AuthProvider
    invitee_handle: str
    invitee_name: str | None
    status: InviteStatus
    created_at: datetime


class CreateInvitesResponse(BaseModel):
    """Response after creating invites."""

    invites: list[InviteItem]
    failed_invitees: list[str]  # Format: "provider:handle" for failures
    remaining_quota: int


class CreateInvitesUseCase(BaseUseCase):
    """Use case for creating multiple multi-provider invites."""

    def __init__(
        self,
        invite_service: InviteService,
        user_service: UserService,
        user_identity_service: UserIdentityService,
        settings: Settings,
    ) -> None:
        """Initialize use case.

        Args:
            invite_service: Invite domain service
            user_service: User domain service
            user_identity_service: User identity domain service
            settings: Application settings
        """
        self.invite_service = invite_service
        self.user_service = user_service
        self.user_identity_service = user_identity_service
        self.settings = settings

    async def execute(self, request: CreateInvitesRequest) -> CreateInvitesResponse:
        """Execute create multi-provider invites use case.

        Args:
            request: Create invites request

        Returns:
            Response with created invites, failures, and remaining quota

        Raises:
            ValueError: If user not found or quota exceeded
        """
        from uuid import UUID

        inviter_id = UserId(UUID(request.inviter_id))

        with logfire.span(
            "create_invites",
            inviter_id=str(inviter_id),
            invite_count=len(request.invitees),
        ):
            # Get inviter
            inviter = await self.user_service.get_user_by_id(inviter_id)
            if not inviter:
                raise ValueError("User not found")

            # Check if user is a seed user (unlimited invites)
            is_seed_user = self._is_seed_user(inviter.handle)

            # Check quota (seed users have unlimited quota)
            if not is_seed_user:
                available_quota = await self.invite_service.get_available_quota(
                    inviter.invite_quota, inviter_id
                )

                if len(request.invitees) > available_quota:
                    logfire.warn(
                        "Invite quota exceeded",
                        inviter_id=str(inviter_id),
                        requested=len(request.invitees),
                        available=available_quota,
                    )
                    raise ValueError(
                        f"Insufficient invite quota. Available: {available_quota}, "
                        f"Requested: {len(request.invitees)}"
                    )
            else:
                logfire.info(
                    "Seed user creating invites - unlimited quota",
                    inviter_id=str(inviter_id),
                    invite_count=len(request.invitees),
                )

            # Create invites
            created_invites: list[Invite] = []
            failed_invitees: list[str] = []

            for invitee in request.invitees:
                try:
                    # Normalize handle and resolve to permanent ID
                    (
                        normalized_handle,
                        provider_user_id,
                    ) = await self._normalize_and_resolve(
                        invitee.provider, invitee.handle
                    )

                    # Check if identity already exists
                    existing_identity = (
                        await self.user_identity_service.get_identity_by_provider(
                            invitee.provider, provider_user_id
                        )
                    )
                    if existing_identity:
                        failed_invitees.append(
                            f"{invitee.provider.value}:{invitee.handle}"
                        )
                        continue

                    # Generate unique token
                    invite_token = InviteToken(root=secrets.token_urlsafe(32))

                    # Create invite via service
                    invite = await self.invite_service.create_invite(
                        inviter_id=inviter_id,
                        provider=invitee.provider,
                        invitee_handle=normalized_handle,
                        invitee_provider_id=provider_user_id,
                        invitee_name=invitee.name,
                        invite_token=invite_token,
                    )
                    created_invites.append(invite)

                except (IdentityResolutionError, ValueError) as e:
                    # Handle resolution failed or duplicate invite
                    failed_invitees.append(f"{invitee.provider.value}:{invitee.handle}")
                    logfire.warn(
                        "Failed to create invite",
                        provider=invitee.provider.value,
                        handle=invitee.handle,
                        error=str(e),
                    )
                except Exception as e:
                    # Other errors
                    failed_invitees.append(f"{invitee.provider.value}:{invitee.handle}")
                    logfire.error(
                        "Unexpected error creating invite",
                        provider=invitee.provider.value,
                        handle=invitee.handle,
                        error=str(e),
                    )

            # Calculate remaining quota (seed users have "unlimited" represented as 999999)
            if is_seed_user:
                remaining_quota = 999999  # Effectively unlimited
            else:
                remaining_quota = await self.invite_service.get_available_quota(
                    inviter.invite_quota, inviter_id
                )

            # Convert invites to response items
            frontend_url = self.settings.api.frontend_url
            invite_items = [
                InviteItem(
                    invite_id=str(invite.id),
                    invite_url=f"{frontend_url}/invites/{invite.invite_token.root}",
                    invite_token=invite.invite_token.root,
                    provider=invite.provider,
                    invitee_handle=invite.invitee_handle,
                    invitee_name=invite.invitee_name,
                    status=invite.status,
                    created_at=invite.created_at,
                )
                for invite in created_invites
            ]

            return CreateInvitesResponse(
                invites=invite_items,
                failed_invitees=failed_invitees,
                remaining_quota=remaining_quota,
            )

    def _is_seed_user(self, handle: Handle) -> bool:
        """Check if user is a seed user (has unlimited invites).

        Args:
            handle: User handle to check

        Returns:
            True if user is a seed user
        """
        seed_users = self.settings.invitations.seed_users

        # Normalize handle by removing @ prefix if present
        # Handle is a Pydantic value object with a root attribute
        normalized_handle = handle.root.lstrip("@")

        return normalized_handle in [s.lstrip("@") for s in seed_users]

    async def _normalize_and_resolve(
        self, provider: AuthProvider, handle: str
    ) -> tuple[str, str]:
        """Normalize handle and resolve to permanent ID.

        Args:
            provider: Authentication provider
            handle: User handle

        Returns:
            Tuple of (normalized_handle, provider_user_id)

        Raises:
            ValueError: If handle invalid or resolution fails
        """
        if provider == AuthProvider.TWITTER:
            # Twitter: Remove @ prefix if present, use username as provider_user_id
            if handle.startswith("@"):
                handle = handle[1:]
            normalized = handle.lower()
            return normalized, normalized  # Username is provider_user_id

        elif provider == AuthProvider.BLUESKY:
            # Bluesky: Resolve handle to DID
            handle = handle.lower()

            # Validate format
            if "." not in handle:
                raise ValueError("Bluesky handle must contain a dot")

            # Resolve to DID
            did = await resolve_handle_to_did(handle)
            return handle, str(did)  # Convert DID to str for provider_user_id

        else:
            raise ValueError(f"Unsupported provider: {provider}")
