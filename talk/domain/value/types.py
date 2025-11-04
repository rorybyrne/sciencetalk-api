"""Domain value objects for Science Talk.

Value objects are immutable and defined by their values, not identity.
They encapsulate validation rules and business logic.
"""

from enum import Enum

from pydantic import field_validator

from talk.domain.value.common import RootValueObject, ValueObject


class PostType(str, Enum):
    """Type of scientific post.

    Each type has specific content requirements:
    - URL-based types (result, method, review, tool): require URL
    - Text-based types (discussion, ask): require text content
    """

    RESULT = "result"  # Published findings or experimental results
    METHOD = "method"  # Experimental protocols or techniques
    REVIEW = "review"  # Literature reviews or paper summaries
    DISCUSSION = "discussion"  # Text-based discussions
    ASK = "ask"  # Questions to the community
    TOOL = "tool"  # Software tools or datasets

    @property
    def requires_url(self) -> bool:
        """Check if this post type requires a URL."""
        return self in (
            PostType.RESULT,
            PostType.METHOD,
            PostType.REVIEW,
            PostType.TOOL,
        )

    @property
    def requires_text(self) -> bool:
        """Check if this post type requires text content."""
        return self in (PostType.DISCUSSION, PostType.ASK)


class VoteType(str, Enum):
    """Type of vote.

    Currently only upvotes are supported to encourage positive engagement.
    """

    UP = "up"


class VotableType(str, Enum):
    """Type of entity that can be voted on."""

    POST = "post"
    COMMENT = "comment"


class InviteStatus(str, Enum):
    """Status of an invite."""

    PENDING = "pending"
    ACCEPTED = "accepted"


class AuthProvider(str, Enum):
    """Supported authentication providers."""

    BLUESKY = "bluesky"
    ORCID = "orcid"
    TWITTER = "twitter"


class Handle(RootValueObject[str]):
    """User handle from any authentication provider.

    Represents a user's human-readable identifier:
    - Bluesky: username.bsky.social
    - Twitter: @username or username
    - ORCID: Full ORCID iD (not typically used as handle, but email)
    """

    @field_validator("root")
    @classmethod
    def validate_handle_format(cls, v: str) -> str:
        """Validate handle is not empty and within length limits."""
        if len(v) < 1 or len(v) > 255:
            raise ValueError("Handle must be 1-255 characters")
        return v


class BlueskyDID(RootValueObject[str]):
    """AT Protocol Decentralized Identifier (DID).

    A globally unique, persistent identifier for users on the AT Protocol network.
    Format: did:plc:<identifier> or did:web:<domain>
    """

    @field_validator("root")
    @classmethod
    def validate_did_format(cls, v: str) -> str:
        """Validate DID starts with 'did:'."""
        if not v.startswith("did:"):
            raise ValueError("DID must start with 'did:'")
        if len(v) < 1 or len(v) > 255:
            raise ValueError("DID must be 1-255 characters")
        return v


class InviteToken(RootValueObject[str]):
    """URL-safe invite token."""

    @field_validator("root")
    @classmethod
    def validate_token_format(cls, v: str) -> str:
        """Validate token is not empty."""
        if len(v) < 1 or len(v) > 255:
            raise ValueError("Token must be 1-255 characters")
        return v


class OAuthProviderInfo(ValueObject):
    """OAuth provider information.

    Generic structure for user info returned from any OAuth provider.
    """

    provider: AuthProvider
    provider_user_id: str  # Permanent ID (DID, ORCID iD, Twitter username)
    handle: str  # Display handle
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    verified: bool = False  # Provider-specific verification status
