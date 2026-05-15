"""Ajouter refunded_at et stripe_refund_id à la table tickets.

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
    op.add_column("tickets", sa.Column("refunded_at", sa.DateTime(), nullable=True))
    op.add_column(
        "tickets", sa.Column("stripe_refund_id", sa.String(255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("tickets", "stripe_refund_id")
    op.drop_column("tickets", "refunded_at")
