"""initial_schema

Create the foundational schema for Science Talk:
- Users (provider-agnostic authentication)
- User Identities (multi-provider authentication: Twitter, Bluesky)
- Posts (6 types: result, method, review, discussion, ask, tool)
- Comments (nested/threaded with unlimited depth)
- Votes (upvote-only system)
- Invites (multi-provider invite-only user onboarding)

Revision ID: 8a050c997a86
Revises:
Create Date: 2025-10-23 22:41:30.096667

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "8a050c997a86"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable required extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "ltree"')

    # Create ENUM types (idempotent)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE votable_type AS ENUM ('post', 'comment');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE vote_type AS ENUM ('up');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE invite_status AS ENUM ('pending', 'accepted');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE tag_type AS ENUM ('science', 'applied', 'content', 'meta');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # ========================================================================
    # USERS table (provider-agnostic)
    # ========================================================================
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("handle", sa.String(255), nullable=False),  # Username
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("karma", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invite_quota", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_users_handle", "users", ["handle"])
    op.create_index("idx_users_email", "users", ["email"])

    # ========================================================================
    # USER_IDENTITIES table (multi-provider authentication)
    # ========================================================================
    op.create_table(
        "user_identities",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),  # 'bluesky', 'twitter'
        sa.Column(
            "provider_user_id", sa.String(255), nullable=False
        ),  # DID, username, etc.
        sa.Column("provider_handle", sa.String(255), nullable=False),
        sa.Column("provider_email", sa.String(255), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "provider_user_id", name="uq_provider_identity"
        ),
    )
    op.create_index("idx_user_identities_user_id", "user_identities", ["user_id"])
    op.create_index(
        "idx_user_identities_provider",
        "user_identities",
        ["provider", "provider_user_id"],
    )

    # ========================================================================
    # TAGS table
    # ========================================================================
    op.create_table(
        "tags",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(30), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(
                "science",
                "applied",
                "content",
                "meta",
                name="tag_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_tag_name"),
    )
    op.create_index("idx_tags_name", "tags", ["name"], unique=True)

    # ========================================================================
    # POSTS table
    # ========================================================================
    op.create_table(
        "posts",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("author_handle", sa.String(255), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # Business rule: must have URL or text content
        sa.CheckConstraint(
            "(url IS NOT NULL OR text IS NOT NULL)",
            name="url_or_text_required",
        ),
    )
    op.create_index("idx_posts_created_at", "posts", [sa.text("created_at DESC")])
    op.create_index("idx_posts_author_id", "posts", ["author_id"])
    op.create_index("idx_posts_deleted_at", "posts", ["deleted_at"])

    # ========================================================================
    # POST_TAGS table (junction table for many-to-many)
    # ========================================================================
    op.create_table(
        "post_tags",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("post_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "tag_id", name="uq_post_tag"),
    )
    op.create_index("idx_post_tags_post_id", "post_tags", ["post_id"])
    op.create_index("idx_post_tags_tag_id", "post_tags", ["tag_id"])

    # ========================================================================
    # COMMENTS table
    # ========================================================================
    op.create_table(
        "comments",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("post_id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("author_handle", sa.String(255), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("path", sa.String(), nullable=True),  # LTREE type
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("depth >= 0", name="depth_non_negative"),
    )

    # Cast path column to ltree type
    op.execute("ALTER TABLE comments ALTER COLUMN path TYPE ltree USING path::ltree")

    op.create_index("idx_comments_post_id", "comments", ["post_id"])
    op.create_index("idx_comments_parent_id", "comments", ["parent_id"])
    op.create_index("idx_comments_author_id", "comments", ["author_id"])
    op.create_index("idx_comments_created_at", "comments", ["created_at"])
    op.create_index("idx_comments_deleted_at", "comments", ["deleted_at"])
    # GIST index for ltree path queries
    op.execute("CREATE INDEX idx_comments_path ON comments USING GIST(path)")

    # ========================================================================
    # VOTES table
    # ========================================================================
    op.create_table(
        "votes",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "votable_type",
            postgresql.ENUM("post", "comment", name="votable_type", create_type=False),
            nullable=False,
        ),
        sa.Column("votable_id", sa.UUID(), nullable=False),
        sa.Column(
            "vote_type",
            postgresql.ENUM("up", name="vote_type", create_type=False),
            nullable=False,
            server_default="up",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "votable_type", "votable_id", name="unique_vote"
        ),
    )
    op.create_index("idx_votes_user_id", "votes", ["user_id"])
    op.create_index("idx_votes_votable", "votes", ["votable_type", "votable_id"])

    # ========================================================================
    # INVITES table (multi-provider)
    # ========================================================================
    op.create_table(
        "invites",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("inviter_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),  # 'bluesky', 'twitter'
        sa.Column("invitee_handle", sa.String(255), nullable=False),
        sa.Column(
            "invitee_provider_id", sa.String(255), nullable=False
        ),  # DID, username, etc.
        sa.Column("invitee_name", sa.String(255), nullable=True),
        sa.Column("invite_token", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending", "accepted", name="invite_status", create_type=False
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("accepted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("accepted_by_user_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["inviter_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["accepted_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Critical index for login check - must be fast (provider + ID matching)
    op.create_index(
        "idx_invites_provider_identity_status",
        "invites",
        ["provider", "invitee_provider_id", "status"],
    )
    op.create_index("idx_invites_inviter_id", "invites", ["inviter_id"])
    op.create_index("idx_invites_token", "invites", ["invite_token"])

    # Partial unique constraint: only one pending invite per provider identity
    op.execute("""
        CREATE UNIQUE INDEX idx_invites_unique_pending_provider_identity
        ON invites (provider, invitee_provider_id)
        WHERE status = 'pending'
    """)

    # ========================================================================
    # TRIGGERS
    # ========================================================================

    # Trigger function to update updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    # Apply updated_at trigger to users, user_identities, posts, and comments
    op.execute("""
        CREATE TRIGGER update_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)

    op.execute("""
        CREATE TRIGGER update_user_identities_updated_at
        BEFORE UPDATE ON user_identities
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)

    op.execute("""
        CREATE TRIGGER update_posts_updated_at
        BEFORE UPDATE ON posts
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)

    op.execute("""
        CREATE TRIGGER update_comments_updated_at
        BEFORE UPDATE ON comments
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)

    # Trigger function to maintain comment path and depth
    op.execute("""
        CREATE OR REPLACE FUNCTION update_comment_path()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.parent_id IS NULL THEN
                -- Top-level comment
                NEW.path = NEW.id::text::ltree;
                NEW.depth = 0;
            ELSE
                -- Nested comment - inherit parent's path
                SELECT path || NEW.id::text, depth + 1
                INTO NEW.path, NEW.depth
                FROM comments
                WHERE id = NEW.parent_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    op.execute("""
        CREATE TRIGGER set_comment_path
        BEFORE INSERT ON comments
        FOR EACH ROW EXECUTE FUNCTION update_comment_path()
    """)

    # ========================================================================
    # SEED TAGS
    # ========================================================================
    tags_data = [
        # science (10 tags) - Core research disciplines
        ("biology", "Biological sciences, life sciences research", "science"),
        ("chemistry", "Chemical research, materials science", "science"),
        ("physics", "Physical sciences, quantum, astrophysics", "science"),
        ("computer-science", "CS research, algorithms, theory", "science"),
        ("mathematics", "Pure and applied mathematics", "science"),
        ("engineering", "Engineering disciplines, systems design", "science"),
        ("ai-ml", "Artificial intelligence, machine learning", "science"),
        ("neuroscience", "Brain research, cognitive science", "science"),
        ("energy", "Energy technology, fusion, batteries, climate", "science"),
        ("robotics", "Automation, embodied AI, hardware", "science"),
        # applied (7 tags) - Building/making things
        ("startups", "Company building, commercialization, ventures", "applied"),
        ("software", "Scientific software, computational tools", "applied"),
        ("hardware", "Lab equipment, instrumentation, sensors", "applied"),
        ("metascience", "Science of science, research on research", "applied"),
        ("design", "Product design, experimental design, systems design", "applied"),
        ("open-science", "Open access, open data, open protocols", "applied"),
        ("ux", "User experience, user research, design research", "applied"),
        # content (6 tags) - Post format
        ("tool", "Software tools, datasets, resources", "content"),
        ("result", "Research findings, experiments, data", "content"),
        ("method", "Protocols, techniques, approaches", "content"),
        ("question", "Questions for the community", "content"),
        ("discussion", "Debates, ideas, opinions", "content"),
        ("essay", "Long-form writing, think pieces", "content"),
        # meta (3 tags) - Philosophy/social studies of science
        ("philosophy", "Philosophy of science, epistemology", "meta"),
        ("anthropology", "Ethnography, STS, lab studies", "meta"),
        ("history", "History of science, historical analysis", "meta"),
    ]

    tags_table = sa.table(
        "tags",
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column(
            "type",
            postgresql.ENUM("science", "applied", "content", "meta", name="tag_type"),
        ),
    )

    op.bulk_insert(
        tags_table,
        [
            {"name": name, "description": description, "type": tag_type}
            for name, description, tag_type in tags_data
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS set_comment_path ON comments")
    op.execute("DROP TRIGGER IF EXISTS update_comments_updated_at ON comments")
    op.execute("DROP TRIGGER IF EXISTS update_posts_updated_at ON posts")
    op.execute(
        "DROP TRIGGER IF EXISTS update_user_identities_updated_at ON user_identities"
    )
    op.execute("DROP TRIGGER IF EXISTS update_users_updated_at ON users")

    # Drop trigger functions
    op.execute("DROP FUNCTION IF EXISTS update_comment_path()")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Drop tables (in reverse order of dependencies)
    op.drop_table("invites")
    op.drop_table("votes")
    op.drop_table("comments")
    op.drop_table("post_tags")
    op.drop_table("posts")
    op.drop_table("tags")
    op.drop_table("user_identities")
    op.drop_table("users")

    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS tag_type")
    op.execute("DROP TYPE IF EXISTS invite_status")
    op.execute("DROP TYPE IF EXISTS vote_type")
    op.execute("DROP TYPE IF EXISTS votable_type")
    op.execute("DROP TYPE IF EXISTS post_type")

    # Drop extensions (commented out to avoid issues with shared extensions)
    # op.execute("DROP EXTENSION IF EXISTS ltree")
    # op.execute("DROP EXTENSION IF EXISTS \"uuid-ossp\"")
