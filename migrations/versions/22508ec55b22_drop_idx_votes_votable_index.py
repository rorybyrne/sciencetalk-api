"""drop idx_votes_votable index

Revision ID: 22508ec55b22
Revises: 7e9cd34a1b5a
Create Date: 2025-11-07 22:07:01.732854

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "22508ec55b22"
down_revision: Union[str, Sequence[str], None] = "7e9cd34a1b5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the unused idx_votes_votable index
    # This index is redundant - the unique_vote constraint (user_id, votable_type, votable_id)
    # handles all our actual query patterns (check if user voted, delete vote, batch queries)
    # We use denormalized points counters instead of COUNT(*) queries
    op.drop_index("idx_votes_votable", table_name="votes")


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate the index if rolling back
    op.create_index("idx_votes_votable", "votes", ["votable_type", "votable_id"])
