"""User identity entity.

Links external authentication providers to user accounts.
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from talk.domain.model.common import DomainModel
from talk.domain.value import AuthProvider, UserId, UserIdentityId


class UserIdentity(DomainModel):
    """External authentication identity linked to user account.

    Users can have multiple identities (Twitter, ORCID, Bluesky)
    linked to a single account. This enables account linking and
    multi-provider authentication.
    """

    id: UserIdentityId
    user_id: UserId
    provider: AuthProvider
    provider_user_id: str  # Permanent ID from provider (DID, ORCID iD, username)
    provider_handle: str  # Display handle (can change over time)
    provider_email: Optional[str] = None
    is_primary: bool = False  # Primary authentication method
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_login_at: Optional[datetime] = None
