"""Domain value objects for Science Talk.

Value objects are immutable and defined by their values, not identity.
They encapsulate validation rules and business logic.
"""

from enum import Enum

from pydantic import Field, field_validator

from talk.domain.value.common import ValueObject


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


class Handle(ValueObject):
    """Bluesky handle (e.g., username.bsky.social).

    Represents a user's human-readable identifier on the AT Protocol network.
    """

    value: str = Field(min_length=1, max_length=255)

    @field_validator("value")
    @classmethod
    def validate_handle_format(cls, v: str) -> str:
        """Validate handle contains a dot (username.domain format)."""
        if "." not in v:
            raise ValueError("Handle must be in format: username.domain")
        return v

    def __str__(self) -> str:
        return self.value


class BlueskyDID(ValueObject):
    """AT Protocol Decentralized Identifier (DID).

    A globally unique, persistent identifier for users on the AT Protocol network.
    Format: did:plc:<identifier> or did:web:<domain>
    """

    value: str = Field(min_length=1, max_length=255)

    @field_validator("value")
    @classmethod
    def validate_did_format(cls, v: str) -> str:
        """Validate DID starts with 'did:'."""
        if not v.startswith("did:"):
            raise ValueError("DID must start with 'did:'")
        return v

    def __str__(self) -> str:
        return self.value


class UserAuthInfo(ValueObject):
    """User authentication information from external provider.

    Represents the authenticated user's identity and profile information
    obtained from an OAuth provider (e.g., Bluesky).
    """

    did: str
    handle: str
    display_name: str | None = None
    avatar_url: str | None = None
