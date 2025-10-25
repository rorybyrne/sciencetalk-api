"""User aggregate root.

Users are authenticated via AT Protocol (Bluesky) and accumulate karma
through community engagement.
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from talk.domain.model.common import DomainModel
from talk.domain.value import BlueskyDID, Handle, UserId


class User(DomainModel):
    """User aggregate root.

    Represents a user authenticated via AT Protocol/Bluesky.
    """

    id: UserId
    bluesky_did: BlueskyDID
    handle: Handle
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    karma: int = Field(default=0, ge=0)
    invite_quota: int = Field(default=5, ge=0)  # Number of invites user can send
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
