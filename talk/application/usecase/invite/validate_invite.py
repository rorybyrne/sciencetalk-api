"""Validate invite use case."""

import logfire
from pydantic import BaseModel

from talk.domain.service import InviteService
from talk.domain.value import AuthProvider, InviteStatus, InviteToken


class ValidateInviteRequest(BaseModel):
    """Validate invite request."""

    token: str


class ValidateInviteResponse(BaseModel):
    """Validate invite response."""

    valid: bool
    status: InviteStatus | None = None
    provider: AuthProvider | None = None
    invitee_handle: str | None = None
    invitee_name: str | None = None
    inviter_handle: str | None = None
    message: str | None = None


class ValidateInviteUseCase:
    """Use case for validating an invite token.

    This allows the frontend to check if an invite link is valid
    before redirecting to OAuth.
    """

    def __init__(self, invite_service: InviteService) -> None:
        """Initialize validate invite use case.

        Args:
            invite_service: Invite domain service
        """
        self.invite_service = invite_service

    async def execute(self, request: ValidateInviteRequest) -> ValidateInviteResponse:
        """Validate an invite token.

        Args:
            request: Validation request with token

        Returns:
            Validation response with invite details or error
        """
        with logfire.span("validate_invite.execute", token=request.token[:8] + "..."):
            # Look up invite by token
            invite = await self.invite_service.get_invite_by_token(
                InviteToken(root=request.token)
            )

            if not invite:
                logfire.info("Invite not found", token=request.token[:8] + "...")
                return ValidateInviteResponse(
                    valid=False,
                    message="Invite not found",
                )

            # Check if already accepted
            if invite.status == InviteStatus.ACCEPTED:
                logfire.info(
                    "Invite already accepted",
                    token=request.token[:8] + "...",
                    accepted_at=invite.accepted_at,
                )
                return ValidateInviteResponse(
                    valid=False,
                    status=invite.status,
                    message="Invite has already been accepted",
                )

            # Valid pending invite
            logfire.info(
                "Valid invite found",
                token=request.token[:8] + "...",
                provider=invite.provider.value,
                invitee_handle=invite.invitee_handle,
            )

            return ValidateInviteResponse(
                valid=True,
                status=invite.status,
                provider=invite.provider,
                invitee_handle=invite.invitee_handle,
                invitee_name=invite.invitee_name,
                message="Valid invite",
            )
