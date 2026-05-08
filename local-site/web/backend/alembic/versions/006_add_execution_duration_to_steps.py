"""Ajoute la colonne execution_duration_seconds à la table steps.

Revision ID: 006
Revises: 005
"""

from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "steps",
        sa.Column("execution_duration_seconds", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("steps", "execution_duration_seconds")
