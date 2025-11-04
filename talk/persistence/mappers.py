"""Mappers for converting between database rows and domain models.

Since we're using Pydantic domain models (immutable), we use manual mapping
instead of SQLAlchemy's classical imperative mapping.
"""

from typing import Any, Dict
from uuid import UUID

from talk.domain.model import Comment, Invite, Post, User, UserIdentity, Vote
from talk.domain.value import (
    AuthProvider,
    CommentId,
    InviteId,
    InviteStatus,
    InviteToken,
    PostId,
    PostType,
    UserId,
    UserIdentityId,
    VotableType,
    VoteId,
    VoteType,
)
from talk.domain.value.types import Handle


def row_to_user(row: Dict[str, Any]) -> User:
    """Convert database row to User domain model.

    Args:
        row: Database row as dict

    Returns:
        User domain model
    """
    return User(
        id=UserId(UUID(row["id"]) if isinstance(row["id"], str) else row["id"]),
        handle=Handle(row["handle"]),
        avatar_url=row.get("avatar_url"),
        email=row.get("email"),
        bio=row.get("bio"),
        karma=row["karma"],
        invite_quota=row.get("invite_quota", 5),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def user_to_dict(user: User) -> Dict[str, Any]:
    """Convert User domain model to database dict.

    Args:
        user: User domain model

    Returns:
        Dict suitable for database insertion/update
    """
    return user.model_dump()


def row_to_user_identity(row: Dict[str, Any]) -> UserIdentity:
    """Convert database row to UserIdentity domain model.

    Args:
        row: Database row as dict

    Returns:
        UserIdentity domain model
    """
    return UserIdentity(
        id=UserIdentityId(UUID(row["id"]) if isinstance(row["id"], str) else row["id"]),
        user_id=UserId(
            UUID(row["user_id"]) if isinstance(row["user_id"], str) else row["user_id"]
        ),
        provider=AuthProvider(row["provider"]),
        provider_user_id=row["provider_user_id"],
        provider_handle=row["provider_handle"],
        provider_email=row.get("provider_email"),
        is_primary=row["is_primary"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        last_login_at=row.get("last_login_at"),
    )


def user_identity_to_dict(identity: UserIdentity) -> Dict[str, Any]:
    """Convert UserIdentity domain model to database dict.

    Args:
        identity: UserIdentity domain model

    Returns:
        Dict suitable for database insertion/update
    """
    return identity.model_dump()


def row_to_post(row: Dict[str, Any]) -> Post:
    """Convert database row to Post domain model.

    Args:
        row: Database row as dict

    Returns:
        Post domain model
    """
    return Post(
        id=PostId(UUID(row["id"]) if isinstance(row["id"], str) else row["id"]),
        title=row["title"],
        type=PostType(row["type"]),
        author_id=UserId(
            UUID(row["author_id"])
            if isinstance(row["author_id"], str)
            else row["author_id"]
        ),
        author_handle=Handle(row["author_handle"]),
        url=row.get("url"),
        text=row.get("text"),
        points=row["points"],
        comment_count=row["comment_count"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row.get("deleted_at"),
    )


def post_to_dict(post: Post) -> Dict[str, Any]:
    """Convert Post domain model to database dict.

    Args:
        post: Post domain model

    Returns:
        Dict suitable for database insertion/update
    """
    return post.model_dump()


def row_to_comment(row: Dict[str, Any]) -> Comment:
    """Convert database row to Comment domain model.

    Args:
        row: Database row as dict

    Returns:
        Comment domain model
    """
    return Comment(
        id=CommentId(UUID(row["id"]) if isinstance(row["id"], str) else row["id"]),
        post_id=PostId(
            UUID(row["post_id"]) if isinstance(row["post_id"], str) else row["post_id"]
        ),
        author_id=UserId(
            UUID(row["author_id"])
            if isinstance(row["author_id"], str)
            else row["author_id"]
        ),
        author_handle=Handle(row["author_handle"]),
        text=row["text"],
        parent_id=CommentId(
            UUID(row["parent_id"])
            if isinstance(row["parent_id"], str)
            else row["parent_id"]
        )
        if row.get("parent_id")
        else None,
        depth=row["depth"],
        path=row.get("path"),
        points=row["points"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row.get("deleted_at"),
    )


def comment_to_dict(comment: Comment) -> Dict[str, Any]:
    """Convert Comment domain model to database dict.

    Args:
        comment: Comment domain model

    Returns:
        Dict suitable for database insertion/update
    """
    return comment.model_dump()


def row_to_vote(row: Dict[str, Any]) -> Vote:
    """Convert database row to Vote domain model.

    Args:
        row: Database row as dict

    Returns:
        Vote domain model
    """
    return Vote(
        id=VoteId(UUID(row["id"]) if isinstance(row["id"], str) else row["id"]),
        user_id=UserId(
            UUID(row["user_id"]) if isinstance(row["user_id"], str) else row["user_id"]
        ),
        votable_type=VotableType(row["votable_type"]),
        votable_id=UUID(row["votable_id"])
        if isinstance(row["votable_id"], str)
        else row["votable_id"],
        vote_type=VoteType(row["vote_type"]),
        created_at=row["created_at"],
    )


def vote_to_dict(vote: Vote) -> Dict[str, Any]:
    """Convert Vote domain model to database dict.

    Args:
        vote: Vote domain model

    Returns:
        Dict suitable for database insertion/update
    """
    return vote.model_dump()


def row_to_invite(row: Dict[str, Any]) -> Invite:
    """Convert database row to Invite domain model.

    Args:
        row: Database row as dict

    Returns:
        Invite domain model
    """
    return Invite(
        id=InviteId(UUID(row["id"]) if isinstance(row["id"], str) else row["id"]),
        inviter_id=UserId(
            UUID(row["inviter_id"])
            if isinstance(row["inviter_id"], str)
            else row["inviter_id"]
        ),
        provider=AuthProvider(row["provider"]),
        invitee_handle=row["invitee_handle"],
        invitee_provider_id=row["invitee_provider_id"],
        invitee_name=row.get("invitee_name"),
        invite_token=InviteToken(root=row["invite_token"]),
        status=InviteStatus(row["status"]),
        created_at=row["created_at"],
        accepted_at=row.get("accepted_at"),
        accepted_by_user_id=UserId(
            UUID(row["accepted_by_user_id"])
            if isinstance(row["accepted_by_user_id"], str)
            else row["accepted_by_user_id"]
        )
        if row.get("accepted_by_user_id")
        else None,
    )


def invite_to_dict(invite: Invite) -> Dict[str, Any]:
    """Convert Invite domain model to database dict.

    Args:
        invite: Invite domain model

    Returns:
        Dict suitable for database insertion/update
    """
    # Handle and InviteStatus are automatically serialized by model_dump()
    # thanks to @model_serializer on Handle and Pydantic's enum serialization
    return invite.model_dump()
