"""User aggregate root.

Users authenticate via multiple providers (Bluesky, ORCID, Twitter)
and accumulate karma through community engagement.
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from talk.domain.model.common import DomainModel
from talk.domain.value import UserId
from talk.domain.value.types import Handle


class User(DomainModel):
    """User aggregate root - provider-agnostic.

    Users can authenticate with multiple providers (Bluesky, ORCID, Twitter).
    One user account can have multiple linked identities.
    """

    id: UserId
    handle: Handle
    avatar_url: Optional[str] = None
    email: Optional[str] = None  # Primary email for notifications
    bio: Optional[str] = None
    karma: int = Field(default=0, ge=0)
    invite_quota: int = Field(default=5, ge=0)  # Number of invites user can send
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
