"""Strongly typed identifiers for Science Talk domain entities.

Using NewType for strong typing prevents mixing up different entity IDs
and makes the code more self-documenting.
"""

from typing import NewType
from uuid import UUID

# Core domain entity identifiers
UserId = NewType("UserId", UUID)
UserIdentityId = NewType("UserIdentityId", UUID)
PostId = NewType("PostId", UUID)
CommentId = NewType("CommentId", UUID)
VoteId = NewType("VoteId", UUID)
InviteId = NewType("InviteId", UUID)
TagId = NewType("TagId", UUID)
