"""replace_updated_at_with_content_and_comments_timestamps

Revision ID: f96f33be5177
Revises: b08ba9210f11
Create Date: 2025-11-06 23:47:49.918738

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f96f33be5177"
down_revision: Union[str, Sequence[str], None] = "b08ba9210f11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Remove triggers for posts and comments (they auto-set updated_at, which we're replacing)
    # Note: Keep triggers for users and user_identities (they still use updated_at)
    op.execute("DROP TRIGGER IF EXISTS update_posts_updated_at ON posts")
    op.execute("DROP TRIGGER IF EXISTS update_comments_updated_at ON comments")

    # 2. Add new content_updated_at columns (nullable initially)
    op.add_column(
        "posts",
        sa.Column("content_updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "comments",
        sa.Column("content_updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # 3. Backfill content_updated_at with created_at (content never edited yet)
    op.execute("UPDATE posts SET content_updated_at = created_at")
    op.execute("UPDATE comments SET content_updated_at = created_at")

    # 4. Make content_updated_at NOT NULL
    op.alter_column("posts", "content_updated_at", nullable=False)
    op.alter_column("comments", "content_updated_at", nullable=False)

    # 5. Rename updated_at to comments_updated_at for posts (tracks last comment activity)
    op.alter_column("posts", "updated_at", new_column_name="comments_updated_at")

    # 6. Drop updated_at from comments (not needed - comments don't have sub-comments)
    op.drop_column("comments", "updated_at")


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Add back updated_at to comments
    op.add_column(
        "comments", sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.execute("UPDATE comments SET updated_at = content_updated_at")
    op.alter_column("comments", "updated_at", nullable=False)

    # 2. Rename comments_updated_at back to updated_at for posts
    op.alter_column("posts", "comments_updated_at", new_column_name="updated_at")

    # 3. Drop new columns
    op.drop_column("posts", "content_updated_at")
    op.drop_column("comments", "content_updated_at")

    # 4. Recreate triggers for posts and comments
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
