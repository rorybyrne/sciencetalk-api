"""add_user_tree_indexes_and_seed_invites

Revision ID: b08ba9210f11
Revises: 8a050c997a86
Create Date: 2025-11-06 16:24:42.969394

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b08ba9210f11"
down_revision: Union[str, Sequence[str], None] = "8a050c997a86"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    1. Add performance indexes for user tree queries
    2. Insert seed invite relationships (rory.bio -> livingphysics.org, isabellease.bsky.social)
    """
    # ========================================================================
    # Add indexes for efficient user tree building
    # ========================================================================

    # Index 1: For reverse lookup - "who invited this user?"
    # Partial index only on rows with accepted users
    op.execute("""
        CREATE INDEX idx_invites_accepted_by_user_id
        ON invites(accepted_by_user_id)
        WHERE accepted_by_user_id IS NOT NULL
    """)

    # Index 2: For full tree query - "get all parent-child relationships"
    # Composite partial index for maximum query performance
    op.execute("""
        CREATE INDEX idx_invites_tree_relationships
        ON invites(status, inviter_id, accepted_by_user_id)
        WHERE status = 'accepted' AND accepted_by_user_id IS NOT NULL
    """)

    # ========================================================================
    # Insert seed invite relationships
    # ========================================================================
    # Creates invites from rory.bio to livingphysics.org and isabellease.bsky.social
    # Only inserts if users exist and don't already have invite records
    # Ignores ryrobyrne as specified

    op.execute("""
        INSERT INTO invites (
            inviter_id,
            provider,
            invitee_handle,
            invitee_provider_id,
            invitee_name,
            invite_token,
            status,
            accepted_by_user_id,
            accepted_at,
            created_at
        )
        SELECT
            u_rory.id AS inviter_id,
            ui_invitee.provider,
            u_invitee.handle AS invitee_handle,
            ui_invitee.provider_user_id AS invitee_provider_id,
            u_invitee.handle AS invitee_name,
            'seed-invite-' || u_invitee.handle AS invite_token,
            'accepted' AS status,
            u_invitee.id AS accepted_by_user_id,
            u_invitee.created_at AS accepted_at,
            u_invitee.created_at AS created_at
        FROM users u_rory
        CROSS JOIN users u_invitee
        LEFT JOIN user_identities ui_invitee
            ON ui_invitee.user_id = u_invitee.id
            AND ui_invitee.is_primary = true
        WHERE
            u_rory.handle = 'rory.bio'
            AND u_invitee.handle IN ('livingphysics.org', 'isabellease.bsky.social')
            AND ui_invitee.provider IS NOT NULL
            AND ui_invitee.provider_user_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM invites
                WHERE accepted_by_user_id = u_invitee.id
            )
    """)


def downgrade() -> None:
    """Downgrade schema.

    1. Remove seed invite relationships
    2. Drop performance indexes
    """
    # Remove seed invites (by unique token pattern)
    op.execute("""
        DELETE FROM invites
        WHERE invite_token IN (
            'seed-invite-livingphysics.org',
            'seed-invite-isabellease.bsky.social'
        )
    """)

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_invites_tree_relationships")
    op.execute("DROP INDEX IF EXISTS idx_invites_accepted_by_user_id")
