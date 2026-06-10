"""Ajout de workflow_type sur dossiers.

Revision ID: 010
Revises: 009
"""

from alembic import op
import sqlalchemy as sa


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dossiers",
        sa.Column(
            "workflow_type",
            sa.String(20),
            nullable=False,
            server_default="standard",
        ),
    )


def downgrade() -> None:
    op.drop_column("dossiers", "workflow_type")
