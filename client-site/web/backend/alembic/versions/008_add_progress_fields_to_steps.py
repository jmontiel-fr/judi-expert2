"""Ajout des colonnes de progression aux steps.

Revision ID: 008
Revises: 007
"""

from alembic import op
import sqlalchemy as sa


revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("steps", sa.Column("progress_current", sa.Integer(), nullable=True))
    op.add_column("steps", sa.Column("progress_total", sa.Integer(), nullable=True))
    op.add_column("steps", sa.Column("progress_message", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("steps", "progress_message")
    op.drop_column("steps", "progress_total")
    op.drop_column("steps", "progress_current")
