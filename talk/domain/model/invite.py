"""Invite entity.

Invites control access to the platform through an invite-only system.
Users can invite others by their Bluesky handle.
"""

from datetime import datetime

from pydantic import Field

from talk.domain.model.common import DomainModel
from talk.domain.value import InviteId, InviteStatus, UserId
from talk.domain.value.types import Handle


class Invite(DomainModel):
    """Invite entity.

    Represents an invitation from one user to another via Bluesky handle.
    Business rules:
    - One pending invite per handle (enforced by database unique constraint)
    - Invites can only be created by existing users within their quota
    - Once accepted, invite is marked as accepted and linked to new user
    """

    id: InviteId
    inviter_id: UserId
    invitee_handle: Handle
    status: InviteStatus = InviteStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    accepted_at: datetime | None = None
    accepted_by_user_id: UserId | None = None
