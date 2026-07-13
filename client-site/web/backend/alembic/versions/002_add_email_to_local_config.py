"""Ajouter le champ email à local_config.

Revision ID: 002
Revises: 001
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("local_config", sa.Column("email", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("local_config", "email")
