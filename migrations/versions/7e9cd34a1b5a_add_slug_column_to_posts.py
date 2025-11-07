"""add slug column to posts

Revision ID: 7e9cd34a1b5a
Revises: f96f33be5177
Create Date: 2025-11-07 13:57:36.276195

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7e9cd34a1b5a"
down_revision: Union[str, Sequence[str], None] = "f96f33be5177"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add slug column (nullable initially for backfill)
    op.add_column(
        "posts",
        sa.Column("slug", sa.String(length=100), nullable=True),
    )

    # 2. Backfill slugs using PostgreSQL function
    # Note: Split into separate execute statements for asyncpg compatibility

    # Create temporary function to slugify titles
    op.execute("""
        CREATE OR REPLACE FUNCTION slugify_title(title TEXT, post_id UUID)
        RETURNS TEXT AS $$
        DECLARE
            base_slug TEXT;
            slug TEXT;
            counter INT := 1;
        BEGIN
            -- Convert to lowercase, replace non-alphanumeric with hyphens
            base_slug := lower(regexp_replace(title, '[^a-z0-9]+', '-', 'g'));
            -- Remove leading/trailing hyphens
            base_slug := trim(both '-' from base_slug);
            -- Truncate to 100 characters
            base_slug := substring(base_slug from 1 for 100);

            -- Handle empty slug (fallback to post-{uuid})
            IF base_slug = '' OR base_slug IS NULL THEN
                base_slug := 'post-' || substring(post_id::text from 1 for 8);
            END IF;

            -- Handle collisions by appending counter
            slug := base_slug;
            WHILE EXISTS (SELECT 1 FROM posts WHERE posts.slug = slug) LOOP
                slug := substring(base_slug from 1 for 100 - length('-' || counter::text)) || '-' || counter;
                counter := counter + 1;
            END LOOP;

            RETURN slug;
        END;
        $$ LANGUAGE plpgsql
    """)

    # Backfill all posts with slugs
    op.execute("""
        UPDATE posts
        SET slug = slugify_title(title, id)
        WHERE posts.slug IS NULL
    """)

    # Drop temporary function
    op.execute("DROP FUNCTION slugify_title(TEXT, UUID)")

    # 3. Make slug NOT NULL now that all posts have slugs
    op.alter_column("posts", "slug", nullable=False)

    # 4. Add unique index (globally unique, even for deleted posts)
    op.create_index(
        "posts_slug_unique_idx",
        "posts",
        ["slug"],
        unique=True,
    )

    # 5. Add regular index for slug lookups
    op.create_index("idx_posts_slug", "posts", ["slug"])

    # 6. Add format validation constraint
    op.create_check_constraint(
        "posts_slug_format_check",
        "posts",
        sa.text("slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop constraint
    op.drop_constraint("posts_slug_format_check", "posts", type_="check")

    # Drop indexes
    op.drop_index("idx_posts_slug", table_name="posts")
    op.drop_index("posts_slug_unique_idx", table_name="posts")

    # Drop column
    op.drop_column("posts", "slug")
