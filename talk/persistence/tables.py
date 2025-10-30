"""SQLAlchemy table definitions for Science Talk.

These table definitions are used for classical ORM mapping.
They match the schema defined in Alembic migrations.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Enum,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

# Metadata object for all tables
metadata = MetaData()

# ============================================================================
# USERS TABLE
# ============================================================================
users_table = Table(
    "users",
    metadata,
    Column("id", UUID, primary_key=True, server_default="uuid_generate_v4()"),
    Column("bluesky_did", String(255), nullable=False, unique=True),
    Column("handle", String(255), nullable=False),
    Column("display_name", String(255), nullable=True),
    Column("avatar_url", Text, nullable=True),
    Column("karma", Integer, nullable=False, server_default="0"),
    Column("invite_quota", Integer, nullable=False, server_default="5"),
    Column(
        "created_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    ),
    Column(
        "updated_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    ),
)

Index("idx_users_bluesky_did", users_table.c.bluesky_did)
Index("idx_users_handle", users_table.c.handle)

# ============================================================================
# POSTS TABLE
# ============================================================================
posts_table = Table(
    "posts",
    metadata,
    Column("id", UUID, primary_key=True, server_default="uuid_generate_v4()"),
    Column("title", String(300), nullable=False),
    Column(
        "type",
        Enum(
            "result",
            "method",
            "review",
            "discussion",
            "ask",
            "tool",
            name="post_type",
            create_type=False,
        ),
        nullable=False,
    ),
    Column("url", Text, nullable=True),
    Column("text", Text, nullable=True),
    Column(
        "author_id", UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    ),
    Column("author_handle", String(255), nullable=False),
    Column("points", Integer, nullable=False, server_default="1"),
    Column("comment_count", Integer, nullable=False, server_default="0"),
    Column(
        "created_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    ),
    Column(
        "updated_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    ),
    Column("deleted_at", TIMESTAMP(timezone=True), nullable=True),
    CheckConstraint(
        "(type IN ('result', 'method', 'review', 'tool') AND url IS NOT NULL) OR (type IN ('discussion', 'ask'))",
        name="url_required_for_url_types",
    ),
    CheckConstraint(
        "(type IN ('discussion', 'ask') AND text IS NOT NULL) OR (type IN ('result', 'method', 'review', 'tool'))",
        name="text_required_for_text_types",
    ),
)

Index("idx_posts_created_at", posts_table.c.created_at.desc())
Index("idx_posts_type", posts_table.c.type)
Index("idx_posts_author_id", posts_table.c.author_id)
Index("idx_posts_deleted_at", posts_table.c.deleted_at)

# ============================================================================
# COMMENTS TABLE
# ============================================================================
comments_table = Table(
    "comments",
    metadata,
    Column("id", UUID, primary_key=True, server_default="uuid_generate_v4()"),
    Column("post_id", UUID, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
    Column(
        "parent_id", UUID, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    ),
    Column(
        "author_id", UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    ),
    Column("author_handle", String(255), nullable=False),
    Column("text", Text, nullable=False),
    Column("points", Integer, nullable=False, server_default="1"),
    Column("depth", Integer, nullable=False, server_default="0"),
    Column("path", String, nullable=True),  # LTREE type
    Column(
        "created_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    ),
    Column(
        "updated_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    ),
    Column("deleted_at", TIMESTAMP(timezone=True), nullable=True),
    CheckConstraint("depth >= 0", name="depth_non_negative"),
)

Index("idx_comments_post_id", comments_table.c.post_id)
Index("idx_comments_parent_id", comments_table.c.parent_id)
Index("idx_comments_author_id", comments_table.c.author_id)
Index("idx_comments_created_at", comments_table.c.created_at)
Index("idx_comments_deleted_at", comments_table.c.deleted_at)
# Note: GIST index for path is created in migration, not here

# ============================================================================
# VOTES TABLE
# ============================================================================
votes_table = Table(
    "votes",
    metadata,
    Column("id", UUID, primary_key=True, server_default="uuid_generate_v4()"),
    Column("user_id", UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column(
        "votable_type",
        Enum("post", "comment", name="votable_type", create_type=False),
        nullable=False,
    ),
    Column("votable_id", UUID, nullable=False),
    Column(
        "vote_type",
        Enum("up", name="vote_type", create_type=False),
        nullable=False,
        server_default="up",
    ),
    Column(
        "created_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    ),
    UniqueConstraint("user_id", "votable_type", "votable_id", name="unique_vote"),
)

Index("idx_votes_user_id", votes_table.c.user_id)
Index("idx_votes_votable", votes_table.c.votable_type, votes_table.c.votable_id)

# ============================================================================
# INVITES TABLE
# ============================================================================
invites_table = Table(
    "invites",
    metadata,
    Column("id", UUID, primary_key=True, server_default="uuid_generate_v4()"),
    Column(
        "inviter_id", UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    ),
    Column("invitee_handle", String(255), nullable=False),
    Column("invitee_did", String(255), nullable=False),  # Resolved DID
    Column(
        "status",
        Enum("pending", "accepted", name="invite_status", create_type=False),
        nullable=False,
        server_default="pending",
    ),
    Column(
        "created_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    ),
    Column("accepted_at", TIMESTAMP(timezone=True), nullable=True),
    Column(
        "accepted_by_user_id",
        UUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ),
)

# Critical index for login check - must be fast (DID is primary matching)
Index(
    "idx_invites_invitee_did_status",
    invites_table.c.invitee_did,
    invites_table.c.status,
)
Index("idx_invites_inviter_id", invites_table.c.inviter_id)

# Partial unique constraint: only one pending invite per DID
# Note: This will be created in migration with: CREATE UNIQUE INDEX ... WHERE status = 'pending'
Index(
    "idx_invites_unique_pending_did",
    invites_table.c.invitee_did,
    unique=True,
    postgresql_where=invites_table.c.status == "pending",
)
