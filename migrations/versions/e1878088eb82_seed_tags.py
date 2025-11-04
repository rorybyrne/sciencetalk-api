"""seed_tags

Revision ID: e1878088eb82
Revises: 8a050c997a86
Create Date: 2025-11-04 23:16:44.062416

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1878088eb82"
down_revision: Union[str, Sequence[str], None] = "8a050c997a86"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed initial tags."""
    # Define the 20 launch tags
    tags = [
        # Core Sciences (6)
        ("biology", "Biological sciences, life sciences research"),
        ("chemistry", "Chemical research, materials science"),
        ("physics", "Physical sciences, quantum, astrophysics"),
        ("computer-science", "CS research, algorithms, theory"),
        ("mathematics", "Pure and applied mathematics"),
        ("engineering", "Engineering disciplines, systems design"),
        # Frontier Fields (5)
        ("ai-ml", "Artificial intelligence, machine learning"),
        ("neuroscience", "Brain research, cognitive science"),
        ("energy", "Energy technology, fusion, batteries, climate"),
        ("robotics", "Automation, embodied AI, hardware"),
        ("startups", "Company building, commercialization, ventures"),
        # Meta/Process (3)
        ("metascience", "Science of science, research on research"),
        ("open-science", "Open access, open data, preprints"),
        ("software", "Scientific software, computational tools"),
        # Content Types (5)
        ("tool", "Software tools, datasets, resources"),
        ("discussion", "Questions, debates, ideas"),
        ("question", "Questions for the community"),
        ("result", "Research findings, experiments, data"),
        ("method", "Protocols, techniques, approaches"),
        # Hardware (1)
        ("hardware", "Lab equipment, instrumentation, sensors"),
    ]

    # Insert tags
    tags_table = sa.table(
        "tags",
        sa.column("name", sa.String),
        sa.column("description", sa.String),
    )

    op.bulk_insert(
        tags_table,
        [{"name": name, "description": description} for name, description in tags],
    )


def downgrade() -> None:
    """Remove seeded tags."""
    # Delete all tags that were seeded
    op.execute(
        """
        DELETE FROM tags WHERE name IN (
            'biology', 'chemistry', 'physics', 'computer-science', 'mathematics',
            'engineering', 'ai-ml', 'neuroscience', 'energy', 'robotics',
            'startups', 'metascience', 'open-science', 'software', 'tool',
            'discussion', 'question', 'result', 'method', 'hardware'
        )
        """
    )
