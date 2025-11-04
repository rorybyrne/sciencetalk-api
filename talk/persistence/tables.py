"""SQLAlchemy table definitions for Science Talk.

These table definitions are used for classical ORM mapping.
They match the schema defined in Alembic migrations.
"""

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

# Metadata object for all tables
metadata = MetaData()

# ============================================================================
# USERS TABLE (Provider-agnostic)
# ============================================================================
users_table = Table(
    "users",
    metadata,
    Column("id", UUID, primary_key=True, server_default="uuid_generate_v4()"),
    Column("handle", String(255), nullable=False),  # Username (from provider handle)
    Column("avatar_url", Text, nullable=True),
    Column("email", String(255), nullable=True),  # Optional email for notifications
    Column("bio", Text, nullable=True),  # Optional bio
    Column("karma", Integer, nullable=False, server_default="0"),
    Column("invite_quota", Integer, nullable=False, server_default="5"),
    Column(
        "created_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    ),
    Column(
        "updated_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    ),
)

Index("idx_users_handle", users_table.c.handle)
Index("idx_users_email", users_table.c.email)

# ============================================================================
# USER IDENTITIES TABLE (Multi-provider authentication)
# ============================================================================
user_identities_table = Table(
    "user_identities",
    metadata,
    Column("id", UUID, primary_key=True, server_default="uuid_generate_v4()"),
    Column("user_id", UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("provider", String(50), nullable=False),  # 'bluesky', 'twitter'
    Column("provider_user_id", String(255), nullable=False),  # DID, username, etc.
    Column("provider_handle", String(255), nullable=False),  # Display handle
    Column("provider_email", String(255), nullable=True),  # Provider email if available
    Column("is_primary", Boolean, nullable=False, server_default="false"),
    Column(
        "created_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    ),
    Column(
        "updated_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    ),
    Column("last_login_at", TIMESTAMP(timezone=True), nullable=True),
    UniqueConstraint("provider", "provider_user_id", name="uq_provider_identity"),
)

Index("idx_user_identities_user_id", user_identities_table.c.user_id)
Index(
    "idx_user_identities_provider",
    user_identities_table.c.provider,
    user_identities_table.c.provider_user_id,
)

# ============================================================================
# TAGS TABLE
# ============================================================================
tags_table = Table(
    "tags",
    metadata,
    Column("id", UUID, primary_key=True, server_default="uuid_generate_v4()"),
    Column("name", String(30), nullable=False, unique=True),
    Column("description", String(200), nullable=False),
    Column(
        "type",
        postgresql.ENUM(
            "science", "applied", "content", "meta", name="tag_type", create_type=False
        ),
        nullable=False,
    ),
    Column(
        "created_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    ),
    Column(
        "updated_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    ),
)

Index("idx_tags_name", tags_table.c.name, unique=True)

# ============================================================================
# POSTS TABLE
# ============================================================================
posts_table = Table(
    "posts",
    metadata,
    Column("id", UUID, primary_key=True, server_default="uuid_generate_v4()"),
    Column("title", String(300), nullable=False),
    Column("url", Text, nullable=True),
    Column("text", Text, nullable=True),
    Column(
        "author_id", UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    ),
    Column("author_handle", String(255), nullable=False),  # Denormalized from users
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
        "(url IS NOT NULL OR text IS NOT NULL)",
        name="url_or_text_required",
    ),
)

Index("idx_posts_created_at", posts_table.c.created_at.desc())
Index("idx_posts_author_id", posts_table.c.author_id)
Index("idx_posts_deleted_at", posts_table.c.deleted_at)

# ============================================================================
# POST_TAGS TABLE (junction table for many-to-many relationship)
# ============================================================================
post_tags_table = Table(
    "post_tags",
    metadata,
    Column("id", UUID, primary_key=True, server_default="uuid_generate_v4()"),
    Column("post_id", UUID, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
    Column("tag_id", UUID, ForeignKey("tags.id", ondelete="RESTRICT"), nullable=False),
    Column(
        "created_at", TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    ),
    UniqueConstraint("post_id", "tag_id", name="uq_post_tag"),
)

Index("idx_post_tags_post_id", post_tags_table.c.post_id)
Index("idx_post_tags_tag_id", post_tags_table.c.tag_id)

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
    Column("author_handle", String(255), nullable=False),  # Denormalized from users
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
# INVITES TABLE (Multi-provider)
# ============================================================================
invites_table = Table(
    "invites",
    metadata,
    Column("id", UUID, primary_key=True, server_default="uuid_generate_v4()"),
    Column(
        "inviter_id", UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    ),
    Column("provider", String(50), nullable=False),  # 'bluesky', 'twitter'
    Column("invitee_handle", String(255), nullable=False),  # Display handle
    Column("invitee_provider_id", String(255), nullable=False),  # DID, username, etc.
    Column("invitee_name", String(255), nullable=True),  # Optional display name
    Column("invite_token", String(255), nullable=False, unique=True),  # URL-safe token
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

# Critical index for login check - must be fast (provider + ID matching)
Index(
    "idx_invites_provider_identity_status",
    invites_table.c.provider,
    invites_table.c.invitee_provider_id,
    invites_table.c.status,
)
Index("idx_invites_inviter_id", invites_table.c.inviter_id)
Index("idx_invites_token", invites_table.c.invite_token)

# Partial unique constraint: only one pending invite per provider identity
# Note: This will be created in migration with: CREATE UNIQUE INDEX ... WHERE status = 'pending'
Index(
    "idx_invites_unique_pending_provider_identity",
    invites_table.c.provider,
    invites_table.c.invitee_provider_id,
    unique=True,
    postgresql_where=invites_table.c.status == "pending",
)
