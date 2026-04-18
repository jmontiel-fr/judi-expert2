"""Ajouter ticket_token et expires_at à la table tickets.

Revision ID: 003
Revises: 002
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("ticket_token", sa.String(500), nullable=True))
    op.add_column("tickets", sa.Column("expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("tickets", "expires_at")
    op.drop_column("tickets", "ticket_token")
