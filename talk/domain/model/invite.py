"""Invite entity.

Invites control access to the platform through an invite-only system.
Users can invite others by their provider-specific handle/identifier.
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from talk.domain.model.common import DomainModel
from talk.domain.value import AuthProvider, InviteId, InviteStatus, InviteToken, UserId


class Invite(DomainModel):
    """Invite entity - single-provider targeting.

    Each invite targets one specific identity on one platform.
    Users can link additional providers after registration.

    Business rules:
    - One pending invite per provider/identity combination
    - Invites can only be created by existing users within their quota
    - Invites never expire
    - Once accepted, invite is marked as accepted and linked to new user
    """

    id: InviteId
    inviter_id: UserId
    provider: AuthProvider  # Target authentication provider
    invitee_handle: str  # Display handle for inviter's reference
    invitee_provider_id: str  # Permanent ID to match against (DID, ORCID iD, username)
    invitee_name: Optional[str] = None  # Optional display name hint
    invite_token: InviteToken  # URL-safe token
    status: InviteStatus = InviteStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    accepted_at: Optional[datetime] = None
    accepted_by_user_id: Optional[UserId] = None
